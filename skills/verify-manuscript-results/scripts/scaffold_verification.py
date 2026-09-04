#!/usr/bin/env python3
"""Preview or create a project-local manuscript verification harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"
DEFAULT_FILES = {
    "verification_helpers.py.template": "verification_helpers.py",
    "verify_all.py.template": "verify_all.py",
}
EXAMPLE_FILES = {
    "verify_formulas.py.template": "verify_formulas.py",
    "verify_numerics.py.template": "verify_numerics.py",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--directory", type=Path, default=Path("verification"))
    parser.add_argument("--with-examples", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"error: project root is not a directory: {root}", file=sys.stderr)
        return 2
    if args.force and not args.apply:
        print("error: --force requires --apply", file=sys.stderr)
        return 2
    target_dir = (root / args.directory).resolve(strict=False)
    try:
        target_dir.relative_to(root)
    except ValueError:
        print("error: verification directory must stay inside project root", file=sys.stderr)
        return 2

    selected = dict(DEFAULT_FILES)
    if args.with_examples:
        selected.update(EXAMPLE_FILES)
    outputs = {
        target_dir / destination: (ASSETS / source).read_text(encoding="utf-8")
        for source, destination in selected.items()
    }
    for path, content in outputs.items():
        try:
            path.resolve(strict=False).relative_to(root)
        except ValueError:
            print(f"error: output escapes project root: {path}", file=sys.stderr)
            return 2
        state = "overwrite" if path.exists() else "create"
        print(f"\n--- {state}: {path.relative_to(root)}\n{content.rstrip()}\n")
    if not args.apply:
        print("Preview only; rerun with --apply to write these files.")
        return 0
    blocked = [path for path in outputs if path.exists() and not args.force]
    if blocked:
        for path in blocked:
            print(f"error: refusing to overwrite {path.relative_to(root)}", file=sys.stderr)
        return 1
    target_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        if path.name.startswith("verify_"):
            path.chmod(path.stat().st_mode | 0o111)
        print(f"WROTE {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
