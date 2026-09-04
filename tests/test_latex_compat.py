from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared import latex_scan


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
BIB = ROOT / "skills/manage-manuscript-citations/scripts/audit_bibliography.py"
NOTATION = ROOT / "skills/edit-scientific-manuscripts/scripts/audit_notation.py"
LINKS = ROOT / "skills/edit-scientific-manuscripts/scripts/audit_manuscript_links.py"


def execute(script: Path, *arguments: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(str(item) for item in arguments)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


def load_bibliography_module():
    specification = importlib.util.spec_from_file_location("smw_bib_compat", BIB)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class BibliographyCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_bibliography_module()

    def test_pybtex_preserves_biblatex_types_fields_macros_and_unicode(self):
        text = (FIXTURES / "latex-compat/references.bib").read_text(encoding="utf-8")
        entries = {entry.key: entry for entry in self.module.parse_bibtex(text)}
        self.assertEqual(entries["CommonData"].entry_type, "xdata")
        self.assertEqual(entries["OnlineSource"].entry_type, "online")
        self.assertEqual(entries["OnlineSource"].fields["title"], "Workbench Project Documentation")
        self.assertEqual(entries["OnlineSource"].fields["xdata"], "CommonData")
        self.assertEqual(entries["DataSet"].entry_type, "dataset")
        self.assertEqual(entries["DataSet"].fields["journaltitle"], "Example Data Journal")
        self.assertEqual(entries["DataSet"].fields["eprinttype"], "arXiv")
        self.assertIn("α", entries["DataSet"].fields["title"])

    def test_real_paper_fixture_and_multiple_bib_resources(self):
        fixture = FIXTURES / "real-papers/hsf-cwp-analysis"
        result = execute(
            BIB,
            "--root-tex", fixture / "main.tex",
            "--project-root", fixture,
            "--bib", fixture / "cwp.bib",
            "--bib", fixture / "software.bib",
            "--format", "json",
            "--strict",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(report["entries"], 2)
        self.assertEqual(report["local_failures"], [])

    def test_cross_file_duplicate_key_doi_and_arxiv_are_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.tex").write_text("\\cite{Same}\n", encoding="utf-8")
            (root / "one.bib").write_text(
                "@article{Same,title={One},doi={10.1/x},eprint={2601.1}}\n",
                encoding="utf-8",
            )
            (root / "two.bib").write_text(
                "@online{same,title={Two},doi={https://doi.org/10.1/X},eprint={arXiv:2601.1v2}}\n",
                encoding="utf-8",
            )
            result = execute(
                BIB, "--root-tex", root / "main.tex", "--bib", root / "one.bib", "--bib", root / "two.bib"
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("duplicate BibTeX keys", result.stdout)
            self.assertIn("duplicate DOIs", result.stdout)
            self.assertIn("duplicate arXiv identifiers", result.stdout)

    def test_non_direct_xdata_entry_is_not_an_uncited_warning(self):
        fixture = FIXTURES / "latex-compat"
        result = execute(
            BIB, "--root-tex", fixture / "main.tex", "--project-root", fixture,
            "--bib", fixture / "references.bib", "--format", "json", "--strict"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        warnings = "\n".join(json.loads(result.stdout)["warnings"])
        self.assertNotIn("CommonData", warnings)

    def test_malformed_bibliography_error_names_the_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.tex").write_text("text\n", encoding="utf-8")
            bad = root / "broken.bib"
            bad.write_text("@article{broken,title={unterminated}\n", encoding="utf-8")
            result = execute(BIB, "--root-tex", root / "main.tex", "--bib", bad)
            self.assertEqual(result.returncode, 2)
            self.assertIn(str(bad), result.stderr)

    def test_multiline_citation_preserves_key_line_locations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.tex").write_text(
                "Text.\n\\cite{\nFirst,\nSecond\n}\n", encoding="utf-8"
            )
            (root / "refs.bib").write_text(
                "@article{First,title={First}}\n@online{Second,title={Second}}\n",
                encoding="utf-8",
            )
            result = execute(
                BIB, "--root-tex", root / "main.tex", "--bib", root / "refs.bib",
                "--format", "json", "--strict"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                [(item["key"], item["line"]) for item in report["citations"]],
                [("First", 3), ("Second", 4)],
            )


class ConservativeScannerTests(unittest.TestCase):
    def test_repeated_include_is_bounded_and_cycle_remains_visible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.tex").write_text(
                "\\input{left}\n\\input{right}\n", encoding="utf-8"
            )
            (root / "left.tex").write_text(
                "\\input{shared}\nLeft.\n", encoding="utf-8"
            )
            (root / "right.tex").write_text(
                "\\input{shared}\nRight.\n", encoding="utf-8"
            )
            (root / "shared.tex").write_text(
                "\\input{main}\nShared.\n", encoding="utf-8"
            )

            result = latex_scan.scan_tex_project(root / "main.tex", root)

            self.assertEqual(
                sum(Path(line.path).name == "shared.tex" for line in result.lines),
                2,
            )
            self.assertEqual(
                [item.code for item in result.diagnostics],
                ["include-cycle", "repeated-include"],
            )

    def test_include_depth_limit_is_an_incomplete_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.tex").write_text("\\input{one}\n", encoding="utf-8")
            (root / "one.tex").write_text("\\input{two}\n", encoding="utf-8")
            (root / "two.tex").write_text("Too deep.\n", encoding="utf-8")

            with mock.patch.object(latex_scan, "MAX_INCLUDE_DEPTH", 2):
                result = latex_scan.scan_tex_project(root / "main.tex", root)

            self.assertEqual(len(result.lines), 2)
            self.assertEqual(
                [item.code for item in result.diagnostics],
                ["include-depth-exceeded"],
            )

    def test_revtex_cleveref_subfiles_and_macro_semantics(self):
        fixture = FIXTURES / "latex-compat"
        notation = execute(
            NOTATION, "--root", fixture / "main.tex", "--project-root", fixture,
            "--spec", fixture / "notation.json", "--format", "json", "--strict"
        )
        self.assertEqual(notation.returncode, 0, notation.stderr)
        report = json.loads(notation.stdout)
        item = report["items"][0]
        self.assertTrue(report["complete"])
        self.assertEqual(item["first_literal_occurrence"]["occurrence_origin"], "literal")
        self.assertEqual(item["first_explicit_definition"]["definition_evidence"], "explicit-definition")
        self.assertGreater(item["counts"]["macro_generated_possibility"], 0)

        links = execute(
            LINKS, "--root", fixture / "main.tex", "--project-root", fixture,
            "--format", "json", "--strict"
        )
        self.assertEqual(links.returncode, 0, links.stderr)
        link_report = json.loads(links.stdout)
        self.assertEqual(link_report["references"], 2)
        self.assertEqual(link_report["failures"], [])

    def test_unsupported_syntax_is_visible_in_text_json_and_strict_status(self):
        fixture = FIXTURES / "latex-compat"
        result = execute(
            NOTATION, "--root", fixture / "unsupported.tex", "--project-root", fixture,
            "--symbol", "E", "--format", "json", "--strict"
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["complete"])
        codes = {item["code"] for item in report["unsupported_syntax"]}
        self.assertTrue({"parameterized-macro", "expanded-definition", "dynamic-include", "macro-indirection", "catcode-change"}.issubset(codes))

        text_result = execute(
            NOTATION, "--root", fixture / "unsupported.tex", "--project-root", fixture,
            "--symbol", "E", "--strict"
        )
        self.assertEqual(text_result.returncode, 1)
        self.assertIn("UNSUPPORTED SYNTAX:", text_result.stdout)

    def test_iff_math_command_is_not_reported_as_tex_conditional(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "main.tex"
            source.write_text("$A \\iff B$.\n", encoding="utf-8")
            result = execute(
                LINKS, "--root", source, "--project-root", root,
                "--format", "json", "--strict"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["complete"])
            self.assertEqual(report["unsupported_syntax"], [])


if __name__ == "__main__":
    unittest.main()
