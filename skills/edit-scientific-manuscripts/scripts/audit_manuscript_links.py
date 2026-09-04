#!/usr/bin/env python3
"""Audit LaTeX labels, references, graphics, and configured generated artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from shared.latex_scan import diagnostic_text, scan_tex_project  # noqa: E402


LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")
REF_RE = re.compile(
    r"\\(?:ref|eqref|autoref|cref|Cref|pageref)\*?\s*\{([^}]+)\}"
)
GRAPHICS_RE = re.compile(
    r"\\includegraphics\*?\s*(?:\[[^]]*\]\s*)?\{([^}]+)\}"
)
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\s*\{((?:\{[^{}]*\})+)\}")
GRAPHIC_DIR_RE = re.compile(r"\{([^{}]*)\}")
GRAPHIC_EXTENSIONS = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg")


def normalize_relative(root: Path, raw: str) -> Path:
    path = (root / raw).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {raw!r}") from exc
    return path


def resolve_graphic(
    raw: str,
    source_file: Path,
    project_root: Path,
    graphic_dirs: list[Path],
) -> Path | None:
    value = Path(raw)
    bases = [source_file.parent, project_root, *graphic_dirs]
    for base in bases:
        for extension in GRAPHIC_EXTENSIONS:
            candidate = (base / (str(value) + extension)).resolve(strict=False)
            try:
                candidate.relative_to(project_root)
            except ValueError:
                continue
            if candidate.is_file():
                return candidate
    return None


def load_artifacts(config: Path | None, project_root: Path) -> list[dict]:
    if config is None:
        return []
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read {config}: {exc}") from exc
    raw_items = data.get("artifacts", {}).get("generated", [])
    if not isinstance(raw_items, list):
        raise ValueError("artifacts.generated must be an array")
    items: list[dict] = []
    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"generated artifact {index} must be a table")
        source = raw.get("source")
        outputs = raw.get("outputs")
        if not isinstance(source, str) or not source:
            raise ValueError(f"generated artifact {index} needs source")
        if not isinstance(outputs, list) or not outputs or not all(
            isinstance(value, str) and value for value in outputs
        ):
            raise ValueError(f"generated artifact {index} needs string outputs")
        source_path = normalize_relative(project_root, source)
        output_paths = [normalize_relative(project_root, value) for value in outputs]
        items.append(
            {
                "source": source_path,
                "outputs": output_paths,
            }
        )
    return items


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def audit(
    root_tex: Path, project_root: Path, config: Path | None
) -> dict:
    scan = scan_tex_project(root_tex, project_root)
    lines = scan.lines
    labels: list[tuple[str, str, int]] = []
    references: list[tuple[str, str, int]] = []
    graphics: list[dict] = []
    graphic_dirs: list[Path] = [root_tex.parent]

    for source in lines:
        source_path = Path(source.path)
        for match in GRAPHICSPATH_RE.finditer(source.text):
            for raw_dir in GRAPHIC_DIR_RE.findall(match.group(1)):
                candidate = (source_path.parent / raw_dir).resolve(strict=False)
                try:
                    candidate.relative_to(project_root)
                except ValueError:
                    continue
                graphic_dirs.append(candidate)
        labels.extend(
            (match.group(1).strip(), source.path, source.line)
            for match in LABEL_RE.finditer(source.text)
        )
        for match in REF_RE.finditer(source.text):
            references.extend(
                (key.strip(), source.path, source.line)
                for key in match.group(1).split(",")
                if key.strip()
            )
        for match in GRAPHICS_RE.finditer(source.text):
            raw = match.group(1).strip()
            resolved = resolve_graphic(
                raw, source_path, project_root, graphic_dirs
            )
            graphics.append(
                {
                    "raw": raw,
                    "source": relative(source_path, project_root),
                    "line": source.line,
                    "resolved": relative(resolved, project_root)
                    if resolved
                    else None,
                }
            )

    label_counts = Counter(label for label, _, _ in labels)
    label_names = set(label_counts)
    reference_names = {label for label, _, _ in references}
    failures: list[str] = []
    warnings: list[str] = [diagnostic_text(item) for item in scan.diagnostics]
    duplicates = sorted(label for label, count in label_counts.items() if count > 1)
    undefined = sorted(reference_names - label_names)
    unreferenced = sorted(label_names - reference_names)
    missing_graphics = [
        f"{item['source']}:{item['line']} -> {item['raw']}"
        for item in graphics
        if item["resolved"] is None
    ]
    if duplicates:
        failures.append("duplicate labels: " + ", ".join(duplicates))
    if undefined:
        failures.append("undefined references: " + ", ".join(undefined))
    if missing_graphics:
        failures.append("missing graphics: " + "; ".join(missing_graphics))
    if unreferenced:
        warnings.append(
            f"{len(unreferenced)} labels are not referenced in the TeX include graph"
        )

    graphic_paths = {
        item["resolved"] for item in graphics if item["resolved"] is not None
    }
    artifacts = []
    for item in load_artifacts(config, project_root):
        source_exists = item["source"].is_file()
        outputs = []
        for output in item["outputs"]:
            output_relative = relative(output, project_root)
            output_exists = output.is_file()
            referenced = output_relative in graphic_paths
            outputs.append(
                {
                    "path": output_relative,
                    "exists": output_exists,
                    "referenced": referenced,
                }
            )
            if not output_exists:
                failures.append(f"generated output is missing: {output_relative}")
            elif not referenced:
                warnings.append(
                    f"generated output is not referenced by active TeX: {output_relative}"
                )
        if not source_exists:
            failures.append(
                "artifact generator is missing: " + relative(item["source"], project_root)
            )
        artifacts.append(
            {
                "source": relative(item["source"], project_root),
                "source_exists": source_exists,
                "outputs": outputs,
            }
        )

    return {
        "root": relative(root_tex, project_root),
        "complete": not bool(scan.diagnostics),
        "unsupported_syntax": [item.to_dict() for item in scan.diagnostics],
        "files": len({line.path for line in lines}),
        "labels": len(labels),
        "references": len(references),
        "graphics": graphics,
        "artifacts": artifacts,
        "failures": failures,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    root_tex = args.root.resolve()
    if not project_root.is_dir() or not root_tex.is_file():
        print("error: project root and root TeX must exist", file=sys.stderr)
        return 2
    try:
        root_tex.relative_to(project_root)
        config = None
        if args.config:
            config = normalize_relative(project_root, str(args.config))
        report = audit(root_tex, project_root, config)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"Files: {report['files']}; labels: {report['labels']}; "
            f"references: {report['references']}; graphics: {len(report['graphics'])}"
        )
        for failure in report["failures"]:
            print(f"FAIL: {failure}")
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
    return 1 if args.strict and (report["failures"] or not report["complete"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
