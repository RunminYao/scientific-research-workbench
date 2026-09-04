from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "skills/verify-manuscript-results/scripts/run_verification.py"


def write_config(root: Path, commands: list[list[str]], *, field: str = "default") -> None:
    (root / "manuscript-project.toml").write_text(
        f"[verification]\n{field} = {json.dumps(commands)}\nonline = []\n",
        encoding="utf-8",
    )


def run(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--project-root", str(root), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


class VerificationRunnerTests(unittest.TestCase):
    def test_dual_stream_unicode_and_head_tail_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code = (
                "import sys;"
                "sys.stdout.write('开头'+'x'*200000+'结尾');"
                "sys.stderr.write('错误'+'y'*200000+'末尾')"
            )
            write_config(root, [[sys.executable, "-c", code]])
            result = run(
                root,
                "--execute",
                "--max-output-bytes",
                "1024",
                "--report",
                "report.json",
                "--junit",
                "junit.xml",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], 1)
            command = report["results"][0]
            for stream, first, last in (
                (command["stdout"], "开头", "结尾"),
                (command["stderr"], "错误", "末尾"),
            ):
                self.assertTrue(stream["truncated"])
                self.assertGreater(stream["total_bytes"], 1024)
                self.assertIn(first, stream["text"])
                self.assertIn(last, stream["text"])
                self.assertIn("[truncated", stream["text"])
            suite = ET.parse(root / "junit.xml").getroot()
            self.assertEqual(suite.attrib["failures"], "0")
            self.assertIsNotNone(suite.find("testcase/system-out"))
            self.assertIsNotNone(suite.find("testcase/system-err"))
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_failure_stops_and_records_skipped_junit_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_config(
                root,
                [
                    [sys.executable, "-c", "raise SystemExit(7)"],
                    [sys.executable, "-c", "print('must not run')"],
                ],
            )
            result = run(root, "--execute", "--report", "report.json", "--junit", "junit.xml")
            self.assertEqual(result.returncode, 1)
            report = json.loads((root / "report.json").read_text(encoding="utf-8"))
            self.assertEqual([item["status"] for item in report["results"]], ["failed", "skipped"])
            suite = ET.parse(root / "junit.xml").getroot()
            self.assertEqual(suite.attrib["failures"], "1")
            self.assertEqual(suite.attrib["skipped"], "1")

    def test_launch_error_is_reported_and_secret_arguments_are_redacted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            secret = "verification-secret-sentinel-92f"
            write_config(root, [["definitely-not-a-real-command", "--token", secret]])
            result = run(root, "--execute", "--report", "report.json")
            self.assertEqual(result.returncode, 2)
            report_text = (root / "report.json").read_text(encoding="utf-8")
            self.assertNotIn(secret, report_text)
            self.assertEqual(json.loads(report_text)["results"][0]["status"], "launch-error")

    def test_keep_going_runs_commands_after_a_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_config(
                root,
                [
                    [sys.executable, "-c", "raise SystemExit(3)"],
                    [sys.executable, "-c", "print('continued')"],
                ],
            )
            result = run(root, "--execute", "--keep-going", "--report", "report.json")
            self.assertEqual(result.returncode, 1)
            report = json.loads((root / "report.json").read_text(encoding="utf-8"))
            self.assertEqual([item["status"] for item in report["results"]], ["failed", "passed"])
            self.assertIn("continued", report["results"][1]["stdout"]["text"])

    @unittest.skipUnless(sys.platform in {"linux", "darwin"}, "POSIX process groups required")
    def test_background_child_holding_pipes_uses_total_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = "import time; time.sleep(60)"
            parent = (
                "import subprocess,sys; "
                f"subprocess.Popen([sys.executable, '-c', {child!r}])"
            )
            write_config(root, [[sys.executable, "-c", parent]])
            result = run(root, "--execute", "--timeout", "1", "--report", "report.json")
            self.assertEqual(result.returncode, 124, result.stderr)
            command = json.loads((root / "report.json").read_text(encoding="utf-8"))["results"][0]
            self.assertEqual(command["status"], "timeout")
            self.assertTrue(command["output_pipes_open_at_timeout"])
            self.assertIn("stdout/stderr to close", command["error"])
            self.assertTrue(command["termination"]["sigterm_sent"])

    def test_junit_encodes_xml_10_forbidden_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code = "import sys; sys.stdout.buffer.write(b'before\\x00after')"
            write_config(root, [[sys.executable, "-c", code]])
            result = run(root, "--execute", "--junit", "junit.xml")
            self.assertEqual(result.returncode, 0, result.stderr)
            suite = ET.parse(root / "junit.xml").getroot()
            output = suite.findtext("testcase/system-out")
            self.assertEqual(output, r"before\u0000after")

    @unittest.skipUnless(sys.platform in {"linux", "darwin"}, "POSIX process groups required")
    def test_timeout_terminates_sigterm_ignoring_process_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"
            parent = textwrap.dedent(
                f"""
                import subprocess, sys, time
                subprocess.Popen([sys.executable, "-c", {child!r}])
                time.sleep(60)
                """
            )
            write_config(root, [[sys.executable, "-c", parent]])
            result = run(root, "--execute", "--timeout", "1", "--report", "report.json")
            self.assertEqual(result.returncode, 124, result.stderr)
            command = json.loads((root / "report.json").read_text(encoding="utf-8"))["results"][0]
            self.assertEqual(command["status"], "timeout")
            self.assertTrue(command["timed_out"])
            self.assertTrue(command["termination"]["sigterm_sent"])
            self.assertTrue(command["termination"]["sigkill_sent"])

    def test_removed_offline_field_is_an_operational_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_config(root, [[sys.executable, "-c", "pass"]], field="offline")
            result = run(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("rename it to verification.default", result.stderr)


if __name__ == "__main__":
    unittest.main()
