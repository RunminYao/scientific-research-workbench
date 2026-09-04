#!/usr/bin/env python3
"""Check the plugin and host prerequisites without executing project code."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MIN_CODEX = (0, 144, 6)


def version_tuple(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
    return tuple(map(int, match.groups())) if match else None


def check(root: Path, project_root: Path | None) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    def add(name: str, status: str, detail: str) -> None:
        results.append({"name": name, "status": status, "detail": detail})

    supported_python = (3, 11) <= sys.version_info[:2] <= (3, 13)
    add("python", "pass" if supported_python else "error", sys.version.split()[0])
    dependencies_ready = True
    constraints = {
        "pybtex": ((0, 26, 1), (0, 27, 0)),
        "jsonschema": ((4, 23, 0), (5, 0, 0)),
        "PyYAML": ((6, 0, 2), (7, 0, 0)),
    }
    for distribution, (minimum, maximum) in constraints.items():
        try:
            version = importlib.metadata.version(distribution)
            parsed = version_tuple(version)
            supported = parsed is not None and minimum <= parsed < maximum
            if not supported:
                dependencies_ready = False
            add(f"dependency:{distribution}", "pass" if supported else "error", version)
        except importlib.metadata.PackageNotFoundError:
            dependencies_ready = False
            add(f"dependency:{distribution}", "error", "not installed")

    codex = shutil.which("codex")
    if codex:
        try:
            completed = subprocess.run(
                [codex, "--version"], capture_output=True, text=True, timeout=10, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            add("codex", "error", str(exc))
        else:
            shown = (completed.stdout or completed.stderr).strip()
            parsed = version_tuple(shown)
            add("codex", "pass" if parsed and parsed >= MIN_CODEX else "error", shown)
    else:
        add("codex", "error", "not found; Codex CLI >=0.144.6 is required to use the plugin")

    if dependencies_ready:
        from check_templates import check_templates
        from validate_plugin import validate_plugin

        for error in validate_plugin(root):
            add("plugin", "error", error)
        if not any(item["name"] == "plugin" for item in results):
            add("plugin", "pass", "manifest, marketplace, skills, agents, and resources")
        for error in check_templates(root):
            add("templates", "error", error)
        if not any(item["name"] == "templates" for item in results):
            add("templates", "pass", "all representative renders")
    else:
        add("plugin", "error", "validation unavailable until core dependencies are installed")
        add("templates", "error", "validation unavailable until core dependencies are installed")

    try:
        sympy_version = importlib.metadata.version("sympy")
    except importlib.metadata.PackageNotFoundError:
        sympy_version = "not found"
    add("optional:sympy", "pass" if sympy_version != "not found" else "warning", sympy_version)
    tools = ("latexmk", "jupyter", "wolframscript", "sbatch")
    for tool in tools:
        add(f"optional:{tool}", "pass" if shutil.which(tool) else "warning", shutil.which(tool) or "not found")
    if project_root:
        add("project-root", "pass" if project_root.is_dir() else "error", str(project_root))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    results = check(root, args.project_root.resolve() if args.project_root else None)
    if args.json:
        print(json.dumps({"checks": results}, indent=2))
    else:
        for item in results:
            print(f"{item['status'].upper()}: {item['name']}: {item['detail']}")
    return 1 if any(item["status"] == "error" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
