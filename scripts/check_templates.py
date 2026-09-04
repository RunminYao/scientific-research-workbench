#!/usr/bin/env python3
"""Render every versioned template with representative values and validate it."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

import yaml


PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
VALUES = {
    "PROJECT_NAME": "representative-project",
    "TEX_ROOT": "paper/main.tex",
    "BIB_FILE": "paper/references.bib",
    "PROFILE_NAME": "generic",
    "PROFILE_CONVENTION_BLOCK": "No domain profile is configured.",
    "PROFILE_CONVENTION_INDEX": "Not configured",
    "LATEX_BUILD_COMMAND": (
        "latexmk -cd -pdf -interaction=nonstopmode -halt-on-error "
        "-outdir=../build paper/main.tex"
    ),
    "ADAPTER_GUIDANCE": "Review the generated adapter contract.",
    "ROOT_PACKET_INDEX": (
        "- [project-overview.md](docs/context/project-overview.md): "
        "registered bounded topic packet."
    ),
    "DOCS_PACKET_INDEX": (
        "- [project-overview.md](context/project-overview.md): "
        "registered bounded topic packet."
    ),
    "CONTEXT_PACKET_INDEX": (
        "- [project-overview.md](project-overview.md): "
        "registered bounded topic packet."
    ),
    "INITIAL_PACKET_LINK": (
        "[project-overview.md](<docs/context/project-overview.md>)"
    ),
    "INPUT_PATHS_TOML": (
        '["AGENTS.md", "SCIENTIFIC_PROGRESS.md", "paper/main.tex", '
        '"paper/MANUSCRIPT_CONTEXT.md", "paper/references.bib"]'
    ),
    "VERIFICATION_COMMANDS_TOML": (
        '[["env/bin/python", "verification/verify_all.py"], '
        '["latexmk", "-cd", "-pdf", "-outdir=../build", "paper/main.tex"]]'
    ),
    "GENERATED_ARTIFACTS_TOML": (
        '[{ source = "paper/main.tex", outputs = ["build/main.pdf"] }]'
    ),
    "PROFILE_TABLES": "",
    "SYNC_RULES_TOML": (
        '[[sync.rules]]\n'
        'sources = ["**/*.tex"]\n'
        'companions = ["paper/MANUSCRIPT_CONTEXT.md"]\n'
        'reason = "Review the manuscript map."\n'
        "required = false\n"
    ),
    "ROOT_TEX": "paper/main.tex",
    "BIBLIOGRAPHY": "paper/references.bib",
    "CONTEXT_FILE": "paper/MANUSCRIPT_CONTEXT.md",
    "INCLUDE_MAP": "- `paper/main.tex`",
    "RESEARCH_CONTEXT_ROUTING": "Read the project context.",
    "RESULT_INDEX_ENTRY": "- Result index: `SCIENTIFIC_PROGRESS.md`",
    "CALCULATION_LAYOUT_GUIDANCE": "## Calculation layout\n\nUse reviewed modules.",
    "ROOT_TEX_TOML": '"paper/main.tex"',
    "BIBLIOGRAPHY_TOML": '"paper/references.bib"',
    "CONTEXT_FILE_TOML": '"paper/MANUSCRIPT_CONTEXT.md"',
    "VERIFICATION_INPUTS_TOML": '["paper/main.tex", "paper/references.bib"]',
    "CONTEXT_DOCS_TOML": '["AGENTS.md"]',
    "CONTEXT_CONFIG_TOML": '[context]\ndefault_context_max_bytes = 30720',
    "CODE_COMPANIONS_TOML": '["AGENTS.md"]',
    "CODE_ANCHORS_TOML": '{ "AGENTS.md" = ["## Manuscript map"] }',
    "VERIFICATION_DEFAULT_TOML": '[["python3", "verification/check.py"]]',
    "SELECTED_ADAPTERS": "latexmk, sympy",
    "ENVIRONMENT_SETUP_GUIDANCE": (
        "Create `env/` with standard-library venv, then install reviewed "
        "requirements."
    ),
    "PROJECT_PYTHON": "env/bin/python",
    "PROJECT_PYTHON_TOML": '"env/bin/python"',
    "RESEARCH_NOTICE_GUIDANCE": (
        "No project-wide research notice log is enabled."
    ),
    "RESEARCH_NOTICE_DOCS_GUIDANCE": (
        "Project-wide research notices are disabled."
    ),
}


def render(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in VALUES.items():
        text = text.replace("{{" + key + "}}", value)
    remaining = PLACEHOLDER_RE.findall(text)
    if remaining:
        raise ValueError(f"unresolved placeholders: {sorted(set(remaining))}")
    return text


def check_templates(root: Path) -> list[str]:
    errors: list[str] = []
    templates = sorted((root / "skills").rglob("*.template"))
    if not templates:
        return ["no templates found"]
    for path in templates:
        relative = path.relative_to(root)
        try:
            content = render(path)
            if not content.strip():
                raise ValueError("rendered template is empty")
            target_suffix = Path(path.stem).suffix
            if target_suffix == ".py":
                compile(content, str(relative), "exec")
            elif target_suffix == ".toml":
                tomllib.loads(content)
            elif target_suffix in {".yaml", ".yml"}:
                yaml.safe_load(content)
            elif target_suffix in {".json", ".ipynb"}:
                document = json.loads(content)
                if target_suffix == ".ipynb":
                    for index, cell in enumerate(document.get("cells", []), start=1):
                        if cell.get("cell_type") == "code":
                            compile(
                                "".join(cell.get("source", [])),
                                f"{relative}:cell-{index}",
                                "exec",
                            )
            elif target_suffix == ".md" and not re.search(r"^#", content, re.MULTILINE):
                raise ValueError("Markdown template has no heading")
        except (OSError, UnicodeError, SyntaxError, ValueError, tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = check_templates(args.project_root.resolve())
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print("Rendered templates: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
