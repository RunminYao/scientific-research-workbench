#!/usr/bin/env python3
"""Report companion artifacts implicated by changed manuscript files."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath


def normalize_relative(raw: str) -> str:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"path must stay relative to the project root: {raw!r}")
    value = path.as_posix()
    while value.startswith("./"):
        value = value[2:]
    if not value:
        raise ValueError("empty project-relative path")
    return value


def git_output(root: Path, arguments: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git command failed")
    return [line for line in result.stdout.splitlines() if line]


def changed_from_git(root: Path, base: str | None = None) -> list[str]:
    if base:
        tracked = git_output(root, ["diff", "--name-only", base, "--"])
        untracked = git_output(root, ["ls-files", "--others", "--exclude-standard"])
        return sorted({normalize_relative(path) for path in [*tracked, *untracked]})
    try:
        tracked = git_output(root, ["diff", "--name-only", "HEAD", "--"])
    except ValueError:
        tracked = git_output(root, ["diff", "--name-only", "--"])
        tracked.extend(git_output(root, ["diff", "--cached", "--name-only", "--"]))
    untracked = git_output(root, ["ls-files", "--others", "--exclude-standard"])
    return sorted({normalize_relative(path) for path in [*tracked, *untracked]})


def matches(path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    candidates = {normalized}
    if normalized.startswith("**/"):
        candidates.add(normalized[3:])
    collapsed = normalized
    while "/**/" in collapsed:
        collapsed = collapsed.replace("/**/", "/", 1)
        candidates.add(collapsed)
    return any(fnmatch.fnmatchcase(path, candidate) for candidate in candidates)


def load_rules(config_path: Path) -> list[dict]:
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read {config_path}: {exc}") from exc
    raw_rules = data.get("sync", {}).get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("sync.rules must be an array of tables")
    rules = []
    for index, raw in enumerate(raw_rules, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"sync rule {index} must be a table")
        sources = raw.get("sources")
        companions = raw.get("companions")
        reason = raw.get("reason", "")
        required = raw.get("required", False)
        anchors = raw.get("anchors", {})
        if not isinstance(sources, list) or not sources or not all(
            isinstance(item, str) and item for item in sources
        ):
            raise ValueError(f"sync rule {index} needs nonempty string sources")
        if not isinstance(companions, list) or not companions or not all(
            isinstance(item, str) and item for item in companions
        ):
            raise ValueError(f"sync rule {index} needs nonempty string companions")
        if not isinstance(reason, str) or not isinstance(required, bool):
            raise ValueError(f"sync rule {index} has invalid reason or required")
        if not isinstance(anchors, dict) or not all(
            isinstance(path, str)
            and isinstance(values, list)
            and all(isinstance(value, str) and value for value in values)
            for path, values in anchors.items()
        ):
            raise ValueError(f"sync rule {index} has invalid anchors")
        normalized_companions = [normalize_relative(item) for item in companions]
        normalized_anchors = {
            normalize_relative(path): values for path, values in anchors.items()
        }
        unknown_anchor_paths = set(normalized_anchors) - set(normalized_companions)
        if unknown_anchor_paths:
            raise ValueError(
                f"sync rule {index} anchors reference unknown companions: "
                + ", ".join(sorted(unknown_anchor_paths))
            )
        rules.append(
            {
                "index": index,
                "sources": [normalize_relative(item) for item in sources],
                "companions": normalized_companions,
                "anchors": normalized_anchors,
                "reason": reason,
                "required": required,
            }
        )
    return rules


def audit(root: Path, changed: list[str], rules: list[dict]) -> list[dict]:
    results = []
    changed_set = set(changed)
    for rule in rules:
        triggers = sorted(
            path
            for path in changed
            if any(matches(path, pattern) for pattern in rule["sources"])
        )
        if not triggers:
            continue
        companions = []
        for companion in rule["companions"]:
            companion_path = root / companion
            exists = companion_path.is_file()
            synchronized = companion in changed_set
            expected_anchors = rule["anchors"].get(companion, [])
            missing_anchors = []
            if exists and expected_anchors:
                content = companion_path.read_text(encoding="utf-8", errors="replace")
                missing_anchors = [
                    anchor for anchor in expected_anchors if anchor not in content
                ]
            if missing_anchors:
                status = "anchor-missing"
            elif synchronized:
                status = "changed"
            elif not exists:
                status = "missing"
            elif rule["required"]:
                status = "required-not-changed"
            else:
                status = "review"
            companions.append(
                {
                    "path": companion,
                    "exists": exists,
                    "changed": synchronized,
                    "missing_anchors": missing_anchors,
                    "status": status,
                }
            )
        results.append(
            {
                "rule": rule["index"],
                "required": rule["required"],
                "reason": rule["reason"],
                "triggers": triggers,
                "companions": companions,
            }
        )
    return results


def render_text(changed: list[str], results: list[dict]) -> str:
    lines = ["Changed files:"]
    lines.extend(f"  - {path}" for path in changed)
    if not changed:
        lines.append("  (none)")
    lines.append("")
    if not results:
        lines.append("No synchronization rules were triggered.")
        return "\n".join(lines) + "\n"
    for result in results:
        mode = "required" if result["required"] else "review"
        lines.append(f"Rule {result['rule']} ({mode}): {result['reason']}")
        lines.append("  Triggered by: " + ", ".join(result["triggers"]))
        for companion in result["companions"]:
            lines.append(f"  - {companion['path']}: {companion['status']}")
            if companion["missing_anchors"]:
                lines.append(
                    "    missing anchors: " + ", ".join(companion["missing_anchors"])
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path, default=Path("manuscript-project.toml")
    )
    parser.add_argument(
        "--changed",
        action="append",
        default=[],
        help="Use an explicit changed path instead of querying Git; may be repeated",
    )
    parser.add_argument(
        "--base",
        help="Compare the working tree against this Git revision instead of HEAD",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 for triggered required companions that are not changed",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"error: project root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        config = (root / args.config).resolve()
        config.relative_to(root)
        rules = load_rules(config)
        changed = (
            sorted({normalize_relative(path) for path in args.changed})
            if args.changed
            else changed_from_git(root, args.base)
        )
        results = audit(root, changed, rules)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"changed": changed, "rules": results}, indent=2))
    else:
        sys.stdout.write(render_text(changed, results))

    required_failure = any(
        result["required"]
        and any(
            companion["status"]
            in {"anchor-missing", "missing", "required-not-changed"}
            for companion in result["companions"]
        )
        for result in results
    )
    return 1 if args.strict and required_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
