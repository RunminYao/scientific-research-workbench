from test_helpers import *  # noqa: F403,F401

class NotationAndSyncTests(unittest.TestCase):
    NOTATION = "skills/edit-scientific-manuscripts/scripts/audit_notation.py"
    NOTATION_SPEC = (
        "skills/edit-scientific-manuscripts/scripts/generate_notation_spec.py"
    )
    SYNC = "skills/edit-scientific-manuscripts/scripts/audit_artifact_sync.py"
    LINKS = "skills/edit-scientific-manuscripts/scripts/audit_manuscript_links.py"

    def test_notation_table_generates_precise_aliases_and_variants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root / "notation.tex",
                r"""
                \begin{tabular}{lll}
                \toprule
                Symbol & Dimensions & Meaning \\
                \midrule
                $g\equiv g_{a\gamma}$ & 1 & Axion coupling \\
                $Q_{\rm eff}$ & 1 & Effective momentum \\
                \bottomrule
                \end{tabular}
                """,
            )
            result = run_script(
                self.NOTATION_SPEC,
                "--table",
                root / "notation.tex",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            by_symbol = {item["canonical"]: item for item in report["items"]}
            self.assertEqual(by_symbol["g"]["aliases"], [r"g_{a\gamma}"])
            self.assertIn(
                r"Q_{\mathrm{eff}}", by_symbol[r"Q_{\rm eff}"]["variants"]
            )

    def test_preview_paths_do_not_count_as_operative_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root / "main.tex",
                r"""
                \input{sections/introduction}
                \input{notation}
                \input{sections/results}
                """,
            )
            write(root / "sections/introduction.tex", r"Preview $\Omega$." + "\n")
            write(root / "notation.tex", r"We define $\Omega$ as frequency." + "\n")
            write(root / "sections/results.tex", r"Use $\Omega$." + "\n")
            write(
                root / "spec.json",
                json.dumps(
                    {
                        "items": [
                            {
                                "name": "frequency",
                                "canonical": r"\Omega",
                                "preview_paths": ["*/sections/introduction.tex"],
                                "definition_patterns": ["frequency"],
                            }
                        ]
                    }
                ),
            )
            result = run_script(
                self.NOTATION,
                "--root",
                root / "main.tex",
                "--spec",
                root / "spec.json",
                "--format",
                "json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["statuses"], ["ok"])
            self.assertEqual(
                item["first_occurrence"]["usage_class"], "preview"
            )
            self.assertEqual(
                item["first_operative_use"]["usage_class"], "operative"
            )

    def test_notation_include_order_comments_and_variants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root / "main.tex",
                r"""
                Use $\omega_0$ first.
                \input{definitions}
                % \omega_{0} in a comment
                """,
            )
            write(
                root / "definitions.tex",
                r"We define $\omega_0$ as the frequency; avoid $\omega_{0}$." + "\n",
            )
            write(
                root / "spec.json",
                json.dumps(
                    {
                        "items": [
                            {
                                "name": "frequency",
                                "canonical": r"\omega_0",
                                "variants": [r"\omega_{0}"],
                                "definition_patterns": ["frequency"],
                            }
                        ]
                    }
                ),
            )
            result = run_script(
                self.NOTATION,
                "--root",
                root / "main.tex",
                "--spec",
                root / "spec.json",
                "--format",
                "json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            statuses = report["items"][0]["statuses"]
            self.assertIn("used-before-definition-candidate", statuses)
            self.assertIn("noncanonical-variant-used", statuses)
            self.assertEqual(report["items"][0]["counts"]["variants"], 1)

    def test_sync_required_rule_and_json_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "AGENTS.md", "guidance\n")
            write(
                root / "manuscript-project.toml",
                """
                [[sync.rules]]
                sources = ["paper/**/*.tex"]
                companions = ["AGENTS.md"]
                reason = "Keep the map synchronized."
                required = true
                """,
            )
            result = run_script(
                self.SYNC,
                "--project-root",
                root,
                "--changed",
                "paper/sections/results.tex",
                "--format",
                "json",
                "--strict",
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["rules"][0]["companions"][0]["status"],
                "required-not-changed",
            )

    def test_sync_anchor_failure_is_actionable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "AGENTS.md", "guidance without expected heading\n")
            write(
                root / "manuscript-project.toml",
                """
                [[sync.rules]]
                sources = ["paper/**/*.tex"]
                companions = ["AGENTS.md"]
                anchors = { "AGENTS.md" = ["## Manuscript map"] }
                reason = "Keep the map synchronized."
                required = true
                """,
            )
            result = run_script(
                self.SYNC,
                "--project-root",
                root,
                "--changed",
                "paper/results.tex",
                "--strict",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("anchor-missing", result.stdout)
            self.assertIn("## Manuscript map", result.stdout)

    def test_sync_base_detects_multi_commit_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "fixture@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Fixture"],
                cwd=root,
                check=True,
            )
            write(root / "AGENTS.md", "## Manuscript map\n")
            write(root / "paper/results.tex", "initial\n")
            write(
                root / "manuscript-project.toml",
                """
                [[sync.rules]]
                sources = ["paper/**/*.tex"]
                companions = ["AGENTS.md"]
                reason = "Review results."
                required = false
                """,
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            write(root / "paper/results.tex", "changed\n")
            result = run_script(
                self.SYNC,
                "--project-root",
                root,
                "--base",
                "HEAD",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("paper/results.tex", result.stdout)
            self.assertIn("Rule 1", result.stdout)

    def test_link_audit_checks_labels_graphics_and_generated_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root / "paper/main.tex",
                r"""
                \documentclass{article}
                \begin{document}
                \label{sec:one}
                See \ref{sec:one}.
                \includegraphics{figures/result}
                \end{document}
                """,
            )
            write(root / "paper/figures/result.pdf", "fake pdf fixture\n")
            write(root / "scripts/make_figure.py", "print('fixture')\n")
            write(
                root / "manuscript-project.toml",
                """
                [artifacts]
                generated = [
                  { source = "scripts/make_figure.py", outputs = ["paper/figures/result.pdf"] },
                ]
                """,
            )
            result = run_script(
                self.LINKS,
                "--project-root",
                root,
                "--root",
                root / "paper/main.tex",
                "--config",
                "manuscript-project.toml",
                "--format",
                "json",
                "--strict",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["failures"], [])
            self.assertTrue(report["artifacts"][0]["outputs"][0]["referenced"])
