"""Conservative, location-preserving LaTeX scanning without TeX expansion.

This module intentionally recognizes only a documented subset. It reports syntax
that could invalidate a conclusion instead of pretending to be a TeX parser.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


INCLUDE_RE = re.compile(r"\\(input|include|subfile)\s*\{([^{}]+)\}")
INCLUDE_COMMAND_RE = re.compile(r"\\(input|include|subfile)\b")
MAX_INCLUDE_DEPTH = 256
VERBATIM_BEGIN_RE = re.compile(r"\\begin\{(?:verbatim\*?|lstlisting|minted)\}")
VERBATIM_END_RE = re.compile(r"\\end\{(?:verbatim\*?|lstlisting|minted)\}")
NEWCOMMAND_RE = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand)\s*"
    r"(?:\{(?P<braced>\\[A-Za-z@]+)\}|(?P<bare>\\[A-Za-z@]+))\s*"
    r"(?P<parameters>\[[^]]+\]\s*)?"
    r"\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}"
)
DEF_RE = re.compile(
    r"\\def\s*(\\[A-Za-z@]+)\s*([^\{]*)\{((?:[^{}]|\{[^{}]*\})*)\}"
)
CONTROL_SEQUENCE_RE = re.compile(r"\\(?P<name>[A-Za-z@]+|.)")
UNSUPPORTED_CONTROL_SEQUENCES = {
    "csname": "macro-indirection",
    "edef": "expanded-definition",
    "xdef": "expanded-definition",
    "catcode": "catcode-change",
    "if": "conditional-expansion",
    "ifcase": "conditional-expansion",
    "ifcat": "conditional-expansion",
    "ifcsname": "conditional-expansion",
    "ifdefined": "conditional-expansion",
    "ifdim": "conditional-expansion",
    "ifeof": "conditional-expansion",
    "iffalse": "conditional-expansion",
    "ifhmode": "conditional-expansion",
    "ifincsname": "conditional-expansion",
    "ifinner": "conditional-expansion",
    "ifmmode": "conditional-expansion",
    "ifnum": "conditional-expansion",
    "ifodd": "conditional-expansion",
    "iftrue": "conditional-expansion",
    "ifvoid": "conditional-expansion",
    "ifvmode": "conditional-expansion",
    "ifx": "conditional-expansion",
    "unless": "conditional-expansion",
}


@dataclass(frozen=True)
class SourceLine:
    order: int
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    construct: str
    path: str
    line: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MacroDefinition:
    name: str
    body: str
    path: str
    line: int


@dataclass(frozen=True)
class ScanResult:
    lines: list[SourceLine]
    diagnostics: list[Diagnostic]
    macros: list[MacroDefinition]


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


def resolve_include(raw: str, current_file: Path, project_root: Path) -> Path | None:
    candidate = Path(raw.strip())
    if not candidate.suffix:
        candidate = candidate.with_suffix(".tex")
    for path in (current_file.parent / candidate, project_root / candidate):
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(project_root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def scan_tex_project(root: Path, project_root: Path | None = None) -> ScanResult:
    root = root.resolve()
    boundary = (project_root or root.parent).resolve()
    try:
        root.relative_to(boundary)
    except ValueError as exc:
        raise ValueError(f"root TeX file is outside project root: {root}") from exc

    lines: list[SourceLine] = []
    diagnostics: list[Diagnostic] = []
    macros: list[MacroDefinition] = []
    visited: set[Path] = set()
    counter = 0

    def report(code: str, construct: str, path: Path, line: int, message: str) -> None:
        diagnostics.append(Diagnostic(code, construct, str(path), line, message))

    def visit(
        path: Path,
        stack: tuple[Path, ...],
        included_from: tuple[Path, int] | None = None,
    ) -> None:
        nonlocal counter
        if path in stack:
            report(
                "include-cycle",
                "include graph",
                path,
                0,
                "include cycle skipped: " + " -> ".join(map(str, (*stack, path))),
            )
            return
        if path in visited:
            source_path, source_line = included_from or (path, 0)
            report(
                "repeated-include",
                "include graph",
                source_path,
                source_line,
                f"repeated include skipped: {path}",
            )
            return
        if len(stack) >= MAX_INCLUDE_DEPTH:
            source_path, source_line = included_from or (path, 0)
            report(
                "include-depth-exceeded",
                "include graph",
                source_path,
                source_line,
                f"include depth exceeds {MAX_INCLUDE_DEPTH}: {path}",
            )
            return
        visited.add(path)
        try:
            raw_lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            raw_lines = path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            report(
                "invalid-utf8",
                "source encoding",
                path,
                0,
                "invalid UTF-8 was replaced while reading the file",
            )
        except OSError as exc:
            report("unreadable-file", "source file", path, 0, str(exc))
            return

        in_verbatim = False
        next_stack = (*stack, path)
        for line_number, raw_line in enumerate(raw_lines, start=1):
            clean = strip_comment(raw_line)
            if in_verbatim:
                if VERBATIM_END_RE.search(clean):
                    in_verbatim = False
                continue
            begin = VERBATIM_BEGIN_RE.search(clean)
            if begin:
                clean = clean[: begin.start()]
                in_verbatim = True

            counter += 1
            source = SourceLine(counter, str(path), line_number, clean)
            lines.append(source)

            literal_include_spans = [match.span() for match in INCLUDE_RE.finditer(clean)]
            for command in INCLUDE_COMMAND_RE.finditer(clean):
                if not any(start <= command.start() < end for start, end in literal_include_spans):
                    report(
                        "dynamic-include",
                        command.group(0),
                        path,
                        line_number,
                        "include target is not a simple braced literal",
                    )

            for match in INCLUDE_RE.finditer(clean):
                included = resolve_include(match.group(2), path, boundary)
                if included is None:
                    report(
                        "unresolved-include",
                        match.group(0),
                        path,
                        line_number,
                        f"unable to resolve include target {match.group(2)!r}",
                    )
                else:
                    visit(included, next_stack, (path, line_number))

            for control_sequence in CONTROL_SEQUENCE_RE.finditer(clean):
                name = control_sequence.group("name")
                code = UNSUPPORTED_CONTROL_SEQUENCES.get(name)
                if code:
                    construct = "\\" + name
                    report(
                        code,
                        construct,
                        path,
                        line_number,
                        "construct requires TeX expansion and was not interpreted",
                    )

            for match in NEWCOMMAND_RE.finditer(clean):
                name = match.group("braced") or match.group("bare")
                body = match.group("body")
                if match.group("parameters") or "#" in body:
                    report(
                        "parameterized-macro",
                        name,
                        path,
                        line_number,
                        "parameterized macro was not expanded",
                    )
                else:
                    macros.append(
                        MacroDefinition(name, body, str(path), line_number)
                    )
            for match in DEF_RE.finditer(clean):
                if match.group(2).strip() or "#" in match.group(3):
                    report(
                        "parameterized-macro",
                        match.group(1),
                        path,
                        line_number,
                        "parameterized macro was not expanded",
                    )
                else:
                    macros.append(
                        MacroDefinition(match.group(1), match.group(3), str(path), line_number)
                    )

    visit(root, ())
    return ScanResult(lines, diagnostics, macros)


def diagnostic_text(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location += f":{diagnostic.line}"
    return (
        f"UNSUPPORTED SYNTAX: {location}: {diagnostic.code}: "
        f"{diagnostic.message}"
    )
