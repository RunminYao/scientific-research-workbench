from test_helpers import *  # noqa: F403,F401

class VerificationTests(unittest.TestCase):
    RUNNER = "skills/verify-manuscript-results/scripts/run_verification.py"
    SCAFFOLD = "skills/verify-manuscript-results/scripts/scaffold_verification.py"

    def test_runner_redacts_secret_arguments_in_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root / "manuscript-project.toml",
                f"""
                [verification]
                default = [
                  ["{sys.executable}", "-c", "print('ok')", "--token", "secret-value", "api_key=another-secret"],
                ]
                online = []
                """,
            )
            result = run_script(self.RUNNER, "--project-root", root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("secret-value", result.stdout)
            self.assertNotIn("another-secret", result.stdout)
            self.assertIn("[REDACTED]", result.stdout)

    def test_runner_requires_explicit_execute(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "executed"
            write(
                root / "manuscript-project.toml",
                f"""
                [verification]
                default = [
                  ["{sys.executable}", "-c", "from pathlib import Path; Path('executed').write_text('yes')"],
                ]
                online = []
                """,
            )
            preview = run_script(self.RUNNER, "--project-root", root)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse(marker.exists())
            execute = run_script(
                self.RUNNER, "--project-root", root, "--execute"
            )
            self.assertEqual(execute.returncode, 0, execute.stderr)
            self.assertEqual(marker.read_text(), "yes")

    def test_verification_scaffold_preview_and_apply(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preview = run_script(self.SCAFFOLD, "--project-root", root)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse((root / "verification").exists())
            apply = run_script(
                self.SCAFFOLD, "--project-root", root, "--apply"
            )
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertTrue((root / "verification/verify_all.py").is_file())

    def test_runner_writes_provenance_and_junit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "input.txt", "scientific input\n")
            write(
                root / "manuscript-project.toml",
                f"""
                [verification]
                default = [
                  ["{sys.executable}", "-c", "print('verified')"],
                ]
                online = []
                inputs = ["input.txt"]
                packages = ["pip"]
                provenance_python = "{sys.executable}"
                seeds = {{ scan = 7 }}
                cache_policy = "bypass"
                """,
            )
            result = run_script(
                self.RUNNER,
                "--project-root",
                root,
                "--execute",
                "--report",
                "verification/report.json",
                "--junit",
                "verification/junit.xml",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(
                (root / "verification/report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["passed"])
            self.assertEqual(
                report["provenance"]["selection"]["cache_policy"], "bypass"
            )
            self.assertEqual(
                report["provenance"]["selection"]["seeds"], {"scan": 7}
            )
            self.assertIsNotNone(report["provenance"]["packages"]["pip"])
            self.assertIsNotNone(report["provenance"]["inputs"][0]["sha256"])
            self.assertTrue((root / "verification/junit.xml").is_file())


if __name__ == "__main__":
    unittest.main()
