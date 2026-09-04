#!/usr/bin/env python3
"""Audit BibTeX structure and optionally verify exact authoritative identities."""

from __future__ import annotations

import argparse
import bisect
import difflib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pybtex.database import parse_string
from pybtex.exceptions import PybtexError

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from online_sources import (  # noqa: E402
    ARXIV_API,
    CROSSREF_API,
    INSPIRE_API,
    normalize_arxiv,
    normalize_doi,
    request_bytes,
    request_json,
)
from shared.latex_scan import (  # noqa: E402
    ScanResult,
    SourceLine,
    diagnostic_text,
    scan_tex_project,
)


INCLUDE_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
CITE_COMMAND_RE = re.compile(r"\\(?:[A-Za-z]*cite[A-Za-z]*|nocite)\*?")
NON_CITABLE_ENTRY_TYPES = {"xdata", "set"}


@dataclass(frozen=True)
class BibEntry:
    entry_type: str
    key: str
    fields: dict[str, str]


@dataclass
class OnlineResult:
    key: str
    status: str
    source: str = ""
    query: str = ""
    record: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str = ""


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


def parse_braced(text: str, start: int) -> tuple[str, int]:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{" and (index == 0 or text[index - 1] != "\\"):
            depth += 1
        elif char == "}" and (index == 0 or text[index - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    raise ValueError("unterminated braced LaTeX argument")


def skip_space(text: str, cursor: int) -> int:
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def parse_bibtex(text: str) -> list[BibEntry]:
    """Parse BibTeX/BibLaTeX with Pybtex's mature parser."""
    try:
        data = parse_string(text, "bibtex")
    except (PybtexError, UnicodeError) as exc:
        raise ValueError(str(exc)) from exc
    return [
        BibEntry(entry.type.lower(), key, dict(entry.fields))
        for key, entry in data.entries.items()
    ]


def resolve_include(raw: str, current: Path, base: Path) -> Path | None:
    value = Path(raw.strip())
    if not value.suffix:
        value = value.with_suffix(".tex")
    for candidate in (current.parent / value, base / value):
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(base)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def skip_optional_argument(text: str, cursor: int) -> int:
    cursor = skip_space(text, cursor)
    if cursor >= len(text) or text[cursor] != "[":
        return cursor
    depth = 0
    for index in range(cursor, len(text)):
        char = text[index]
        escaped = index > 0 and text[index - 1] == "\\"
        if char == "[" and not escaped:
            depth += 1
        elif char == "]" and not escaped:
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unterminated optional citation argument")


def cited_group_spans(text: str) -> list[tuple[str, int]]:
    groups: list[tuple[str, int]] = []
    for match in CITE_COMMAND_RE.finditer(text):
        cursor = match.end()
        while True:
            while True:
                before_optional = skip_space(text, cursor)
                after_optional = skip_optional_argument(text, before_optional)
                if after_optional == before_optional:
                    cursor = before_optional
                    break
                cursor = after_optional
            cursor = skip_space(text, cursor)
            if cursor < len(text) and text[cursor] == "{":
                content_start = cursor + 1
                group, cursor = parse_braced(text, cursor)
                groups.append((group, content_start))
                continue
            break
    return groups


def cited_groups(text: str) -> list[str]:
    return [group for group, _offset in cited_group_spans(text)]


def scan_citations(
    root_tex: Path, project_root: Path | None = None
) -> tuple[set[str], list[str], bool, list[dict], ScanResult]:
    scan = scan_tex_project(root_tex, project_root)
    keys: set[str] = set()
    cite_all = False
    occurrences: list[dict] = []
    sources_by_path: dict[str, dict[int, SourceLine]] = {}
    for source in scan.lines:
        sources_by_path.setdefault(source.path, {}).setdefault(source.line, source)

    for path, by_line in sources_by_path.items():
        sources = [by_line[line] for line in sorted(by_line)]
        text = "\n".join(source.text for source in sources)
        line_starts: list[int] = []
        cursor = 0
        for source in sources:
            line_starts.append(cursor)
            cursor += len(source.text) + 1
        for group, group_offset in cited_group_spans(text):
            for item in re.finditer(r"[^,]+", group):
                raw = item.group(0)
                key = raw.strip()
                if not key:
                    continue
                key_offset = group_offset + item.start() + (len(raw) - len(raw.lstrip()))
                line_index = bisect.bisect_right(line_starts, key_offset) - 1
                source = sources[max(0, line_index)]
                if key == "*":
                    cite_all = True
                    continue
                keys.add(key)
                occurrences.append({"key": key, "path": path, "line": source.line})
    return (
        keys,
        [diagnostic_text(item) for item in scan.diagnostics],
        cite_all,
        occurrences,
        scan,
    )


def citation_keys(
    root_tex: Path, project_root: Path | None = None
) -> tuple[set[str], list[str], bool]:
    keys, warnings, cite_all, _occurrences, _scan = scan_citations(
        root_tex, project_root
    )
    return keys, warnings, cite_all


def normalize_text(value: str) -> str:
    value = re.sub(r"\\(?:mathcal|mathrm|text|operatorname)\s*", "", value)
    value = re.sub(r"\\[A-Za-z]+\s*", "", value)
    value = html.unescape(value.replace("{", "").replace("}", "").replace("$", ""))
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def duplicate_values(entries: list[BibEntry], field_name: str, normalizer) -> list[str]:
    values = [
        normalizer(entry.fields[field_name])
        for entry in entries
        if entry.fields.get(field_name)
    ]
    return sorted(value for value, count in Counter(values).items() if count > 1)


def local_audit(
    entries: list[BibEntry], cited: set[str], cite_all: bool
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    keys = [entry.key for entry in entries]
    normalized_keys = Counter(key.casefold() for key in keys)
    duplicate_keys = sorted(
        key for key in keys if normalized_keys[key.casefold()] > 1
    )
    if duplicate_keys:
        failures.append("duplicate BibTeX keys: " + ", ".join(duplicate_keys))
    for label, field_name, normalizer in (
        ("arXiv identifiers", "eprint", normalize_arxiv),
        ("DOIs", "doi", normalize_doi),
    ):
        duplicates = duplicate_values(entries, field_name, normalizer)
        if duplicates:
            failures.append(f"duplicate {label}: " + ", ".join(duplicates))
    local_keys = set(keys)
    missing = sorted(cited - local_keys)
    if missing:
        failures.append("citation keys missing from bibliography: " + ", ".join(missing))
    if not cite_all:
        citable_keys = {
            entry.key
            for entry in entries
            if entry.entry_type not in NON_CITABLE_ENTRY_TYPES
        }
        uncited = sorted(citable_keys - cited)
        if uncited:
            warnings.append(f"{len(uncited)} uncited entries: " + ", ".join(uncited))
    return failures, warnings

def online_query(entry: BibEntry) -> tuple[str, str] | None:
    if entry.fields.get("eprint"):
        value = normalize_arxiv(entry.fields["eprint"])
        return "arxiv", value
    if entry.fields.get("doi"):
        value = normalize_doi(entry.fields["doi"])
        return "doi", value
    return None


def remote_title(metadata: dict[str, Any]) -> str:
    titles = metadata.get("titles") or []
    return str(titles[0].get("title", "")) if titles else ""


def title_result(
    entry: BibEntry,
    *,
    source: str,
    query: str,
    title: str,
    record: str,
    threshold: float,
    warnings: list[str] | None = None,
) -> OnlineResult:
    local_title = normalize_text(entry.fields.get("title", ""))
    found_title = normalize_text(title)
    if not local_title:
        return OnlineResult(
            entry.key,
            "FAIL",
            source=source,
            query=query,
            record=record,
            error="local title is missing",
        )
    similarity = difflib.SequenceMatcher(None, local_title, found_title).ratio()
    if similarity < threshold:
        return OnlineResult(
            entry.key,
            "FAIL",
            source=source,
            query=query,
            record=record,
            error=f"title similarity {similarity:.3f} below {threshold:.3f}",
        )
    return OnlineResult(
        entry.key,
        "PASS",
        source=source,
        query=query,
        record=record,
        warnings=warnings or [],
    )


def verify_crossref(
    entry: BibEntry, doi: str, timeout: float, retries: int, threshold: float
) -> OnlineResult:
    url = CROSSREF_API + "/" + urllib.parse.quote(doi, safe="")
    payload = request_json(url, timeout, retries).get("message", {})
    remote_doi = normalize_doi(str(payload.get("DOI", "")))
    if remote_doi != doi:
        return OnlineResult(
            entry.key,
            "FAIL",
            source="Crossref",
            query=f"doi:{doi}",
            error="exact DOI absent from returned record",
        )
    titles = payload.get("title") or []
    return title_result(
        entry,
        source="Crossref",
        query=f"doi:{doi}",
        title=str(titles[0]) if titles else "",
        record=remote_doi,
        threshold=threshold,
        warnings=["INSPIRE did not provide a matching record"],
    )


def verify_arxiv(
    entry: BibEntry, arxiv_id: str, timeout: float, retries: int, threshold: float
) -> OnlineResult:
    url = ARXIV_API + "?" + urllib.parse.urlencode({"id_list": arxiv_id})
    payload = request_bytes(url, timeout, retries, "application/atom+xml")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise OSError(f"invalid arXiv XML response: {exc}") from exc
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    remote_entry = root.find("atom:entry", namespace)
    if remote_entry is None:
        return OnlineResult(
            entry.key,
            "FAIL",
            source="arXiv",
            query=f"arxiv:{arxiv_id}",
            error="no arXiv record found",
        )
    identifier = remote_entry.findtext("atom:id", default="", namespaces=namespace)
    remote_id = normalize_arxiv(identifier)
    if remote_id != arxiv_id:
        return OnlineResult(
            entry.key,
            "FAIL",
            source="arXiv",
            query=f"arxiv:{arxiv_id}",
            error="exact arXiv identifier absent from returned record",
        )
    title = remote_entry.findtext("atom:title", default="", namespaces=namespace)
    return title_result(
        entry,
        source="arXiv",
        query=f"arxiv:{arxiv_id}",
        title=title,
        record=remote_id,
        threshold=threshold,
        warnings=["INSPIRE did not provide a matching record"],
    )


def verify_online(
    entry: BibEntry, timeout: float, retries: int, threshold: float
) -> OnlineResult:
    query = online_query(entry)
    if query is None:
        return OnlineResult(entry.key, "SKIP", warnings=["no DOI or arXiv identifier"])
    kind, exact_id = query
    query_text = f"{kind}:{exact_id}"
    url = INSPIRE_API + "?" + urllib.parse.urlencode({"q": query_text, "size": 3})
    inspire_error = ""
    try:
        payload = request_json(url, timeout, retries)
    except OSError as exc:
        payload = {}
        inspire_error = str(exc)
    hits = payload.get("hits", {}).get("hits", [])
    if hits:
        hit = hits[0]
        metadata = hit.get("metadata", {})
        if kind == "arxiv":
            remote_ids = {
                normalize_arxiv(str(item.get("value", "")))
                for item in metadata.get("arxiv_eprints", [])
                if item.get("value")
            }
        else:
            remote_ids = {
                normalize_doi(str(item.get("value", "")))
                for item in metadata.get("dois", [])
                if item.get("value")
            }
        if exact_id in remote_ids:
            return title_result(
                entry,
                source="INSPIRE",
                query=query_text,
                title=remote_title(metadata),
                record=str(metadata.get("control_number") or hit.get("id") or ""),
                threshold=threshold,
            )
        inspire_error = "INSPIRE record omitted the exact identifier"
    elif not inspire_error:
        inspire_error = "no INSPIRE record found"

    try:
        result = (
            verify_arxiv(entry, exact_id, timeout, retries, threshold)
            if kind == "arxiv"
            else verify_crossref(entry, exact_id, timeout, retries, threshold)
        )
    except OSError as exc:
        return OnlineResult(
            entry.key,
            "ERROR",
            source="INSPIRE + fallback",
            query=query_text,
            error=f"INSPIRE: {inspire_error}; fallback: {exc}",
        )
    if inspire_error and result.status == "PASS":
        result.warnings.insert(0, f"INSPIRE: {inspire_error}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-tex", required=True, type=Path)
    parser.add_argument(
        "--bib",
        required=True,
        type=Path,
        action="append",
        help="BibTeX/BibLaTeX resource; may be repeated",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Boundary for TeX includes; defaults to the root TeX directory",
    )
    parser.add_argument("--online", action="store_true")
    parser.add_argument(
        "--key",
        action="append",
        default=[],
        help="Verify only this BibTeX key online; may be repeated",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--title-threshold", type=float, default=0.88)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when unsupported LaTeX syntax prevents a complete audit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1.0 <= args.timeout <= 120.0:
        print("error: --timeout must be between 1 and 120 seconds", file=sys.stderr)
        return 2
    if not 0 <= args.retries <= 5 or not 0 <= args.delay <= 10:
        print("error: retries or delay outside allowed range", file=sys.stderr)
        return 2
    if not 0.0 <= args.title_threshold <= 1.0:
        print("error: --title-threshold must be between 0 and 1", file=sys.stderr)
        return 2
    if not args.root_tex.is_file() or any(not path.is_file() for path in args.bib):
        print("error: --root-tex and every --bib must be existing files", file=sys.stderr)
        return 2
    try:
        entries: list[BibEntry] = []
        for bib_path in args.bib:
            try:
                entries.extend(parse_bibtex(bib_path.read_text(encoding="utf-8")))
            except ValueError as exc:
                raise ValueError(f"{bib_path}: {exc}") from exc
        cited, include_warnings, cite_all, citation_uses, scan = scan_citations(
            args.root_tex, args.project_root
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not entries:
        print("error: no BibTeX entries found", file=sys.stderr)
        return 2
    failures, warnings = local_audit(entries, cited, cite_all)
    warnings.extend(include_warnings)

    online_results: list[OnlineResult] = []
    if args.online:
        selected_keys = set(args.key)
        known_keys = {entry.key for entry in entries}
        unknown = sorted(selected_keys - known_keys)
        if unknown:
            print(
                "error: unknown --key values: " + ", ".join(unknown),
                file=sys.stderr,
            )
            return 2
        selected = [
            entry for entry in entries if not selected_keys or entry.key in selected_keys
        ]
        for index, entry in enumerate(selected):
            if index and args.delay:
                time.sleep(args.delay)
            online_results.append(
                verify_online(entry, args.timeout, args.retries, args.title_threshold)
            )

    payload = {
        "entries": len(entries),
        "cited_keys": len(cited),
        "citations": citation_uses,
        "complete": not bool(scan.diagnostics),
        "unsupported_syntax": [item.to_dict() for item in scan.diagnostics],
        "local_failures": failures,
        "warnings": warnings,
        "online": [asdict(result) for result in online_results],
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Entries: {len(entries)}; cited keys: {len(cited)}")
        for message in failures:
            print(f"FAIL: {message}")
        for message in warnings:
            print(f"WARNING: {message}")
        for result in online_results:
            detail = f" [{result.query}]" if result.query else ""
            record = f" record={result.record}" if result.record else ""
            source = f" via {result.source}" if result.source else ""
            print(f"{result.status}: {result.key}{source}{detail}{record}")
            for warning in result.warnings:
                print(f"  WARNING: {warning}")
            if result.error:
                print(f"  ERROR: {result.error}")
    if any(result.status == "ERROR" for result in online_results):
        return 2
    if args.strict and scan.diagnostics:
        return 1
    if failures or any(result.status == "FAIL" for result in online_results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
