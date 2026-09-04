#!/usr/bin/env python3
"""Audit an optional bounded result index and two-hop topic-packet architecture."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path


LINK_RE = re.compile(r"(?<!!)\[[^]]+\]\((<[^>]+>|[^)\s]+)\)")
RESULT_KEY_RE = re.compile(r"^\| `([^`]+)`", flags=re.MULTILINE)
DEFAULT_RESULT_INDEX_MAX_BYTES = 16 * 1024
INDEX_HEADINGS = (
    "## Current state",
    "## Evidence levels",
    "## Topic map",
    "## Retained result catalogue",
    "## Stop and do-not-repeat decisions",
    "## Maintenance contract",
)


def fail(message: str) -> None:
    raise ValueError(message)


def inside(root: Path, raw: str) -> Path:
    path = (root / raw).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"configured context path escapes project root: {raw}") from exc
    return path


def string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        fail(f"{name} must be a nonempty-path string array")
    return value


def positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        fail(f"{name} must be a positive integer")
    return value


def ordered_headings(text: str, headings: list[str] | tuple[str, ...], label: str) -> None:
    positions: list[int] = []
    for heading in headings:
        position = text.find(heading)
        if position < 0:
            fail(f"{label} is missing required heading {heading!r}")
        positions.append(position)
    if positions != sorted(positions):
        fail(f"{label} does not preserve the required heading order")


def check_local_links(root: Path, documents: list[Path]) -> int:
    external_count = 0
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "data:")):
                continue
            resolved = (document.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(root)
            except ValueError:
                if not resolved.exists():
                    fail(
                        f"broken external context link in {document.relative_to(root)}: {raw}"
                    )
                external_count += 1
                continue
            if not resolved.exists():
                fail(f"broken local context link in {document.relative_to(root)}: {raw}")
    return external_count


def audit(project_root: Path, config_path: Path) -> str:
    with config_path.open("rb") as handle:
        manifest = tomllib.load(handle)
    context = manifest.get("context")
    manuscript = manifest.get("manuscript")
    if not isinstance(manuscript, dict):
        fail("manifest has no [manuscript] table")
    inferred = False
    if context is None:
        inferred_index = project_root / "SCIENTIFIC_PROGRESS.md"
        inferred_packets = sorted((project_root / "docs/context").glob("*.md"))
        if not inferred_index.is_file() or not inferred_packets:
            fail("manifest has no [context] table and no conventional result index plus topic packets")
        context = {
            "result_index": "SCIENTIFIC_PROGRESS.md",
            "packets": [path.relative_to(project_root).as_posix() for path in inferred_packets],
            "required_packet_headings": [
                "## Load when", "## Established results", "## Limits and non-claims",
                "## Rejected or superseded routes", "## Evidence routes", "## Active gap",
            ],
            "result_index_max_bytes": DEFAULT_RESULT_INDEX_MAX_BYTES,
            "default_context_max_bytes": 30720,
            "packet_max_bytes": 24576,
        }
        inferred = True
    elif not isinstance(context, dict):
        fail("manifest [context] must be a table")

    result_index_raw = context.get("result_index")
    if not isinstance(result_index_raw, str) or not result_index_raw:
        fail("context.result_index must be a nonempty project-relative path")
    packet_raw = string_list(context.get("packets"), "context.packets")
    required_headings = string_list(
        context.get("required_packet_headings"), "context.required_packet_headings",
    )
    default_docs_raw = string_list(manuscript.get("context_docs"), "manuscript.context_docs")
    default_limit = positive_int(
        context.get("default_context_max_bytes"), "context.default_context_max_bytes",
    )
    packet_limit = positive_int(context.get("packet_max_bytes"), "context.packet_max_bytes")
    result_index_limit = positive_int(
        context.get("result_index_max_bytes", DEFAULT_RESULT_INDEX_MAX_BYTES),
        "context.result_index_max_bytes",
    )

    result_index = inside(project_root, result_index_raw)
    packets = [inside(project_root, raw) for raw in packet_raw]
    default_docs = [inside(project_root, raw) for raw in default_docs_raw]
    for path in [result_index, *packets, *default_docs]:
        if not path.is_file():
            fail(f"required context file is missing: {path.relative_to(project_root)}")

    index_text = result_index.read_text(encoding="utf-8")
    ordered_headings(index_text, INDEX_HEADINGS, result_index_raw)
    keys = RESULT_KEY_RE.findall(index_text)
    if not keys:
        fail("result catalogue contains no backtick-delimited result key")
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        fail(f"duplicate result keys: {duplicates}")

    total_default = sum(path.stat().st_size for path in default_docs)
    if total_default > default_limit:
        fail(f"default context is {total_default} bytes, above its {default_limit}-byte limit")
    result_index_size = result_index.stat().st_size
    if result_index_size > result_index_limit:
        fail(f"{result_index_raw} exceeds its {result_index_limit}-byte limit")
    for raw, path in zip(packet_raw, packets, strict=True):
        if path.stat().st_size > packet_limit:
            fail(f"topic packet {raw} is above its {packet_limit}-byte limit")
        ordered_headings(path.read_text(encoding="utf-8"), required_headings, raw)

    documents = list(dict.fromkeys([result_index, *packets, *default_docs]))
    external_links = check_local_links(project_root, documents)
    mode = "; inferred conventional layout" if inferred else ""
    external = f"; {external_links} external local links" if external_links else ""
    largest_packet_size, largest_packet = max(
        (path.stat().st_size, raw)
        for raw, path in zip(packet_raw, packets, strict=True)
    )
    return (
        f"PASS: research context ({len(keys)} result keys; {len(packets)} packets; "
        f"result index {result_index_size}/{result_index_limit} bytes; "
        f"default context {total_default}/{default_limit} bytes; "
        f"largest packet {largest_packet} {largest_packet_size}/{packet_limit} bytes"
        f"{mode}{external})"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("manuscript-project.toml"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"ERROR: project root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        config = inside(root, args.config.as_posix())
        if not config.is_file():
            fail(f"manifest does not exist: {config.relative_to(root)}")
        print(audit(root, config))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"FAIL: research context: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
