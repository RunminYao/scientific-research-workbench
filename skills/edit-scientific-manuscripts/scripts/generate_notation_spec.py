#!/usr/bin/env python3
"""Generate an audit_notation JSON specification from a LaTeX notation table."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def split_top_level(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(text):
        escaped = index > 0 and text[index - 1] == "\\"
        if char == "{" and not escaped:
            depth += 1
        elif char == "}" and not escaped:
            depth = max(0, depth - 1)
        elif char == delimiter and depth == 0 and not escaped:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def strip_math(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("$") and value.endswith("$"):
        return value[1:-1].strip()
    return value


def left_hand_symbols(cell: str) -> tuple[list[str], list[str]]:
    expression = strip_math(cell)
    aliases: list[str] = []
    if r"\equiv" in expression:
        left, right = expression.split(r"\equiv", 1)
        right = right.strip()
        if re.fullmatch(r"(?:\\[A-Za-z]+|[A-Za-z])(?:[_^]\{[^{}]+\})*", right):
            aliases.append(right)
    elif "=" in expression:
        left = expression.split("=", 1)[0]
    else:
        left = expression
    symbols = [value for value in split_top_level(left, ",") if value]
    return symbols, aliases


def style_variants(token: str) -> list[str]:
    variants: list[str] = []
    alternate = re.sub(
        r"_\{\\rm\s+([^{}]+)\}",
        lambda match: r"_{\mathrm{" + match.group(1) + "}}",
        token,
    )
    if alternate != token:
        variants.append(alternate)
    return variants


def rows(text: str) -> list[tuple[int, str]]:
    output: list[tuple[int, str]] = []
    buffer = ""
    start_line = 0
    in_tabular = False
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if r"\begin{tabular" in raw:
            in_tabular = True
            continue
        if r"\end{tabular" in raw:
            break
        if not in_tabular:
            continue
        clean = raw.strip()
        if not clean or clean.startswith("%"):
            continue
        if re.fullmatch(r"\\(?:toprule|midrule|bottomrule)(?:\[[^]]*\])?", clean):
            continue
        if not buffer:
            start_line = line_number
        buffer += (" " if buffer else "") + clean
        if re.search(r"(?<!\\)\\\\\s*$", buffer):
            row = re.sub(r"(?<!\\)\\\\\s*$", "", buffer).strip()
            if "&" in row:
                output.append((start_line, row))
            buffer = ""
    return output


def generate(
    table: Path,
    source_label: str | None = None,
    preview_paths: list[str] | None = None,
) -> dict:
    items: list[dict] = []
    seen: set[str] = set()
    text = table.read_text(encoding="utf-8", errors="replace")
    for line_number, row in rows(text):
        cells = split_top_level(row, "&")
        if len(cells) < 3 or strip_math(cells[0]).lower() == "symbol":
            continue
        symbols, aliases = left_hand_symbols(cells[0])
        meaning = cells[2].strip()
        for index, symbol in enumerate(symbols):
            if symbol in seen:
                continue
            seen.add(symbol)
            item_aliases = aliases if index == 0 else []
            items.append(
                {
                    "name": symbol,
                    "canonical": symbol,
                    "aliases": item_aliases,
                    "variants": style_variants(symbol),
                    "definition_patterns": [re.escape(meaning)],
                    "preview_paths": preview_paths or [],
                    "source": {
                        "table": source_label or str(table),
                        "line": line_number,
                    },
                }
            )
    if not items:
        raise ValueError("no notation rows found")
    return {"source": source_label or str(table), "items": items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Emit the notation-table source path relative to this project root",
    )
    parser.add_argument(
        "--preview-path",
        action="append",
        default=[],
        help="Glob for files whose pre-definition occurrences are previews",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.table.is_file():
        print(f"error: notation table does not exist: {args.table}", file=sys.stderr)
        return 2
    if args.force and not args.apply:
        print("error: --force requires --apply", file=sys.stderr)
        return 2
    try:
        table = args.table.resolve()
        source_label = None
        if args.project_root:
            project_root = args.project_root.resolve()
            source_label = table.relative_to(project_root).as_posix()
        payload = generate(table, source_label, args.preview_path)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if not args.output:
        sys.stdout.write(rendered)
        return 0
    output = args.output.resolve(strict=False)
    print(rendered, end="")
    if not args.apply:
        print(f"Preview only; rerun with --apply to write {output}.")
        return 0
    if output.exists() and not args.force:
        print(f"error: refusing to overwrite {output}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"WROTE {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
