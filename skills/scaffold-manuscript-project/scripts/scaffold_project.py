#!/usr/bin/env python3
"""Preview or create portable guidance for a scientific LaTeX repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
import venv
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSET_DIR = SKILL_DIR / "assets"
INCLUDE_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
MAX_INCLUDE_DEPTH = 256
BIB_RE = re.compile(
    r"\\(?:bibliography|addbibresource)(?:\[[^]]*\])?\s*\{([^}]+)\}"
)
IGNORED_PARTS = {
    ".git",
    ".venv",
    "env",
    "venv",
    "build",
    "dist",
    "archive",
    "archives",
    "old",
    "__pycache__",
}
DOMAIN_PROFILES = ("hep-astrophysics", "axion-phenomenology")
STANDARD_PACKET_HEADINGS = (
    "## Load when",
    "## Established results",
    "## Limits and non-claims",
    "## Rejected or superseded routes",
    "## Evidence routes",
    "## Active gap",
)
UNIFIED_INPUT_PATHS = (
    "AGENTS.md",
    "RESEARCH_PLAN.md",
    "SCIENTIFIC_PROGRESS.md",
    "CITATION_PLAN.md",
    "docs/README.md",
    "docs/ENVIRONMENT.md",
    "docs/derivations/README.md",
    "docs/context/README.md",
    "calculations/README.md",
    "calculations/__init__.py",
    "calculations/core/__init__.py",
    "calculations/models/__init__.py",
    "calculations/workflows/__init__.py",
    "calculations/cli/__init__.py",
    "configs/README.md",
    "verification/README.md",
    "verification/verify_all.py",
    "verification/verify_context_architecture.py",
    "requirements.txt",
    "requirements-runtime.txt",
    "requirements-verification.txt",
    "requirements-plot.txt",
)


def fail(message: str) -> "NoReturn":
    raise ValueError(message)


def inside(root: Path, candidate: Path) -> Path:
    root = root.resolve(strict=False)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {candidate}") from exc
    return resolved


def strip_comment(line: str) -> str:
    for index, char in enumerate(line):
        if char != "%":
            continue
        slashes = 0
        cursor = index - 1
        while cursor >= 0 and line[cursor] == "\\":
            slashes += 1
            cursor -= 1
        if slashes % 2 == 0:
            return line[:index]
    return line


def resolve_tex(
    raw: str,
    current: Path,
    root_tex_directory: Path,
    project_root: Path,
) -> Path | None:
    value = Path(raw.strip())
    if not value.suffix:
        value = value.with_suffix(".tex")
    candidates = dict.fromkeys(
        (
            current.parent / value,
            root_tex_directory / value,
            project_root / value,
        )
    )
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(project_root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def include_graph(root_tex: Path, project_root: Path) -> tuple[list[Path], list[str]]:
    project_root = project_root.resolve(strict=False)
    root_tex = inside(project_root, root_tex)
    ordered: list[Path] = []
    warnings: list[str] = []
    visited: set[Path] = set()

    def visit(path: Path, stack: tuple[Path, ...]) -> None:
        if path in stack:
            warnings.append(f"include cycle skipped: {path}")
            return
        if path in visited:
            return
        if len(stack) >= MAX_INCLUDE_DEPTH:
            warnings.append(f"include depth exceeds {MAX_INCLUDE_DEPTH}: {path}")
            return
        visited.add(path)
        ordered.append(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        clean = "\n".join(strip_comment(line) for line in text.splitlines())
        for match in INCLUDE_RE.finditer(clean):
            target = resolve_tex(
                match.group(1), path, root_tex.parent, project_root
            )
            if target is None:
                warnings.append(f"unresolved include in {path}: {match.group(1)}")
            else:
                visit(target, (*stack, path))

    visit(root_tex, ())
    return ordered, warnings


def discover_root_tex(project_root: Path) -> Path:
    candidates: list[tuple[int, Path]] = []
    for path in project_root.rglob("main.tex"):
        relative = path.relative_to(project_root)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        clean = "\n".join(strip_comment(line) for line in text.splitlines())
        score = 0
        score += 5 if r"\documentclass" in clean else 0
        score += 4 if r"\begin{document}" in clean else 0
        score += 2 if BIB_RE.search(clean) else 0
        score += min(len(INCLUDE_RE.findall(clean)), 3)
        candidates.append((score, path.resolve()))
    if not candidates:
        fail("cannot infer a root TeX file; pass --root-tex")
    candidates.sort(key=lambda item: (-item[0], item[1].as_posix()))
    best_score = candidates[0][0]
    best = [path for score, path in candidates if score == best_score]
    if len(best) != 1:
        shown = ", ".join(
            f"{path.relative_to(project_root)} (score {score})"
            for score, path in candidates
        )
        fail(
            "cannot infer a unique root TeX file; pass --root-tex "
            f"(candidates: {shown})"
        )
    return best[0]


def load_existing_manifest(project_root: Path) -> dict:
    """Load an existing project manifest without treating it as disposable scaffold output."""
    path = project_root / "manuscript-project.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        value = tomllib.load(handle)
    if not isinstance(value, dict):
        fail("existing manuscript-project.toml is not a TOML table")
    return value


def configured_project_path(
    project_root: Path, manifest: dict, section: str, key: str,
) -> Path | None:
    table = manifest.get(section, {})
    if not isinstance(table, dict):
        fail(f"existing manifest [{section}] must be a table")
    raw = table.get(key)
    if raw in (None, ""):
        return None
    if not isinstance(raw, str):
        fail(f"existing manifest {section}.{key} must be a string")
    return inside(project_root, project_root / raw)


def discover_bibliography(
    files: list[Path], project_root: Path, explicit: Path | None
) -> str:
    if explicit is not None:
        resolved = inside(project_root, project_root / explicit)
        if not resolved.is_file():
            fail(f"bibliography does not exist: {explicit}")
        return resolved.relative_to(project_root).as_posix()
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        clean = "\n".join(strip_comment(line) for line in text.splitlines())
        match = BIB_RE.search(clean)
        if not match:
            continue
        value = Path(match.group(1).split(",", 1)[0].strip())
        if not value.suffix:
            value = value.with_suffix(".bib")
        for candidate in (path.parent / value, project_root / value):
            resolved = candidate.resolve(strict=False)
            try:
                resolved.relative_to(project_root)
            except ValueError:
                continue
            if resolved.is_file():
                return resolved.relative_to(project_root).as_posix()
    return ""


def render(template_name: str, values: dict[str, str]) -> str:
    text = (ASSET_DIR / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    remaining = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    if remaining:
        fail(f"unresolved template fields in {template_name}: {remaining}")
    return text


def markdown_link(label: str, target: str) -> str:
    """Render a local Markdown link that remains valid when paths contain spaces."""
    safe_label = label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    return f"[{safe_label}](<{target}>)"


def latexmk_command(root_tex: str) -> list[str]:
    """Build from the repository root while isolating products under build/."""
    depth = len(Path(root_tex).parent.parts)
    output_dir = Path(*([".."] * depth), "build").as_posix() if depth else "build"
    return [
        "latexmk",
        "-cd",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-outdir={output_dir}",
        root_tex,
    ]


def existing_environment_specs(project_root: Path) -> list[str]:
    """Return user-owned environment specifications that adoption must not duplicate."""
    conventional = (
        "pyproject.toml",
        "environment.yml",
        "environment.yaml",
        "conda-lock.yml",
        "Pipfile",
        "poetry.lock",
        "uv.lock",
    )
    found = [name for name in conventional if (project_root / name).is_file()]
    found.extend(
        path.relative_to(project_root).as_posix()
        for path in sorted(project_root.glob("requirements*.txt"))
    )
    found.extend(
        f"{name}/"
        for name in ("env", ".venv", "venv")
        if (project_root / name).is_dir()
    )
    return list(dict.fromkeys(found))


def environment_python_relative(directory: str = "env") -> str:
    """Return the repository-relative interpreter created by stdlib venv."""
    if sys.platform == "win32":
        return f"{directory}/Scripts/python.exe"
    return f"{directory}/bin/python"


def read_venv_configuration(path: Path) -> dict[str, str]:
    """Read the simple key/value format used by pyvenv.cfg."""
    configuration: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            configuration[key.strip().lower()] = value.strip()
    return configuration


def inspect_virtual_environment(project_root: Path, directory: str) -> str:
    """Validate a local venv structurally without executing project-owned code."""
    target = inside(project_root, project_root / directory)
    configuration_path = target / "pyvenv.cfg"
    python_relative = environment_python_relative(directory)
    python_path = project_root / python_relative
    if (
        not target.is_dir()
        or not configuration_path.is_file()
        or not python_path.is_file()
        or not os.access(python_path, os.X_OK)
    ):
        fail(f"{directory}/ is not a recognizable executable virtual environment")
    configuration = read_venv_configuration(configuration_path)
    if configuration.get("include-system-site-packages", "").lower() != "false":
        fail(f"{directory}/ enables or does not declare isolation from system packages")
    version = configuration.get("version", "")
    match = re.match(r"^(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (3, 11):
        fail(f"{directory}/ does not declare Python 3.11 or newer")
    return python_relative


def inspect_environment_target(project_root: Path) -> str:
    """Classify an existing env path without executing project-owned code."""
    target = inside(project_root, project_root / "env")
    if not target.exists():
        return "create"
    try:
        inspect_virtual_environment(project_root, "env")
    except ValueError as exc:
        fail(
            f"env exists but cannot satisfy the project environment contract ({exc}); "
            "inspect it and rerun with --no-bootstrap-environment to preserve it"
        )
    return "preserve"


def configured_provenance_python(manifest: dict) -> str:
    """Return an established manifest interpreter without rewriting its policy."""
    verification = manifest.get("verification", {})
    if not isinstance(verification, dict):
        return ""
    value = verification.get("provenance_python", "")
    return value if isinstance(value, str) and value else ""


def select_project_python(
    project_root: Path,
    manifest: dict,
    *,
    bootstrap_environment: bool,
) -> tuple[str, list[str]]:
    """Choose a project command path without executing adopted interpreters."""
    if bootstrap_environment:
        return environment_python_relative(), []
    configured = configured_provenance_python(manifest)
    if configured:
        return configured, []

    valid: list[str] = []
    warnings: list[str] = []
    for directory in ("env", ".venv", "venv"):
        if not (project_root / directory).exists():
            continue
        try:
            selected = inspect_virtual_environment(project_root, directory)
            valid.append(selected)
            warnings.append(
                f"{directory}/ was discovered by structural inspection only; "
                "execute the registered verifier to validate the interpreter"
            )
        except ValueError as exc:
            warnings.append(
                f"ignored unusable local environment {directory}/: {exc}"
            )
    if len(valid) == 1:
        return valid[0], warnings
    if len(valid) > 1:
        warnings.append(
            "multiple structurally compatible local environments were found; "
            "generated commands "
            "use a portable Python launcher until one contract is selected"
        )
    return portable_python_command(), warnings


def shell_token(value: str) -> str:
    """Quote one command token for the platform-specific generated guidance."""
    if sys.platform == "win32":
        return subprocess.list2cmdline([value])
    return shlex.quote(value)


def portable_python_command() -> str:
    """Return a portable fallback for an activated or system Python 3."""
    return "py" if sys.platform == "win32" else "python3"


def create_environment(project_root: Path) -> str:
    """Create and validate an offline repository-local virtual environment."""
    if sys.version_info < (3, 11):
        fail(
            "environment bootstrap requires Python 3.11 or newer; "
            "invoke the scaffold with the intended interpreter"
        )
    target = inside(project_root, project_root / "env")
    if target.exists():
        fail("refusing to replace an existing env directory")
    try:
        venv.EnvBuilder(
            system_site_packages=False,
            clear=False,
            symlinks=False,
            upgrade=False,
            with_pip=True,
            upgrade_deps=False,
        ).create(target)
        python_path = project_root / environment_python_relative()
        if not python_path.is_file():
            fail(f"virtual environment interpreter is missing: {python_path}")
        probe = subprocess.run(
            [
                str(python_path),
                "-c",
                (
                    "import json, sys; "
                    "print(json.dumps({'prefix': sys.prefix, "
                    "'base_prefix': sys.base_prefix, "
                    "'version': list(sys.version_info[:3])}))"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if probe.returncode:
            fail(
                "created virtual environment failed its interpreter probe: "
                + (probe.stderr.strip() or f"exit {probe.returncode}")
            )
        details = json.loads(probe.stdout)
        if Path(details["prefix"]).resolve() != target.resolve():
            fail("created interpreter does not report the repository env as sys.prefix")
        if details["prefix"] == details["base_prefix"]:
            fail("created interpreter is not isolated from its base interpreter")
        if tuple(details["version"]) < (3, 11, 0):
            fail("created virtual environment uses Python older than 3.11")
        configuration = (target / "pyvenv.cfg").read_text(
            encoding="utf-8", errors="replace"
        ).lower()
        if "include-system-site-packages = false" not in configuration:
            fail("created virtual environment enables undeclared system packages")
    except Exception as exc:
        cleanup_error = ""
        if target.exists():
            try:
                shutil.rmtree(target)
            except OSError as cleanup_exc:
                cleanup_error = f"; cleanup also failed: {cleanup_exc}"
        if isinstance(exc, ValueError):
            raise ValueError(f"{exc}{cleanup_error}") from exc
        raise ValueError(
            f"could not create repository virtual environment: {exc}{cleanup_error}"
        ) from exc
    return environment_python_relative()


def preflight_output_paths(project_root: Path, paths: tuple[Path, ...]) -> None:
    """Reject path-shape conflicts before writing files or creating env."""
    for path in paths:
        inside(project_root, path)
        if path.exists() and not path.is_file():
            fail(f"output target exists but is not a file: {path.relative_to(project_root)}")
        parent = path.parent
        while parent != project_root:
            inside(project_root, parent)
            if parent.exists() and not parent.is_dir():
                fail(
                    "output parent exists but is not a directory: "
                    f"{parent.relative_to(project_root)}"
                )
            parent = parent.parent


def manifest_migration_gaps(
    manifest: dict,
    expected_inputs: list[str],
    expected_packets: list[str],
    project_root: Path,
    context_file: str,
) -> list[str]:
    """Describe unified-contract gaps without mutating an adopted manifest."""
    gaps: list[str] = []
    manuscript = manifest.get("manuscript")
    if not isinstance(manuscript, dict):
        gaps.append("add a [manuscript] table")
    elif manuscript.get("context_docs") != ["AGENTS.md", "SCIENTIFIC_PROGRESS.md"]:
        gaps.append(
            'set manuscript.context_docs to ["AGENTS.md", "SCIENTIFIC_PROGRESS.md"] '
            "before enabling the unified structural verifier"
        )

    verification = manifest.get("verification")
    if not isinstance(verification, dict):
        gaps.append("add a [verification] table with a default command group")
    else:
        if "offline" in verification:
            if "default" in verification:
                gaps.append(
                    "resolve the conflict between verification.offline and "
                    "verification.default; keep only verification.default"
                )
            else:
                gaps.append(
                    "rename verification.offline to verification.default "
                    "(the name does not imply network isolation)"
                )
        elif "default" not in verification:
            gaps.append("add verification.default")
        default_commands = verification.get("default", [])
        if not (
            isinstance(default_commands, list)
            and any(
                isinstance(command, list)
                and "verification/verify_all.py" in command
                for command in default_commands
            )
        ):
            gaps.append(
                "register verification/verify_all.py in verification.default "
                "before treating the unified verifier as a default gate"
            )
        raw_inputs = verification.get("inputs", [])
        if isinstance(raw_inputs, list) and all(
            isinstance(item, str) for item in raw_inputs
        ):
            missing = [item for item in expected_inputs if item not in raw_inputs]
            if missing:
                gaps.append(
                    "register unified verification inputs: " + ", ".join(missing)
                )
        else:
            gaps.append("make verification.inputs an array of project-relative paths")
    context = manifest.get("context")
    if not isinstance(context, dict):
        gaps.append("add the bounded [context] result-index and topic-packet contract")
    else:
        if context.get("result_index") != "SCIENTIFIC_PROGRESS.md":
            gaps.append("set context.result_index to SCIENTIFIC_PROGRESS.md")
        if context.get("required_packet_headings") != list(STANDARD_PACKET_HEADINGS):
            gaps.append(
                "reconcile context.required_packet_headings with the unified "
                "ordered packet contract"
            )
        for key in ("default_context_max_bytes", "packet_max_bytes"):
            value = context.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                gaps.append(f"set context.{key} to a positive integer")
        result_index_limit = context.get("result_index_max_bytes")
        if result_index_limit is not None and (
            not isinstance(result_index_limit, int)
            or isinstance(result_index_limit, bool)
            or result_index_limit <= 0
        ):
            gaps.append("set context.result_index_max_bytes to a positive integer")
        registered_packets = context.get("packets")
        if (
            not isinstance(registered_packets, list)
            or any(not isinstance(item, str) for item in registered_packets)
            or len(registered_packets) != len(set(registered_packets))
            or sorted(registered_packets) != sorted(expected_packets)
        ):
            gaps.append(
                "reconcile context.packets with the preserved packet set: "
                + ", ".join(expected_packets)
            )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or "generated" not in artifacts:
        gaps.append("add [artifacts] with generated = []")
        generated = []
    else:
        generated = artifacts.get("generated")
    if not isinstance(generated, list):
        gaps.append("make artifacts.generated an array")
    elif any(not isinstance(item, dict) for item in generated):
        gaps.append(
            "replace every artifacts.generated path string with "
            '{ source = "...", outputs = ["..."] }'
        )
    else:
        seen_outputs: set[str] = set()
        for index, item in enumerate(generated):
            if set(item) != {"source", "outputs"}:
                gaps.append(
                    f"limit artifacts.generated[{index}] to exactly source and outputs"
                )
            source = item.get("source")
            outputs = item.get("outputs")
            if not isinstance(source, str) or not source:
                gaps.append(
                    f"give artifacts.generated[{index}] a nonempty source path"
                )
            else:
                try:
                    source_path = inside(project_root, project_root / source)
                except ValueError:
                    gaps.append(
                        f"keep artifacts.generated[{index}].source inside the project"
                    )
                else:
                    if not source_path.is_file():
                        gaps.append(
                            f"restore generated-artifact source file: {source}"
                        )
            if (
                not isinstance(outputs, list)
                or not outputs
                or any(not isinstance(output, str) or not output for output in outputs)
            ):
                gaps.append(
                    f"give artifacts.generated[{index}] a nonempty string outputs array"
                )
                continue
            for output in outputs:
                try:
                    inside(project_root, project_root / output)
                except ValueError:
                    gaps.append(
                        f"keep generated-artifact output inside the project: {output}"
                    )
                if isinstance(source, str) and output == source:
                    gaps.append(
                        f"generated artifact must not overwrite its source: {source}"
                    )
                if output in seen_outputs:
                    gaps.append(
                        f"declare generated output only once: {output}"
                    )
                seen_outputs.add(output)

    role_headings = {
        "AGENTS.md": (
            "## Two-hop context protocol",
            "## Project orientation and research notices",
            "## Scientific invariants",
            "## Build and validation",
        ),
        "SCIENTIFIC_PROGRESS.md": (
            "## Topic map",
            "## Retained result catalogue",
            "## Stop and do-not-repeat decisions",
        ),
        "RESEARCH_PLAN.md": (
            "## Central question",
            "## Decisive results",
            "## Immediate next decision",
        ),
        context_file: (
            "## Include order",
            "## Section guide",
        ),
        "CITATION_PLAN.md": (
            "## Source and coverage ledger",
            "## Bibliography gate",
        ),
        "docs/README.md": (
            "## Current context",
            "## Citation, computation, and verification",
        ),
    }
    for relative, headings in role_headings.items():
        path = project_root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [heading for heading in headings if heading not in text]
        if missing:
            gaps.append(
                f"restore unified role headings in {relative}: " + ", ".join(missing)
            )
    context_path = project_root / context_file
    if context_path.is_file():
        context_text = context_path.read_text(encoding="utf-8", errors="replace")
        if not any(
            heading in context_text
            for heading in (
                "## Claim status and evidence",
                "## Claim-readiness gates",
            )
        ):
            gaps.append(
                f"restore claim-status heading in {context_file}: "
                "## Claim status and evidence "
                "(legacy ## Claim-readiness gates is also accepted)"
            )
    for relative in expected_packets:
        path = project_root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        positions = [text.find(heading) for heading in STANDARD_PACKET_HEADINGS]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            gaps.append(
                f"restore the ordered topic-packet heading contract in {relative}"
            )
    return gaps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--root-tex", type=Path)
    parser.add_argument("--bibliography", type=Path)
    parser.add_argument(
        "--adopt",
        action="store_true",
        help="Preserve every existing guidance file and manifest; create only missing files",
    )
    parser.add_argument(
        "--mature-research",
        action="store_true",
        help="Deprecated compatibility alias; the unified default already includes it",
    )
    parser.add_argument(
        "--with-calculation-layout",
        action="store_true",
        help="Deprecated compatibility alias; the unified default already includes it",
    )
    parser.add_argument(
        "--with-research-notices",
        action="store_true",
        help=(
            "Explicitly enable and create the optional human-facing "
            "RESEARCH_NOTICES.md navigation file"
        ),
    )
    parser.add_argument(
        "--profile",
        choices=("generic", *DOMAIN_PROFILES),
        default="generic",
        help="Generate generic guidance or a selected domain starter",
    )
    parser.add_argument(
        "--adapter",
        action="append",
        default=[],
        choices=("latexmk", "jupyter", "sympy", "mathematica", "slurm"),
        help="Generate an optional reviewable environment adapter; may be repeated",
    )
    parser.add_argument(
        "--bootstrap-environment",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Create env/ on apply (default for fresh scaffolds, disabled by "
            "default with --adopt)"
        ),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"error: project root is not a directory: {project_root}", file=sys.stderr)
        return 2
    if args.force and not args.apply:
        print("error: --force requires --apply", file=sys.stderr)
        return 2
    if args.force and args.adopt:
        print(
            "error: --adopt and --force are mutually exclusive; adoption never overwrites",
            file=sys.stderr,
        )
        return 2
    bootstrap_environment = (
        not args.adopt
        if args.bootstrap_environment is None
        else args.bootstrap_environment
    )

    try:
        existing_manifest = load_existing_manifest(project_root)
        scaffold_creates_root = False
        if args.root_tex:
            root_tex = inside(project_root, project_root / args.root_tex)
            if not root_tex.is_file():
                fail(f"root TeX file does not exist: {args.root_tex}")
        else:
            configured_root = configured_project_path(
                project_root, existing_manifest, "manuscript", "root_tex",
            )
            if configured_root:
                root_tex = configured_root
            elif not any(project_root.rglob("main.tex")):
                root_tex = project_root / "paper/main.tex"
                scaffold_creates_root = True
            else:
                root_tex = discover_root_tex(project_root)
            if not root_tex.is_file() and not scaffold_creates_root:
                fail(f"configured root TeX file does not exist: {root_tex}")
        if scaffold_creates_root:
            files, warnings = [root_tex], []
        else:
            files, warnings = include_graph(root_tex, project_root)
        if args.bibliography is None:
            configured_bibliography = configured_project_path(
                project_root, existing_manifest, "manuscript", "bibliography",
            )
            if configured_bibliography is not None:
                if not configured_bibliography.is_file():
                    fail(
                        "configured bibliography does not exist: "
                        f"{configured_bibliography.relative_to(project_root)}"
                    )
                bibliography = configured_bibliography.relative_to(project_root).as_posix()
            elif scaffold_creates_root:
                bibliography = "paper/references.bib"
            else:
                bibliography = discover_bibliography(files, project_root, None)
        else:
            bibliography = discover_bibliography(
                files, project_root, args.bibliography,
            )
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        project_python, environment_selection_warnings = select_project_python(
            project_root,
            existing_manifest,
            bootstrap_environment=bootstrap_environment,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root_rel = root_tex.relative_to(project_root).as_posix()
    research_path = project_root / "RESEARCH_PLAN.md"
    research_notices_path = project_root / "RESEARCH_NOTICES.md"
    research_notices_enabled = (
        args.with_research_notices or research_notices_path.is_file()
    )
    context_path = root_tex.parent / "MANUSCRIPT_CONTEXT.md"
    context_rel = context_path.relative_to(project_root).as_posix()
    section_relatives = (
        "paper/sections/introduction.tex",
        "paper/sections/formalism.tex",
        "paper/sections/methods.tex",
        "paper/sections/results.tex",
        "paper/sections/discussion.tex",
        "paper/sections/conclusion.tex",
    )
    if scaffold_creates_root:
        files = [root_tex, *(project_root / relative for relative in section_relatives)]
    include_map = "\n".join(
        f"- `{path.relative_to(project_root).as_posix()}`" for path in files
    )
    existing_packets = [
        path
        for path in sorted((project_root / "docs/context").glob("*.md"))
        if path.name != "README.md"
    ]
    preserve_existing_packets = args.adopt and bool(existing_packets)
    packet_relatives = (
        [path.relative_to(project_root).as_posix() for path in existing_packets]
        if preserve_existing_packets
        else ["docs/context/project-overview.md"]
    )
    context_config = f"""[context]
result_index = "SCIENTIFIC_PROGRESS.md"
packets = {json.dumps(packet_relatives)}
required_packet_headings = {json.dumps(STANDARD_PACKET_HEADINGS)}
result_index_max_bytes = 16384
default_context_max_bytes = 30720
packet_max_bytes = 24576
"""
    selected_adapters = list(dict.fromkeys(("latexmk", *args.adapter)))
    optional_adapter_inputs = {
        "jupyter": ["verification/verify_notebook.ipynb"],
        "sympy": ["verification/verify_sympy.py"],
        "mathematica": ["verification/verify_mathematica.wl"],
        "slurm": ["verification/slurm_worker.py", "verification/verify.sbatch"],
    }
    profile_inputs = []
    if args.profile in DOMAIN_PROFILES:
        profile_inputs = [
            (
                "HEP_ASTROPHYSICS_PROFILE.md"
                if args.profile == "hep-astrophysics"
                else "AXION_PHENOMENOLOGY_PROFILE.md"
            ),
            "notation.json",
        ]
    unified_inputs = [
        *UNIFIED_INPUT_PATHS,
        *(["RESEARCH_NOTICES.md"] if research_notices_enabled else []),
        *(path.relative_to(project_root).as_posix() for path in files),
        context_rel,
        *packet_relatives,
        *([bibliography] if bibliography else []),
        *profile_inputs,
        *(
            relative
            for adapter in selected_adapters
            for relative in optional_adapter_inputs.get(adapter, ())
        ),
    ]
    unified_inputs = list(dict.fromkeys(unified_inputs))
    profile_file = profile_inputs[0] if profile_inputs else ""
    if profile_file:
        profile_convention_index = f"`{profile_file}`"
        profile_convention_block = (
            f"Use `{profile_file}` as the explicit input and convention contract. "
            "Unresolved entries are not implicit assumptions."
        )
    else:
        profile_convention_index = "Not configured"
        profile_convention_block = (
            "No domain profile is configured. Add a reviewed convention and input "
            "contract before a claim depends on domain-specific units, priors, or data."
        )
    if research_notices_enabled:
        research_notice_guidance = (
            "Human-facing research notices are enabled at `RESEARCH_NOTICES.md`. "
            "Use them only for consequential developments whose omission could "
            "distort the mainline, cause a costly stopped route to be repeated, "
            "or hide a decision-changing result. Let the nearest useful scientific "
            "adjudication finish, coalesce related findings, and keep notices as "
            "navigation rather than evidence. In multi-agent work, only the primary "
            "agent or designated integrator edits the project-wide file."
        )
        research_notice_docs_guidance = (
            "[RESEARCH_NOTICES.md](../RESEARCH_NOTICES.md) is enabled as optional "
            "human-facing navigation. Reconcile every notice with its linked "
            "authoritative evidence before relying on it."
        )
    else:
        research_notice_guidance = (
            "No project-wide research notice log is enabled. Return a candidate "
            "notice in the response when useful, but do not create or update a "
            "global notice artifact unless the user explicitly opts in."
        )
        research_notice_docs_guidance = (
            "Project-wide research notices are disabled. Orientation remains "
            "available from the result index, topic packets, and authoritative "
            "evidence without a separate attention log."
        )
    adapter_guidance = (
        "The default LaTeX adapter is documented in `ADAPTERS.md`. "
        + (
            "Review the additional generated adapters there before running them."
            if len(selected_adapters) > 1
            else "No additional execution adapter was selected."
        )
    )
    root_packet_index = "\n".join(
        f"- {markdown_link(Path(relative).name, relative)}: "
        "registered bounded topic packet."
        for relative in packet_relatives
    )
    docs_packet_index = "\n".join(
        f"- {markdown_link(Path(relative).name, f'context/{Path(relative).name}')}: "
        "registered bounded topic packet."
        for relative in packet_relatives
    )
    context_packet_index = "\n".join(
        f"- {markdown_link(Path(relative).name, Path(relative).name)}: "
        "registered bounded topic packet."
        for relative in packet_relatives
    )
    initial_packet_link = markdown_link(
        Path(packet_relatives[0]).name,
        packet_relatives[0],
    )
    sync_rules = f"""[[sync.rules]]
sources = ["**/*.tex"]
companions = [{json.dumps(context_rel)}]
reason = "Review when the include graph, section responsibilities, narrative dependencies, or claim status changed."
required = false
anchors = {{ {json.dumps(context_rel)} = ["## Include order", "## Section guide"] }}

[[sync.rules]]
sources = ["calculations/**/*.py", "calculations/**/*.jl", "calculations/**/*.m", "calculations/**/*.ipynb"]
companions = ["SCIENTIFIC_PROGRESS.md"]
reason = "Review research context only when calculation behavior changes a named result, evidence level, or durable decision."
required = false
anchors = {{ "SCIENTIFIC_PROGRESS.md" = ["## Retained result catalogue", "## Maintenance contract"] }}

[[sync.rules]]
sources = ["**/*.bib"]
companions = ["CITATION_PLAN.md"]
reason = "Review the source-to-claim ledger whenever bibliography coverage or rationale changes."
required = false
anchors = {{ "CITATION_PLAN.md" = ["## Source and coverage ledger", "## Bibliography gate"] }}

[[sync.rules]]
sources = ["verification/**"]
companions = ["SCIENTIFIC_PROGRESS.md"]
reason = "Review scientific status only when executable coverage changes a named result or durable decision."
required = false
anchors = {{ "SCIENTIFIC_PROGRESS.md" = ["## Retained result catalogue"] }}

[[sync.rules]]
sources = ["configs/**", "*_PROFILE.md", "notation.json"]
companions = [{json.dumps(context_rel)}]
reason = "Review affected definitions when scientific inputs, conventions, units, or canonical symbols change."
required = false
anchors = {{ {json.dumps(context_rel)} = ["## Cross-artifact dependencies"] }}"""
    project_python_token = shell_token(project_python)
    if bootstrap_environment:
        environment_setup_guidance = f"""For a fresh project, `scaffold_project.py --apply` creates `env/` with the
interpreter that runs the scaffold. It uses standard-library `venv`, disables
system site packages, and installs no project dependencies.

To recreate the environment intentionally, remove or archive the old
environment first, then run from the repository root:

```bash
python3 -m venv env
{project_python_token} -m pip install -r requirements.txt
```"""
    else:
        environment_setup_guidance = f"""The scaffold preserved the existing environment state and did not create,
replace, or install into a virtual environment. Generated Python commands use:

```text
{project_python}
```

Recreate and install dependencies through the repository's established
environment manager. If this interpreter is only a temporary fallback, replace
it in the manifest and guidance after selecting the canonical project
environment."""
    values = {
        "PROJECT_NAME": project_root.name,
        "TEX_ROOT": root_rel,
        "BIB_FILE": bibliography or "(not detected)",
        "PROFILE_NAME": args.profile,
        "PROFILE_CONVENTION_BLOCK": profile_convention_block,
        "PROFILE_CONVENTION_INDEX": profile_convention_index,
        "LATEX_BUILD_COMMAND": shlex.join(latexmk_command(root_rel)),
        "ADAPTER_GUIDANCE": adapter_guidance,
        "ROOT_PACKET_INDEX": root_packet_index,
        "DOCS_PACKET_INDEX": docs_packet_index,
        "CONTEXT_PACKET_INDEX": context_packet_index,
        "INITIAL_PACKET_LINK": initial_packet_link,
        "INPUT_PATHS_TOML": json.dumps(unified_inputs),
        "VERIFICATION_COMMANDS_TOML": "",
        "GENERATED_ARTIFACTS_TOML": "[]",
        "PROFILE_TABLES": "",
        "SYNC_RULES_TOML": sync_rules,
        "CONTEXT_FILE": context_rel,
        "INCLUDE_MAP": include_map,
        "ROOT_TEX_TOML": json.dumps(root_rel),
        "BIBLIOGRAPHY_TOML": json.dumps(bibliography),
        "CONTEXT_CONFIG_TOML": context_config.rstrip(),
        "SELECTED_ADAPTERS": ", ".join(selected_adapters),
        "ENVIRONMENT_SETUP_GUIDANCE": environment_setup_guidance,
        "PROJECT_PYTHON": project_python_token,
        "PROJECT_PYTHON_TOML": json.dumps(project_python),
        "RESEARCH_NOTICE_GUIDANCE": research_notice_guidance,
        "RESEARCH_NOTICE_DOCS_GUIDANCE": research_notice_docs_guidance,
    }
    adapter_commands: list[list[str]] = [
        [project_python, "verification/verify_all.py"],
    ]
    for adapter in selected_adapters:
        if adapter == "latexmk":
            adapter_commands.append(latexmk_command(root_rel))
        elif adapter == "jupyter":
            adapter_commands.append(
                [project_python, "-m", "jupyter", "nbconvert", "--execute", "--to", "notebook", "--inplace", "verification/verify_notebook.ipynb"]
            )
        elif adapter == "sympy":
            adapter_commands.append(
                [project_python, "verification/verify_sympy.py"]
            )
        elif adapter == "mathematica":
            adapter_commands.append(["wolframscript", "-file", "verification/verify_mathematica.wl"])
    values["VERIFICATION_COMMANDS_TOML"] = json.dumps(adapter_commands)
    outputs = {
        project_root / "AGENTS.md": render("AGENTS.md.template", values),
        research_path: render("RESEARCH_PLAN.md.template", values),
        context_path: render("MANUSCRIPT_CONTEXT.md.template", values),
        project_root / "manuscript-project.toml": render(
            "manuscript-project.toml.template", values
        ),
        project_root / "SCIENTIFIC_PROGRESS.md": render(
            "SCIENTIFIC_PROGRESS.md.template", values
        ),
        project_root / "CITATION_PLAN.md": render(
            "CITATION_PLAN.md.template", values
        ),
        project_root / "docs/README.md": render(
            "docs/README.md.template", values
        ),
        project_root / "docs/ENVIRONMENT.md": render(
            "docs/ENVIRONMENT.md.template", values
        ),
        project_root / "docs/derivations/README.md": render(
            "docs/derivations/README.md.template", values
        ),
        project_root / "docs/context/README.md": render(
            "docs/context/README.md.template", values
        ),
        project_root / "calculations/README.md": render(
            "calculations/README.md.template", values
        ),
        project_root / "configs/README.md": render(
            "configs/README.md.template", values
        ),
        project_root / "verification/README.md": render(
            "verification/README.md.template", values
        ),
        project_root / "verification/verify_all.py": render(
            "verification/verify_all.py.template", values
        ),
        project_root / "verification/verify_context_architecture.py": render(
            "verification/verify_context_architecture.py.template", values
        ),
        project_root / ".gitignore": render(".gitignore.template", values),
        project_root / "requirements.txt": render(
            "requirements.txt.template", values
        ),
        project_root / "requirements-runtime.txt": render(
            "requirements-runtime.txt.template", values
        ),
        project_root / "requirements-verification.txt": render(
            "requirements-verification.txt.template", values
        ),
        project_root / "requirements-plot.txt": render(
            "requirements-plot.txt.template", values
        ),
    }
    outputs[project_root / "docs/context/project-overview.md"] = render(
        "TOPIC_PACKET.md.template", values
    )
    if args.with_research_notices and not research_notices_path.exists():
        outputs[research_notices_path] = render(
            "RESEARCH_NOTICES.md.template", values
        )
    calculation_templates = {
        "calculations/__init__.py.template": "calculations/__init__.py",
        "calculations/core/__init__.py.template": "calculations/core/__init__.py",
        "calculations/models/__init__.py.template": "calculations/models/__init__.py",
        "calculations/workflows/__init__.py.template": "calculations/workflows/__init__.py",
        "calculations/cli/__init__.py.template": "calculations/cli/__init__.py",
    }
    for template_name, relative in calculation_templates.items():
        outputs[project_root / relative] = render(template_name, values)

    if scaffold_creates_root:
        root_template = (
            "profiles/hep-astrophysics/main.tex.template"
            if args.profile in DOMAIN_PROFILES
            else "paper/main.tex.template"
        )
        bibliography_template = (
            "profiles/hep-astrophysics/references.bib.template"
            if args.profile in DOMAIN_PROFILES
            else "paper/references.bib.template"
        )
        manuscript_outputs = {
            root_tex: render(root_template, values),
            project_root / "paper/references.bib": render(
                bibliography_template, values
            ),
        }
        for relative in section_relatives:
            name = Path(relative).stem
            manuscript_outputs[project_root / relative] = render(
                f"paper/sections/{name}.tex.template", values
            )
        outputs.update(manuscript_outputs)

    if args.profile in DOMAIN_PROFILES:
        profile_file_names = {
            "hep-astrophysics": "HEP_ASTROPHYSICS_PROFILE.md",
            "axion-phenomenology": "AXION_PHENOMENOLOGY_PROFILE.md",
        }
        profile_outputs = {
            project_root / profile_file_names[args.profile]: render(
                f"profiles/{args.profile}/PROFILE.md.template", values
            ),
            project_root / "notation.json": render(
                f"profiles/{args.profile}/notation.json.template", values
            ),
        }
        outputs.update(profile_outputs)

    adapter_templates = {
        "latexmk": ("adapters/latexmkrc.template", ".latexmkrc"),
        "jupyter": ("adapters/notebook_wrapper.ipynb.template", "verification/verify_notebook.ipynb"),
        "sympy": ("adapters/verify_sympy.py.template", "verification/verify_sympy.py"),
        "mathematica": ("adapters/verify_mathematica.wl.template", "verification/verify_mathematica.wl"),
    }
    for adapter in selected_adapters:
        if adapter == "slurm":
            for template_name, relative in (
                ("adapters/slurm_worker.py.template", "verification/slurm_worker.py"),
                ("adapters/verify.sbatch.template", "verification/verify.sbatch"),
            ):
                path = project_root / relative
                outputs[path] = render(template_name, values)
        else:
            template_name, relative = adapter_templates[adapter]
            path = project_root / relative
            outputs[path] = render(template_name, values)
    path = project_root / "ADAPTERS.md"
    outputs[path] = render("adapters/ADAPTERS.md.template", values)
    guidance_paths = tuple(outputs)
    preserved: list[Path] = []
    preserved_packet_count = 0
    environment_specs: list[str] = []
    if args.adopt:
        if preserve_existing_packets:
            outputs.pop(project_root / "docs/context/project-overview.md", None)
            preserved_packet_count = len(existing_packets)
        environment_specs = existing_environment_specs(project_root)
        preserved = [path for path in guidance_paths if path.exists()]
        outputs = {
            path: content
            for path, content in outputs.items()
            if path not in preserved
        }

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if args.mature_research:
        print(
            "WARNING: --mature-research is deprecated and has no effect; "
            "bounded research context is part of the unified default",
            file=sys.stderr,
        )
    if args.with_calculation_layout:
        print(
            "WARNING: --with-calculation-layout is deprecated and has no effect; "
            "the calculation package is part of the unified default",
            file=sys.stderr,
        )
    external_dependencies = {
        "latexmk": shutil.which("latexmk"),
        "mathematica": shutil.which("wolframscript"),
        "slurm": shutil.which("sbatch"),
    }
    for adapter in selected_adapters:
        if adapter in {"jupyter", "sympy"}:
            print(
                f"WARNING: optional Python dependency for {adapter} must be "
                f"reviewed, declared, and installed for {project_python}; "
                "host availability is not used as project provenance",
                file=sys.stderr,
            )
        elif not external_dependencies[adapter]:
            print(
                f"WARNING: optional dependency for {adapter} was not found; "
                "generated files remain reviewable but are not runnable",
                file=sys.stderr,
            )
    for warning in environment_selection_warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if preserved_packet_count:
        print(f"ADOPT existing topic packets: {preserved_packet_count}")
    if environment_specs:
        print(
            "ADOPT existing environment specifications: "
            + ", ".join(environment_specs)
        )
    environment_state = "skip"
    if bootstrap_environment:
        try:
            environment_state = inspect_environment_target(project_root)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if environment_state == "create":
            print(
                "ENVIRONMENT PLAN: create env/ with "
                f"{sys.executable} (Python {sys.version_info.major}."
                f"{sys.version_info.minor}.{sys.version_info.micro}); "
                "do not install packages"
            )
        else:
            print("ENVIRONMENT PLAN: preserve existing env/ without modification")
    elif args.adopt:
        print(
            "ENVIRONMENT PLAN: adoption preserves environment state; "
            f"generated commands use {project_python}"
        )
    else:
        print(
            "ENVIRONMENT PLAN: skipped by --no-bootstrap-environment; "
            f"generated commands use {project_python}"
        )
    if args.adopt and existing_manifest:
        for gap in manifest_migration_gaps(
            existing_manifest,
            unified_inputs,
            packet_relatives,
            project_root,
            context_rel,
        ):
            print(f"MIGRATION REVIEW: {gap}")
    for path in preserved:
        text = path.read_text(encoding="utf-8", errors="replace")
        expected_by_path = {
            project_root / "AGENTS.md": {
                "root TeX": root_rel,
                "bibliography": bibliography,
                "research plan": "RESEARCH_PLAN.md",
                "project manifest": "manuscript-project.toml",
                "project orientation": "$orient-scientific-project",
                **(
                    {"research notices": "RESEARCH_NOTICES.md"}
                    if research_notices_enabled
                    else {}
                ),
            },
            context_path: {
                "root TeX": root_rel,
                "bibliography": bibliography,
                "research plan": "RESEARCH_PLAN.md",
            },
            research_path: {},
            project_root / "manuscript-project.toml": {
                "root TeX": root_rel,
                "bibliography": bibliography,
            },
            project_root / "SCIENTIFIC_PROGRESS.md": {},
            project_root / "docs/context/project-overview.md": {},
        }
        expected = expected_by_path.get(path, {})
        missing = [
            label
            for label, token in expected.items()
            if token
            and token not in text
            and not (path == context_path and Path(token).name in text)
        ]
        detail = f"; review missing references: {', '.join(missing)}" if missing else ""
        print(f"ADOPT existing: {path.relative_to(project_root)}{detail}")
    for path, content in outputs.items():
        relative = path.relative_to(project_root)
        state = "overwrite" if path.exists() else "create"
        print(f"\n--- {state}: {relative}\n{content.rstrip()}\n")

    if not args.apply:
        mode = " --adopt" if args.adopt else ""
        mature = " --mature-research" if args.mature_research else ""
        calculation = (
            " --with-calculation-layout" if args.with_calculation_layout else ""
        )
        notices = " --with-research-notices" if args.with_research_notices else ""
        profile = f" --profile {args.profile}" if args.profile != "generic" else ""
        adapters = "".join(f" --adapter {item}" for item in dict.fromkeys(args.adapter))
        if args.bootstrap_environment is True:
            environment = " --bootstrap-environment"
        elif args.bootstrap_environment is False:
            environment = " --no-bootstrap-environment"
        else:
            environment = ""
        print(
            f"Preview only; rerun with --apply{mode}{mature}{calculation}{notices}{profile}"
            f"{adapters}{environment} "
            "to write proposed files."
        )
        return 0
    blocked = [path for path in outputs if path.exists() and not args.force]
    if blocked:
        for path in blocked:
            print(
                f"error: refusing to overwrite {path.relative_to(project_root)}",
                file=sys.stderr,
            )
        return 1
    try:
        preflight_output_paths(project_root, tuple(outputs))
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"WROTE {path.relative_to(project_root)}")
    except (OSError, ValueError) as exc:
        print(f"error: could not write scaffold outputs: {exc}", file=sys.stderr)
        return 2
    if environment_state == "create":
        try:
            interpreter = create_environment(project_root)
        except ValueError as exc:
            print(
                "error: scaffold files were written, but environment bootstrap "
                f"failed: {exc}; rerun with --adopt --bootstrap-environment --apply",
                file=sys.stderr,
            )
            return 2
        print(f"CREATED virtual environment: env/ ({interpreter})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
