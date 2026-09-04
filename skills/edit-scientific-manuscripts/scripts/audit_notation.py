#!/usr/bin/env python3
"""Audit LaTeX notation occurrences in manuscript order.

The audit is intentionally conservative: it proves file and occurrence order,
but labels definitions only as candidates based on explicit patterns or common
definition-language cues.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from shared.latex_scan import (  # noqa: E402
    MacroDefinition,
    diagnostic_text,
    scan_tex_project,
)


INCLUDE_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
VERBATIM_BEGIN_RE = re.compile(r"\\begin\{(?:verbatim\*?|lstlisting|minted)\}")
VERBATIM_END_RE = re.compile(r"\\end\{(?:verbatim\*?|lstlisting|minted)\}")
DEFINITION_CUE_RE = re.compile(
    r"\b(?:"
    r"let|where|define[sd]?|denot(?:e|es|ed)|"
    r"represent(?:s|ed)?|stand(?:s)?\s+for|refer(?:s)?\s+to|"
    r"we\s+(?:introduce|use|write|call)"
    r")\b|(?:定义|记为|表示|代表|称为)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceLine:
    order: int
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class Occurrence:
    token: str
    role: str
    path: str
    line: int
    column: int
    order: int
    definition_candidate: bool
    definition_basis: str | None
    definition_confidence: str | None
    occurrence_origin: str
    definition_evidence: str
    usage_class: str
    context: str


@dataclass
class ItemResult:
    name: str
    canonical: str
    aliases: list[str]
    variants: list[str]
    statuses: list[str]
    preview_paths: list[str]
    first_occurrence: dict | None
    first_operative_use: dict | None
    first_definition_candidate: dict | None
    definition_confidence: str | None
    first_literal_occurrence: dict | None
    first_macro_generated_possibility: dict | None
    first_explicit_definition: dict | None
    first_heuristic_candidate: dict | None
    counts: dict[str, int]
    occurrences: list[dict]


def strip_comment(line: str) -> str:
    """Remove an unescaped TeX comment from one line."""
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


def resolve_include(raw: str, current_file: Path, root_dir: Path) -> Path | None:
    candidate = Path(raw.strip())
    if not candidate.suffix:
        candidate = candidate.with_suffix(".tex")
    search = [current_file.parent / candidate, root_dir / candidate]
    for path in search:
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(root_dir)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def expand_tex(
    root: Path, project_root: Path | None = None
) -> tuple[list[SourceLine], list[str]]:
    """Scan supported includes and preserve manuscript traversal order."""
    result = scan_tex_project(root, project_root)
    return result.lines, [diagnostic_text(item) for item in result.diagnostics]


def token_regex(token: str) -> re.Pattern[str]:
    if not token:
        raise ValueError("Notation tokens must not be empty")
    expression = re.escape(token)
    if token[0].isalnum():
        expression = r"(?<![A-Za-z0-9_])" + expression
    if token[-1].isalnum() or token.startswith("\\"):
        expression += r"(?![A-Za-z0-9_])"
    return re.compile(expression)


def load_spec(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load specification {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("Specification must be an object containing an 'items' array")

    items: list[dict] = []
    for index, raw in enumerate(data["items"], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Specification item {index} must be an object")
        canonical = raw.get("canonical")
        if not isinstance(canonical, str) or not canonical:
            raise ValueError(f"Specification item {index} needs a nonempty 'canonical'")
        name = raw.get("name", canonical)
        aliases = raw.get("aliases", [])
        variants = raw.get("variants", [])
        patterns = raw.get("definition_patterns", [])
        preview_paths = raw.get("preview_paths", [])
        if not isinstance(name, str) or not name:
            raise ValueError(f"Specification item {index} has an invalid 'name'")
        if not isinstance(variants, list) or not all(
            isinstance(value, str) and value for value in variants
        ):
            raise ValueError(f"Specification item {index} has invalid 'variants'")
        if not isinstance(aliases, list) or not all(
            isinstance(value, str) and value for value in aliases
        ):
            raise ValueError(f"Specification item {index} has invalid 'aliases'")
        if not isinstance(patterns, list) or not all(
            isinstance(value, str) and value for value in patterns
        ):
            raise ValueError(
                f"Specification item {index} has invalid 'definition_patterns'"
            )
        if not isinstance(preview_paths, list) or not all(
            isinstance(value, str) and value for value in preview_paths
        ):
            raise ValueError(f"Specification item {index} has invalid 'preview_paths'")
        items.append(
            {
                "name": name,
                "canonical": canonical,
                "aliases": aliases,
                "variants": variants,
                "definition_patterns": patterns,
                "preview_paths": preview_paths,
            }
        )
    return items


def compile_definition_patterns(items: Iterable[dict]) -> dict[str, list[re.Pattern[str]]]:
    compiled: dict[str, list[re.Pattern[str]]] = {}
    for item in items:
        patterns: list[re.Pattern[str]] = []
        for raw in item["definition_patterns"]:
            try:
                patterns.append(re.compile(raw, re.IGNORECASE))
            except re.error as exc:
                raise ValueError(
                    f"Invalid definition pattern for {item['name']!r}: {raw!r}: {exc}"
                ) from exc
        compiled[item["name"]] = patterns
    return compiled


def definition_basis(
    text: str, explicit_patterns: list[re.Pattern[str]], use_heuristics: bool
) -> tuple[str | None, str | None]:
    for pattern in explicit_patterns:
        if pattern.search(text):
            return f"explicit pattern: {pattern.pattern}", "explicit-definition"
    if use_heuristics and DEFINITION_CUE_RE.search(text):
        return "definition-language heuristic", "heuristic-candidate"
    return None, None


def location(occurrence: Occurrence) -> dict:
    return {
        "path": occurrence.path,
        "line": occurrence.line,
        "column": occurrence.column,
        "token": occurrence.token,
        "role": occurrence.role,
        "usage_class": occurrence.usage_class,
        "occurrence_origin": occurrence.occurrence_origin,
        "definition_evidence": occurrence.definition_evidence,
    }


def preview_occurrence(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    basename = Path(path).name
    return any(
        fnmatch.fnmatchcase(normalized, pattern)
        or fnmatch.fnmatchcase(basename, pattern)
        for pattern in patterns
    )


def audit(
    lines: list[SourceLine],
    items: list[dict],
    use_heuristics: bool,
    definition_window: int = 0,
    macros: list[MacroDefinition] | None = None,
) -> list[ItemResult]:
    definition_patterns = compile_definition_patterns(items)
    results: list[ItemResult] = []

    seen_tokens: dict[str, str] = {}
    for item in items:
        for token in [item["canonical"], *item["aliases"], *item["variants"]]:
            previous = seen_tokens.get(token)
            if previous is not None:
                raise ValueError(
                    f"Token {token!r} is assigned to both {previous!r} and "
                    f"{item['name']!r}"
                )
            seen_tokens[token] = item["name"]

    for item in items:
        occurrences: list[Occurrence] = []
        roles = {item["canonical"]: "canonical"}
        roles.update({alias: "alias" for alias in item["aliases"]})
        roles.update({variant: "variant" for variant in item["variants"]})

        for token, role in roles.items():
            matcher = token_regex(token)
            generating_macros = [
                macro for macro in macros or [] if matcher.search(macro.body)
            ]
            for source_index, source in enumerate(lines):
                if any(
                    source.path == macro.path and source.line == macro.line
                    for macro in generating_macros
                ):
                    continue
                context_lines = [
                    nearby.text
                    for nearby in lines[
                        max(0, source_index - definition_window) :
                        min(len(lines), source_index + definition_window + 1)
                    ]
                    if nearby.path == source.path
                ]
                basis, confidence = definition_basis(
                    " ".join(context_lines),
                    definition_patterns[item["name"]],
                    use_heuristics,
                )
                for match in matcher.finditer(source.text):
                    usage_class = (
                        "preview"
                        if preview_occurrence(source.path, item["preview_paths"])
                        else "operative"
                    )
                    occurrences.append(
                        Occurrence(
                            token=token,
                            role=role,
                            path=source.path,
                            line=source.line,
                            column=match.start() + 1,
                            order=source.order,
                            definition_candidate=basis is not None,
                            definition_basis=basis,
                            definition_confidence=confidence,
                            occurrence_origin="literal",
                            definition_evidence=confidence or "none",
                            usage_class=usage_class,
                            context=" ".join(source.text.strip().split()),
                        )
                    )

            for macro in generating_macros:
                invocation = token_regex(macro.name)
                for source in lines:
                    if source.path == macro.path and source.line == macro.line:
                        continue
                    for match in invocation.finditer(source.text):
                        occurrences.append(
                            Occurrence(
                                token=token,
                                role=role,
                                path=source.path,
                                line=source.line,
                                column=match.start() + 1,
                                order=source.order,
                                definition_candidate=False,
                                definition_basis=f"possible expansion of {macro.name}",
                                definition_confidence=None,
                                occurrence_origin="macro-generated-possibility",
                                definition_evidence="none",
                                usage_class="preview"
                                if preview_occurrence(source.path, item["preview_paths"])
                                else "operative",
                                context=" ".join(source.text.strip().split()),
                            )
                        )

        occurrences.sort(key=lambda entry: (entry.order, entry.column, entry.token))
        literal = [entry for entry in occurrences if entry.occurrence_origin == "literal"]
        macro_generated = [
            entry
            for entry in occurrences
            if entry.occurrence_origin == "macro-generated-possibility"
        ]
        definitions = [entry for entry in literal if entry.definition_candidate]
        explicit_definitions = [
            entry
            for entry in literal
            if entry.definition_evidence == "explicit-definition"
        ]
        heuristic_candidates = [
            entry
            for entry in literal
            if entry.definition_evidence == "heuristic-candidate"
        ]
        operative_occurrences = [
            entry
            for entry in literal
            if entry.usage_class == "operative"
        ]
        canonical_occurrences = [
            entry for entry in literal if entry.role == "canonical"
        ]
        alias_occurrences = [entry for entry in literal if entry.role == "alias"]
        variant_occurrences = [entry for entry in literal if entry.role == "variant"]

        statuses: list[str] = []
        if not literal:
            statuses.append("missing")
        else:
            if not canonical_occurrences:
                statuses.append("canonical-missing")
            if variant_occurrences:
                statuses.append("noncanonical-variant-used")
            if not definitions:
                statuses.append("no-definition-candidate")
            elif operative_occurrences and (
                operative_occurrences[0].order < definitions[0].order
                or (
                    operative_occurrences[0].order == definitions[0].order
                    and operative_occurrences[0].column < definitions[0].column
                )
            ):
                statuses.append("used-before-definition-candidate")
        if not statuses:
            statuses.append("ok")

        counts = {
            "canonical": len(canonical_occurrences),
            "aliases": len(alias_occurrences),
            "variants": len(variant_occurrences),
            "total": len(occurrences),
            "literal": len(literal),
            "macro_generated_possibility": len(macro_generated),
        }
        results.append(
            ItemResult(
                name=item["name"],
                canonical=item["canonical"],
                aliases=item["aliases"],
                variants=item["variants"],
                statuses=statuses,
                preview_paths=item["preview_paths"],
                first_occurrence=location(literal[0]) if literal else None,
                first_operative_use=location(operative_occurrences[0])
                if operative_occurrences
                else None,
                first_definition_candidate=location(definitions[0])
                if definitions
                else None,
                definition_confidence=definitions[0].definition_confidence
                if definitions
                else None,
                first_literal_occurrence=location(literal[0]) if literal else None,
                first_macro_generated_possibility=location(macro_generated[0])
                if macro_generated
                else None,
                first_explicit_definition=location(explicit_definitions[0])
                if explicit_definitions
                else None,
                first_heuristic_candidate=location(heuristic_candidates[0])
                if heuristic_candidates
                else None,
                counts=counts,
                occurrences=[asdict(entry) for entry in occurrences],
            )
        )
    return results


def relative_path(path: str, base: Path) -> str:
    try:
        return str(Path(path).relative_to(base))
    except ValueError:
        return path


def render_markdown(
    root: Path, results: list[ItemResult], warnings: list[str]
) -> str:
    lines = [
        "# Notation audit",
        "",
        f"Root: `{root}`",
        "",
        "Occurrences and definition evidence are separate: macro-generated "
        "possibilities never count as confirmed occurrences or definitions.",
        "",
        "## Summary",
        "",
        "| Item | Canonical | Status | Literal | Macro possibility | Explicit definition | Heuristic candidate |",
        "|---|---|---|---:|---:|---|---|",
    ]
    base = root.parent
    for result in results:
        first = result.first_explicit_definition
        definition = result.first_heuristic_candidate
        first_text = (
            f"`{relative_path(first['path'], base)}:{first['line']}`"
            if first
            else "—"
        )
        definition_text = (
            f"`{relative_path(definition['path'], base)}:{definition['line']}`"
            if definition
            else "—"
        )
        lines.append(
            "| {name} | `{canonical}` | {status} | {literal_count} | "
            "{macro_count} | {first} | {definition} |".format(
                name=result.name.replace("|", r"\|"),
                canonical=result.canonical.replace("|", r"\|"),
                status=", ".join(result.statuses),
                literal_count=result.counts["literal"],
                macro_count=result.counts["macro_generated_possibility"],
                first=first_text,
                definition=definition_text,
            )
        )

    if warnings:
        lines.extend(["", "## Unsupported syntax", ""])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.extend(["", "## Occurrences", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                "| Location | Token role | Origin | Usage | Definition evidence | Context |",
                "|---|---|---|---|---|---|",
            ]
        )
        if not result.occurrences:
            lines.append("| — | — | — | — | — | No occurrence found |")
            continue
        for occurrence in result.occurrences:
            path = relative_path(occurrence["path"], base)
            definition = occurrence["definition_evidence"]
            escaped_definition = definition.replace("|", r"\|")
            context = occurrence["context"].replace("|", r"\|").replace("`", r"\`")
            lines.append(
                f"| `{path}:{occurrence['line']}:{occurrence['column']}` | "
                f"`{occurrence['token']}` ({occurrence['role']}) | "
                f"{occurrence['occurrence_origin']} | "
                f"{occurrence['usage_class']} | "
                f"{escaped_definition} | {context} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit literal LaTeX notation occurrences in input/include order. "
            "Definition detection is conservative and heuristic."
        )
    )
    parser.add_argument("--root", required=True, type=Path, help="Root TeX file")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Boundary for TeX includes; defaults to the root TeX directory",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Canonical symbol to audit; may be repeated",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        help="Trusted JSON file defining canonical tokens, variants, and definition patterns",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Report format",
    )
    parser.add_argument("--output", type=Path, help="Write report to this path")
    parser.add_argument(
        "--no-heuristics",
        action="store_true",
        help="Use only explicit definition_patterns from the JSON specification",
    )
    parser.add_argument(
        "--definition-window",
        type=int,
        default=0,
        help="Inspect this many neighboring source lines for definition language (0-3)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when any item has a finding or an include cannot be resolved",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_file():
        print(f"error: root TeX file does not exist: {root}", file=sys.stderr)
        return 2
    if not 0 <= args.definition_window <= 3:
        print("error: --definition-window must be between 0 and 3", file=sys.stderr)
        return 2

    try:
        items = load_spec(args.spec) if args.spec else []
        items.extend(
            {
                "name": token,
                "canonical": token,
                "aliases": [],
                "variants": [],
                "definition_patterns": [],
                "preview_paths": [],
            }
            for token in args.symbol
        )
        if not items:
            raise ValueError("Provide at least one --symbol or a --spec file")
        scan = scan_tex_project(root, args.project_root)
        lines = scan.lines
        warnings = [diagnostic_text(item) for item in scan.diagnostics]
        results = audit(
            lines,
            items,
            use_heuristics=not args.no_heuristics,
            definition_window=args.definition_window,
            macros=scan.macros,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        report = json.dumps(
            {
                "root": str(root),
                "complete": not bool(scan.diagnostics),
                "unsupported_syntax": [
                    item.to_dict() for item in scan.diagnostics
                ],
                "warnings": warnings,
                "items": [asdict(result) for result in results],
            },
            ensure_ascii=False,
            indent=2,
        )
        report += "\n"
    else:
        report = render_markdown(root, results, warnings)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    findings = any(result.statuses != ["ok"] for result in results)
    if args.strict and (findings or warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
