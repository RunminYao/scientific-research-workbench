#!/usr/bin/env python3
"""Preview or explicitly execute repository-controlled verification commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import selectors
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


REPORT_SCHEMA_VERSION = 1
DEFAULT_MAX_OUTPUT_BYTES = 1024 * 1024
MIN_MAX_OUTPUT_BYTES = 1024
MAX_MAX_OUTPUT_BYTES = 64 * 1024 * 1024
TERMINATION_GRACE_SECONDS = 2.0
PIPE_DRAIN_GRACE_SECONDS = 1.0
SAFE_ENVIRONMENT_KEYS = {
    "HOME",
    "LANG",
    "LC_ALL",
    "MPLCONFIGDIR",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "VIRTUAL_ENV",
}
SECRET_FLAGS = {
    "--api-key",
    "--apikey",
    "--password",
    "--secret",
    "--token",
}


def redact_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    hide_next = False
    for argument in command:
        if hide_next:
            redacted.append("[REDACTED]")
            hide_next = False
            continue
        lowered = argument.lower()
        if lowered in SECRET_FLAGS:
            redacted.append(argument)
            hide_next = True
            continue
        if "=" in argument:
            name, _value = argument.split("=", 1)
            if name.lower().lstrip("-").replace("_", "-") in {
                "api-key",
                "apikey",
                "password",
                "secret",
                "token",
            }:
                redacted.append(name + "=[REDACTED]")
                continue
        redacted.append(argument)
    return redacted


def validate_commands(raw: object, label: str) -> list[list[str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"verification.{label} must be an array")
    commands: list[list[str]] = []
    for index, command in enumerate(raw, start=1):
        if not isinstance(command, list) or not command or not all(
            isinstance(argument, str) and argument and "\0" not in argument
            for argument in command
        ):
            raise ValueError(
                f"verification.{label}[{index}] must be a nonempty string array"
            )
        commands.append(command)
    return commands


def validate_string_list(raw: object, label: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(
        isinstance(value, str) and value for value in raw
    ):
        raise ValueError(f"verification.{label} must be a string array")
    return raw


def load_configuration(
    config: Path, include_online: bool
) -> tuple[list[tuple[str, list[str]]], dict]:
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read {config}: {exc}") from exc
    section = data.get("verification", {})
    if not isinstance(section, dict):
        raise ValueError("verification must be a TOML table")
    if "offline" in section:
        raise ValueError(
            "verification.offline is no longer supported; rename it to "
            "verification.default (this does not provide network isolation)"
        )
    commands = [
        ("default", command)
        for command in validate_commands(section.get("default"), "default")
    ]
    if include_online:
        commands.extend(
            ("online", command)
            for command in validate_commands(section.get("online"), "online")
        )
    cache_policy = section.get("cache_policy", "unspecified")
    if not isinstance(cache_policy, str):
        raise ValueError("verification.cache_policy must be a string")
    provenance_python = section.get("provenance_python")
    if provenance_python is not None and (
        not isinstance(provenance_python, str) or not provenance_python
    ):
        raise ValueError("verification.provenance_python must be a nonempty string")
    metadata = {
        "inputs": validate_string_list(section.get("inputs"), "inputs"),
        "packages": validate_string_list(section.get("packages"), "packages"),
        "seeds": section.get("seeds", {}),
        "cache_policy": cache_policy,
        "provenance_python": provenance_python,
    }
    try:
        json.dumps(metadata["seeds"])
    except (TypeError, ValueError) as exc:
        raise ValueError("verification.seeds must be JSON-compatible") from exc
    return commands, metadata


def safe_project_path(root: Path, raw: Path) -> Path:
    path = (root / raw).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {raw}") from exc
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_provenance(root: Path) -> dict:
    def run(arguments: list[str]) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    commit = run(["rev-parse", "HEAD"])
    status = run(["status", "--porcelain=v1", "--untracked-files=all"])
    return {
        "commit": commit or None,
        "dirty": bool(status),
        "status": status.splitlines(),
    }


def collect_provenance(
    root: Path,
    config: Path,
    metadata: dict,
    online: bool,
    environment_mode: str,
    environment: dict[str, str],
) -> dict:
    inputs = []
    for raw in metadata["inputs"]:
        path = safe_project_path(root, Path(raw))
        inputs.append(
            {
                "path": raw,
                "exists": path.is_file(),
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    packages = {}
    verification_python = metadata["provenance_python"]
    if metadata["packages"]:
        verification_python = verification_python or sys.executable
        code = "\n".join(
            [
                "import importlib.metadata, json, sys",
                "out = {}",
                "for name in sys.argv[1:]:",
                "    try:",
                "        out[name] = importlib.metadata.version(name)",
                "    except importlib.metadata.PackageNotFoundError:",
                "        out[name] = None",
                "print(json.dumps(out))",
            ]
        )
        try:
            completed = subprocess.run(
                [verification_python, "-c", code, *metadata["packages"]],
                cwd=root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f"cannot query package versions: {exc}") from exc
        if completed.returncode:
            raise ValueError(
                "cannot query package versions with "
                f"{verification_python}: {completed.stderr.strip()}"
            )
        try:
            packages = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("package-version query returned invalid JSON") from exc
    return {
        "generated_at_unix": time.time(),
        "project_root": str(root),
        "config": {
            "path": str(config.relative_to(root)),
            "sha256": sha256_file(config),
        },
        "git": git_provenance(root),
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "environment": environment_mode,
            "verification_python": verification_python,
        },
        "selection": {
            "online": online,
            "cache_policy": metadata["cache_policy"],
            "seeds": metadata["seeds"],
        },
        "packages": packages,
        "inputs": inputs,
    }


@dataclass
class BoundedCapture:
    limit: int
    total_bytes: int = 0
    head: bytearray = field(default_factory=bytearray)
    tail: bytearray = field(default_factory=bytearray)

    def add(self, chunk: bytes) -> None:
        self.total_bytes += len(chunk)
        head_limit = self.limit // 2
        tail_limit = self.limit - head_limit
        if len(self.head) < head_limit:
            take = min(head_limit - len(self.head), len(chunk))
            self.head.extend(chunk[:take])
            chunk = chunk[take:]
        if chunk:
            self.tail.extend(chunk)
            if len(self.tail) > tail_limit:
                del self.tail[: len(self.tail) - tail_limit]

    @property
    def truncated(self) -> bool:
        return self.total_bytes > self.limit

    def text(self) -> str:
        if not self.truncated:
            payload = bytes(self.head + self.tail)
        else:
            omitted = self.total_bytes - len(self.head) - len(self.tail)
            marker = f"\n... [truncated {omitted} bytes] ...\n".encode()
            payload = bytes(self.head) + marker + bytes(self.tail)
        return payload.decode("utf-8", errors="replace")

    def report(self) -> dict:
        return {
            "text": self.text(),
            "total_bytes": self.total_bytes,
            "truncated": self.truncated,
            "limit_bytes": self.limit,
        }


def process_group_exists(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # macOS can deny a signal-zero probe for an extant process group.
        return True
    return True


def terminate_process_group(process: subprocess.Popen[bytes]) -> dict:
    detail = {
        "method": "process-group" if os.name == "posix" else "process",
        "sigterm_sent": False,
        "sigkill_sent": False,
        "grace_seconds": TERMINATION_GRACE_SECONDS,
        "group_gone_after_termination": False,
    }
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        detail["sigterm_sent"] = True
    except ProcessLookupError:
        return detail
    deadline = time.monotonic() + TERMINATION_GRACE_SECONDS
    if os.name == "posix":
        while time.monotonic() < deadline:
            if not process_group_exists(process.pid):
                detail["group_gone_after_termination"] = True
                break
            time.sleep(0.05)
    else:
        try:
            process.wait(timeout=TERMINATION_GRACE_SECONDS)
            detail["group_gone_after_termination"] = True
            return detail
        except subprocess.TimeoutExpired:
            pass
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        detail["sigkill_sent"] = True
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        if not process_group_exists(process.pid):
            detail["group_gone_after_termination"] = True
    return detail


def skipped_result(kind: str, command: list[str], reason: str) -> dict:
    return {
        "kind": kind,
        "command": redact_command(command),
        "status": "skipped",
        "returncode": None,
        "duration_seconds": 0.0,
        "error": reason,
        "timed_out": False,
        "output_pipes_open_at_timeout": False,
        "termination": None,
        "stdout": {"text": "", "total_bytes": 0, "truncated": False, "limit_bytes": 0},
        "stderr": {"text": "", "total_bytes": 0, "truncated": False, "limit_bytes": 0},
    }


def execute_command(
    kind: str,
    command: list[str],
    root: Path,
    environment: dict[str, str],
    timeout: float,
    max_output_bytes: int,
) -> dict:
    display_command = redact_command(command)
    stdout_capture = BoundedCapture(max_output_bytes)
    stderr_capture = BoundedCapture(max_output_bytes)
    started = time.monotonic()
    error = ""
    termination = None
    timed_out = False
    output_pipes_open_at_timeout = False
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except OSError as exc:
        duration = time.monotonic() - started
        return {
            "kind": kind,
            "command": display_command,
            "status": "launch-error",
            "returncode": None,
            "duration_seconds": duration,
            "error": str(exc),
            "timed_out": False,
            "output_pipes_open_at_timeout": False,
            "termination": None,
            "stdout": stdout_capture.report(),
            "stderr": stderr_capture.report(),
        }

    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    streams = (process.stdout, process.stderr)
    for stream, capture in zip(streams, (stdout_capture, stderr_capture)):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, capture)

    def drain_ready(wait: float) -> None:
        for key, _events in selector.select(wait):
            try:
                chunk = os.read(key.fileobj.fileno(), 64 * 1024)
            except BlockingIOError:
                continue
            if chunk:
                key.data.add(chunk)
            else:
                selector.unregister(key.fileobj)
                key.fileobj.close()

    deadline = started + timeout
    while process.poll() is None or selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            output_pipes_open_at_timeout = bool(selector.get_map())
            process_was_running = process.poll() is None
            timed_out = True
            if process_was_running:
                error = f"timed out after {timeout:g} seconds"
            else:
                error = (
                    f"timed out after {timeout:g} seconds while waiting for "
                    "stdout/stderr to close"
                )
            termination = terminate_process_group(process)
            break
        drain_ready(min(remaining, 0.1))

    if timed_out:
        drain_deadline = time.monotonic() + PIPE_DRAIN_GRACE_SECONDS
        while selector.get_map() and time.monotonic() < drain_deadline:
            drain_ready(min(0.1, drain_deadline - time.monotonic()))

    for key in list(selector.get_map().values()):
        selector.unregister(key.fileobj)
        key.fileobj.close()
    selector.close()
    if not timed_out:
        try:
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            # The poll loop should make this unreachable, but preserve the total
            # deadline if a platform delays child reaping.
            output_pipes_open_at_timeout = False
            timed_out = True
            error = f"timed out after {timeout:g} seconds while reaping the process"
            termination = terminate_process_group(process)
    duration = time.monotonic() - started
    if timed_out:
        status = "timeout"
    elif process.returncode == 0:
        status = "passed"
    else:
        status = "failed"
    return {
        "kind": kind,
        "command": display_command,
        "status": status,
        "returncode": process.returncode,
        "duration_seconds": duration,
        "error": error,
        "timed_out": timed_out,
        "output_pipes_open_at_timeout": output_pipes_open_at_timeout,
        "termination": termination,
        "stdout": stdout_capture.report(),
        "stderr": stderr_capture.report(),
    }


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = Path(raw_temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_report(path: Path, report: dict) -> None:
    atomic_write_text(
        path,
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )


def xml_10_safe(value: str) -> str:
    """Encode characters forbidden by XML 1.0 as visible escape sequences."""
    pieces: list[str] = []
    for character in value:
        codepoint = ord(character)
        if (
            character in "\t\n\r"
            or 0x20 <= codepoint <= 0xD7FF
            or 0xE000 <= codepoint <= 0xFFFD
            or 0x10000 <= codepoint <= 0x10FFFF
        ):
            pieces.append(character)
        else:
            pieces.append(f"\\u{codepoint:04X}")
    return "".join(pieces)


def write_junit(path: Path, results: list[dict]) -> None:
    failures = sum(1 for result in results if result["status"] == "failed")
    errors = sum(
        1 for result in results if result["status"] in {"timeout", "launch-error"}
    )
    skipped = sum(1 for result in results if result["status"] == "skipped")
    suite = ET.Element(
        "testsuite",
        name="manuscript-verification",
        tests=str(len(results)),
        failures=str(failures),
        errors=str(errors),
        skipped=str(skipped),
        time=f"{sum(result['duration_seconds'] for result in results):.6f}",
    )
    for result in results:
        case = ET.SubElement(
            suite,
            "testcase",
            name=xml_10_safe(
                f"{result['kind']}: {shlex.join(result['command'])}"
            ),
            time=f"{result['duration_seconds']:.6f}",
        )
        if result["status"] == "failed":
            failure = ET.SubElement(
                case,
                "failure",
                message=xml_10_safe(f"command returned {result['returncode']}"),
            )
            failure.text = xml_10_safe(
                result.get("error") or result["stderr"]["text"]
            )
        elif result["status"] in {"timeout", "launch-error"}:
            safe_error = xml_10_safe(result["error"])
            error = ET.SubElement(case, "error", message=safe_error)
            error.text = safe_error
        elif result["status"] == "skipped":
            ET.SubElement(
                case, "skipped", message=xml_10_safe(result["error"])
            )
        stdout = ET.SubElement(case, "system-out")
        stdout.text = xml_10_safe(result["stdout"]["text"])
        stderr = ET.SubElement(case, "system-err")
        stderr.text = xml_10_safe(result["stderr"]["text"])
    payload = ET.tostring(suite, encoding="unicode", xml_declaration=True)
    atomic_write_text(path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path, default=Path("manuscript-project.toml")
    )
    parser.add_argument("--online", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Execute arbitrary repository-controlled commands. This is equivalent "
            "to running repository code and is not sandboxed."
        ),
    )
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
        help="Maximum retained bytes per stdout/stderr stream (default: 1048576)",
    )
    parser.add_argument("--report", type=Path, help="Write a JSON provenance report")
    parser.add_argument("--junit", type=Path, help="Write JUnit XML results")
    parser.add_argument(
        "--inherit-env",
        action="store_true",
        help=(
            "Pass the full current environment. Environment filtering is not a "
            "sandbox or network isolation mechanism."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"error: project root is not a directory: {root}", file=sys.stderr)
        return 2
    if not 1 <= args.timeout <= 86400:
        print("error: --timeout must be between 1 and 86400 seconds", file=sys.stderr)
        return 2
    if not MIN_MAX_OUTPUT_BYTES <= args.max_output_bytes <= MAX_MAX_OUTPUT_BYTES:
        print(
            "error: --max-output-bytes must be between 1024 and 67108864",
            file=sys.stderr,
        )
        return 2
    config = safe_project_path(root, args.config)
    try:
        commands, metadata = load_configuration(config, args.online)
        report_path = safe_project_path(root, args.report) if args.report else None
        junit_path = safe_project_path(root, args.junit) if args.junit else None
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not commands:
        print("No selected verification commands are configured.")
        return 0

    print("Configured verification commands:")
    for index, (kind, command) in enumerate(commands, start=1):
        print(f"  {index}. [{kind}] {shlex.join(redact_command(command))}")
    if not args.execute:
        if report_path or junit_path:
            print("Reports are written only with --execute.")
        print(
            "Preview only. --execute runs repository code without sandboxing or "
            "network isolation."
        )
        return 0

    if args.inherit_env:
        environment = os.environ.copy()
        environment_mode = "inherited"
    else:
        environment = {
            key: value for key, value in os.environ.items() if key in SAFE_ENVIRONMENT_KEYS
        }
        environment_mode = "filtered"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"

    try:
        provenance = collect_provenance(
            root,
            config,
            metadata,
            args.online,
            environment_mode,
            environment,
        )
    except (OSError, ValueError) as exc:
        print(f"error: cannot collect provenance: {exc}", file=sys.stderr)
        return 2

    results: list[dict] = []
    stop = False
    for kind, command in commands:
        if stop:
            results.append(skipped_result(kind, command, "not run after prior failure"))
            continue
        display_command = redact_command(command)
        print(f"\n==> [{kind}] {shlex.join(display_command)}", flush=True)
        result = execute_command(
            kind,
            command,
            root,
            environment,
            args.timeout,
            args.max_output_bytes,
        )
        results.append(result)
        if result["stdout"]["text"]:
            sys.stdout.write(result["stdout"]["text"])
            if not result["stdout"]["text"].endswith("\n"):
                sys.stdout.write("\n")
        if result["stderr"]["text"]:
            sys.stderr.write(result["stderr"]["text"])
            if not result["stderr"]["text"].endswith("\n"):
                sys.stderr.write("\n")
        if result["error"]:
            print(f"ERROR: {result['error']}", file=sys.stderr)
        if result["status"] != "passed" and not args.keep_going:
            stop = True

    passed = all(result["status"] == "passed" for result in results)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "provenance": provenance,
        "results": results,
        "passed": passed,
    }
    try:
        if report_path:
            write_json_report(report_path, report)
            print(f"WROTE {report_path.relative_to(root)}")
        if junit_path:
            write_junit(junit_path, results)
            print(f"WROTE {junit_path.relative_to(root)}")
    except OSError as exc:
        print(f"error: cannot write report: {exc}", file=sys.stderr)
        return 2

    if passed:
        return 0
    if any(result["status"] == "timeout" for result in results):
        return 124
    if any(result["status"] == "launch-error" for result in results):
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
