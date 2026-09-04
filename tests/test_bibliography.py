from test_helpers import *  # noqa: F403,F401

class BibliographyTests(unittest.TestCase):
    RELATIVE = "skills/manage-manuscript-citations/scripts/audit_bibliography.py"
    INIT_PLAN = (
        "skills/manage-manuscript-citations/scripts/init_citation_plan.py"
    )

    @classmethod
    def setUpClass(cls):
        cls.module = load_module("smw_audit_bibliography", cls.RELATIVE)

    def test_parser_supports_parentheses_string_macros_and_concatenation(self):
        entries = self.module.parse_bibtex(
            textwrap.dedent(
                r'''
                @string{jname = "Physical" # " Review"}
                @article(Key:1,
                  title = "A " # {Useful} # " Result",
                  journal = jname,
                  month = jan,
                  year = 2024
                )
                '''
            )
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].key, "Key:1")
        self.assertEqual(entries[0].fields["title"], "A Useful Result")
        self.assertEqual(entries[0].fields["journal"], "Physical Review")
        self.assertEqual(entries[0].fields["month"], "January")

    def test_citation_plan_preview_then_apply(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preview = run_script(
                self.INIT_PLAN,
                "--project-root",
                root,
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse((root / "CITATION_PLAN.md").exists())
            self.assertIn("Preview only", preview.stdout)

            apply = run_script(
                self.INIT_PLAN,
                "--project-root",
                root,
                "--apply",
            )
            self.assertEqual(apply.returncode, 0, apply.stderr)
            plan = root / "CITATION_PLAN.md"
            self.assertTrue(plan.is_file())
            self.assertIn("## Citation ledger", plan.read_text(encoding="utf-8"))

    def test_multicite_and_project_root_include_are_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(
                root / "paper/main.tex",
                r"""
                \input{../shared}
                \cites[see][p. 2]{A}[compare]{B}{C,D}
                """,
            )
            write(root / "shared.tex", r"\citeauthor{E}" + "\n")
            keys, warnings, cite_all = self.module.citation_keys(
                root / "paper/main.tex", root
            )
            self.assertEqual(keys, {"A", "B", "C", "D", "E"})
            self.assertEqual(warnings, [])
            self.assertFalse(cite_all)

    def test_local_cli_reports_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "main.tex", r"\cite{A}" + "\n")
            write(
                root / "refs.bib",
                """
                @article{A, title={A}, doi={10.1/example}}
                @article{B, title={B}, doi={10.1/example}}
                """,
            )
            result = run_script(
                self.RELATIVE,
                "--root-tex",
                root / "main.tex",
                "--bib",
                root / "refs.bib",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate DOIs", result.stdout)

    def test_online_key_filter_and_crossref_fallback(self):
        entry = self.module.BibEntry(
            "article",
            "Key",
            {"title": "A Useful Result", "doi": "10.1/example"},
        )

        def fake_json(url, _timeout, _retries):
            if "inspirehep" in url:
                return {"hits": {"hits": []}}
            return {
                "message": {
                    "DOI": "10.1/example",
                    "title": ["A Useful Result"],
                }
            }

        with mock.patch.object(self.module, "request_json", side_effect=fake_json):
            result = self.module.verify_online(entry, 5.0, 0, 0.88)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.source, "Crossref")
        self.assertTrue(any("INSPIRE" in warning for warning in result.warnings))
