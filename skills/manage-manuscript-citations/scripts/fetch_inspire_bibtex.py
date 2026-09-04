#!/usr/bin/env python3
"""Preview or append authoritative INSPIRE BibTeX using identifier-first search."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from online_sources import (  # noqa: E402
    INSPIRE_API,
    normalize_arxiv,
    normalize_doi,
    request_bytes,
    request_json,
)


KEY_RE = re.compile(r"^[^,\s{}]+$")


@dataclass(frozen=True)
class Candidate:
    record_id: str
    title: str
    authors: tuple[str, ...]
    year: str
    arxiv_ids: frozenset[str]
    dois: frozenset[str]

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> "Candidate":
        metadata = hit.get("metadata", {})
        titles = metadata.get("titles") or []
        authors = metadata.get("authors") or []
        publication = metadata.get("publication_info") or []
        year = str(
            metadata.get("earliest_date")
            or (publication[0].get("year") if publication else "")
            or "?"
        )
        record_id = str(
            hit.get("id") or metadata.get("control_number") or ""
        )
        return cls(
            record_id=record_id,
            title=str(titles[0].get("title", "")) if titles else "",
            authors=tuple(
                str(author.get("full_name") or author.get("preferred_name"))
                for author in authors
                if author.get("full_name") or author.get("preferred_name")
            ),
            year=year,
            arxiv_ids=frozenset(
                normalize_arxiv(str(item.get("value", "")))
                for item in metadata.get("arxiv_eprints", [])
                if item.get("value")
            ),
            dois=frozenset(
                normalize_doi(str(item.get("value", "")))
                for item in metadata.get("dois", [])
                if item.get("value")
            ),
        )

    def summary(self) -> str:
        names = ", ".join(self.authors[:3]) or "unknown authors"
        if len(self.authors) > 3:
            names += " et al."
        return f"{self.record_id}: {self.title or '(no title)'} [{self.year}], {names}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arxiv", help="Exact arXiv ID or arxiv.org URL")
    parser.add_argument("--doi", help="Exact DOI or doi.org URL")
    parser.add_argument("--title", help="Bibliographic title fallback")
    parser.add_argument("--author", help="Author used only to narrow a title query")
    parser.add_argument("--choose", type=int, help="1-based title-search candidate")
    parser.add_argument("--size", type=int, default=5)
    parser.add_argument("--bib", type=Path, help="Existing bibliography to inspect")
    parser.add_argument("--apply", action="store_true", help="Append after preview checks")
    parser.add_argument("--key", help="Override the returned BibTeX key")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args(argv)
    if not any((args.arxiv, args.doi, args.title)):
        parser.error("provide --arxiv, --doi, or --title")
    if args.author and not args.title:
        parser.error("--author requires --title")
    if args.apply and args.bib is None:
        parser.error("--apply requires --bib")
    if args.key and not KEY_RE.fullmatch(args.key):
        parser.error("--key must be a nonempty BibTeX key without spaces, braces, or commas")
    return args


def query_url(query: str, size: int) -> str:
    return INSPIRE_API + "?" + urllib.parse.urlencode({"q": query, "size": size})


def search(query: str, size: int, timeout: float, retries: int) -> list[Candidate]:
    payload = request_json(query_url(query, size), timeout, retries)
    return [
        Candidate.from_hit(hit)
        for hit in payload.get("hits", {}).get("hits", [])
        if isinstance(hit, dict)
    ]


def select_candidate(
    args: argparse.Namespace,
) -> tuple[Candidate | None, str, list[Candidate], str]:
    exact_queries: list[tuple[str, str, str]] = []
    expected_arxiv = ""
    expected_doi = ""
    if args.arxiv:
        expected_arxiv = normalize_arxiv(args.arxiv)
        if not expected_arxiv:
            raise ValueError("empty arXiv identifier after normalization")
        exact_queries.append(("arXiv", f"arxiv:{expected_arxiv}", expected_arxiv))
    if args.doi:
        expected_doi = normalize_doi(args.doi)
        if not expected_doi:
            raise ValueError("empty DOI after normalization")
        exact_queries.append(("DOI", f"doi:{expected_doi}", expected_doi))

    for label, query, _exact_id in exact_queries:
        candidates = search(query, args.size, args.timeout, args.retries)
        matches = [
            candidate
            for candidate in candidates
            if (not expected_arxiv or expected_arxiv in candidate.arxiv_ids)
            and (not expected_doi or expected_doi in candidate.dois)
        ]
        if len(matches) == 1:
            return matches[0], label, matches, query
        if len(matches) > 1:
            return None, label, matches, query

    if exact_queries:
        label = exact_queries[-1][0] if exact_queries else "identifier"
        query = exact_queries[-1][1] if exact_queries else ""
        return None, label, [], query

    title = args.title.strip()
    author = args.author.strip() if args.author else ""
    query = f'title:"{title}"'
    if author:
        query += f' author:"{author}"'
    candidates = search(query, args.size, args.timeout, args.retries)
    if args.choose is None:
        return None, "title", candidates, query
    if not 1 <= args.choose <= len(candidates):
        return None, "title-choice", candidates, query
    return candidates[args.choose - 1], "title-choice", candidates, query


def fetch_bibtex(candidate: Candidate, timeout: float, retries: int) -> str:
    if not candidate.record_id:
        raise OSError("INSPIRE candidate has no record identifier")
    url = f"{INSPIRE_API}/{urllib.parse.quote(candidate.record_id, safe='')}?format=bibtex"
    text = request_bytes(
        url,
        timeout,
        retries,
        "application/x-bibtex,text/plain,*/*",
    ).decode("utf-8", errors="strict").strip()
    if not text.startswith("@"):
        raise OSError("INSPIRE did not return BibTeX for the selected record")
    entries = parse_entries(text)
    if len(entries) != 1:
        raise OSError(f"expected one INSPIRE BibTeX entry, received {len(entries)}")
    return text


def replace_key(bibtex: str, key: str | None) -> str:
    if key is None:
        return bibtex
    return re.sub(
        r"(@[A-Za-z]+\s*[({]\s*)[^,\s]+",
        lambda match: match.group(1) + key,
        bibtex,
        count=1,
    )


def parse_entries(text: str) -> list[Any]:
    try:
        from audit_bibliography import parse_bibtex
    except ModuleNotFoundError as exc:
        if exc.name == "pybtex":
            raise OSError(
                "Pybtex is required for safe BibTeX parsing; install the plugin requirements"
            ) from exc
        raise
    return parse_bibtex(text)


def duplicate_status(
    existing: list[Any], incoming: Any
) -> tuple[str, str]:
    incoming_doi = normalize_doi(incoming.fields.get("doi", ""))
    incoming_arxiv = normalize_arxiv(incoming.fields.get("eprint", ""))
    for entry in existing:
        if incoming_doi and normalize_doi(entry.fields.get("doi", "")) == incoming_doi:
            return "same", f"DOI {incoming_doi} already exists as {entry.key}"
        if (
            incoming_arxiv
            and normalize_arxiv(entry.fields.get("eprint", "")) == incoming_arxiv
        ):
            return "same", f"arXiv {incoming_arxiv} already exists as {entry.key}"
    for entry in existing:
        if entry.key.casefold() == incoming.key.casefold():
            return "conflict", f"BibTeX key {incoming.key} already exists"
    return "new", ""


def atomic_append(path: Path, bibtex: str) -> None:
    old = path.read_text(encoding="utf-8")
    separator = "" if not old else "\n" if old.endswith("\n") else "\n\n"
    content = old + separator + bibtex.rstrip() + "\n"
    mode = path.stat().st_mode
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def print_candidates(candidates: list[Candidate]) -> None:
    for index, candidate in enumerate(candidates, start=1):
        print(f"{index}. {candidate.summary()}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not 1 <= args.size <= 25:
        print("error: --size must be between 1 and 25", file=sys.stderr)
        return 2
    if not 1.0 <= args.timeout <= 120.0 or not 0 <= args.retries <= 5:
        print("error: timeout or retries outside allowed range", file=sys.stderr)
        return 2
    if args.bib is not None:
        args.bib = args.bib.resolve()
        if not args.bib.is_file():
            print(f"error: bibliography is not an existing file: {args.bib}", file=sys.stderr)
            return 2

    try:
        candidate, selection, candidates, query = select_candidate(args)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: INSPIRE search failed: {exc}", file=sys.stderr)
        return 2

    print(f"INSPIRE query ({selection}): {query}", file=sys.stderr)
    print_candidates(candidates)
    if candidate is None:
        if selection == "title":
            print("error: title search requires an explicit --choose candidate", file=sys.stderr)
        elif selection == "title-choice":
            print("error: --choose is outside the returned candidate range", file=sys.stderr)
        elif candidates:
            print("error: exact identifier matched multiple INSPIRE records", file=sys.stderr)
        else:
            print("error: no exact INSPIRE record found", file=sys.stderr)
        return 1
    if selection == "title-choice" and args.choose is None:
        print("error: title search requires --choose", file=sys.stderr)
        return 1

    try:
        bibtex = replace_key(fetch_bibtex(candidate, args.timeout, args.retries), args.key)
        incoming_entries = parse_entries(bibtex)
        incoming = incoming_entries[0]
        existing: list[Any] = []
        if args.bib is not None:
            existing = parse_entries(args.bib.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: could not prepare INSPIRE BibTeX: {exc}", file=sys.stderr)
        return 2

    status, message = duplicate_status(existing, incoming)
    if status == "conflict":
        print(f"error: {message}; choose a repository-conformant --key", file=sys.stderr)
        return 1
    if status == "same":
        print(f"SKIP: {message}; bibliography unchanged", file=sys.stderr)
        return 0

    print(bibtex.rstrip())
    if args.bib is None:
        print("Preview only; pass --bib to check a target bibliography.", file=sys.stderr)
        return 0
    if not args.apply:
        print(
            f"Preview only; rerun with --apply to append {incoming.key} to {args.bib}.",
            file=sys.stderr,
        )
        return 0
    try:
        atomic_append(args.bib, bibtex)
    except OSError as exc:
        print(f"error: could not update {args.bib}: {exc}", file=sys.stderr)
        return 2
    print(f"WROTE {incoming.key} to {args.bib}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
