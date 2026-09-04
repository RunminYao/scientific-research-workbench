#!/usr/bin/env python3
"""Preview or create a citation-plan ledger in a manuscript project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


TEMPLATE = (
    Path(__file__).resolve().parents[1] / "assets" / "CITATION_PLAN.md.template"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("CITATION_PLAN.md"))
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
    output = (root / args.output).resolve(strict=False)
    try:
        output.relative_to(root)
    except ValueError:
        print("error: output must stay inside project root", file=sys.stderr)
        return 2
    content = TEMPLATE.read_text(encoding="utf-8")
    print(f"--- {'overwrite' if output.exists() else 'create'}: {output.relative_to(root)}")
    print(content)
    if not args.apply:
        print("Preview only; rerun with --apply to write the file.")
        return 0
    if output.exists() and not args.force:
        print(f"error: refusing to overwrite {output.relative_to(root)}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"WROTE {output.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
