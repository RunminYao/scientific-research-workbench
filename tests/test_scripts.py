import contextlib
import io

from test_helpers import *  # noqa: F403,F401


class InspireBibtexScriptTests(unittest.TestCase):
    RELATIVE = (
        "skills/manage-manuscript-citations/scripts/fetch_inspire_bibtex.py"
    )

    @classmethod
    def setUpClass(cls):
        cls.module = load_module("smw_fetch_inspire_bibtex", cls.RELATIVE)

    @staticmethod
    def hit(
        record: str,
        title: str,
        *,
        arxiv: str = "",
        doi: str = "",
    ) -> dict:
        metadata = {
            "control_number": int(record),
            "titles": [{"title": title}],
            "authors": [{"full_name": "Example, Alice"}],
            "earliest_date": "2024",
            "arxiv_eprints": ([{"value": arxiv}] if arxiv else []),
            "dois": ([{"value": doi}] if doi else []),
        }
        return {"id": record, "metadata": metadata}

    @staticmethod
    def bibtex(key: str = "Example:2024abc", doi: str = "10.1/example") -> bytes:
        return textwrap.dedent(
            f"""
            @article{{{key},
              title = {{A Useful Result}},
              doi = {{{doi}}},
              eprint = {{2401.00001}}
            }}
            """
        ).strip().encode("utf-8")

    def run_main(self, arguments: list[str], *, hits: list[dict], bibtex: bytes):
        stdout = io.StringIO()
        stderr = io.StringIO()
        payload = {"hits": {"hits": hits}}
        with (
            mock.patch.object(self.module, "request_json", return_value=payload),
            mock.patch.object(self.module, "request_bytes", return_value=bibtex),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = self.module.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_exact_identifier_preview_does_not_modify_bibliography(self):
        with tempfile.TemporaryDirectory() as temporary:
            bibliography = Path(temporary) / "references.bib"
            original = "@article{Existing, title={Existing}}\n"
            bibliography.write_text(original, encoding="utf-8")
            code, stdout, stderr = self.run_main(
                ["--arxiv", "arXiv:2401.00001v2", "--bib", str(bibliography)],
                hits=[self.hit("123", "A Useful Result", arxiv="2401.00001")],
                bibtex=self.bibtex(),
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(bibliography.read_text(encoding="utf-8"), original)
            self.assertIn("@article{Example:2024abc", stdout)
            self.assertIn("Preview only", stderr)

    def test_apply_appends_after_exact_identifier_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            bibliography = Path(temporary) / "references.bib"
            bibliography.write_text("@article{Existing, title={Existing}}\n", encoding="utf-8")
            code, _stdout, stderr = self.run_main(
                [
                    "--doi",
                    "https://doi.org/10.1/example",
                    "--bib",
                    str(bibliography),
                    "--key",
                    "UsefulResult2024",
                    "--apply",
                ],
                hits=[self.hit("123", "A Useful Result", doi="10.1/example")],
                bibtex=self.bibtex(),
            )
            self.assertEqual(code, 0, stderr)
            text = bibliography.read_text(encoding="utf-8")
            self.assertIn("@article{UsefulResult2024", text)
            self.assertIn("WROTE UsefulResult2024", stderr)

    def test_title_search_requires_explicit_candidate_choice(self):
        code, _stdout, stderr = self.run_main(
            ["--title", "A Useful Result"],
            hits=[
                self.hit("123", "A Useful Result"),
                self.hit("124", "A Useful Result Revisited"),
            ],
            bibtex=self.bibtex(),
        )
        self.assertEqual(code, 1)
        self.assertIn("requires an explicit --choose", stderr)

    def test_conflicting_exact_identifiers_do_not_fall_back_to_title(self):
        code, _stdout, stderr = self.run_main(
            [
                "--arxiv",
                "2401.00001",
                "--doi",
                "10.1/different",
                "--title",
                "A Useful Result",
                "--choose",
                "1",
            ],
            hits=[
                self.hit(
                    "123",
                    "A Useful Result",
                    arxiv="2401.00001",
                    doi="10.1/example",
                )
            ],
            bibtex=self.bibtex(),
        )
        self.assertEqual(code, 1)
        self.assertIn("no exact INSPIRE record found", stderr)

    def test_arxiv_pdf_url_normalization(self):
        self.assertEqual(
            self.module.normalize_arxiv(
                "https://arxiv.org/pdf/2401.00001.pdf"
            ),
            "2401.00001",
        )

    def test_duplicate_doi_is_idempotent_and_not_appended(self):
        with tempfile.TemporaryDirectory() as temporary:
            bibliography = Path(temporary) / "references.bib"
            original = textwrap.dedent(
                """
                @article{Existing,
                  title = {Existing},
                  doi = {10.1/example}
                }
                """
            ).lstrip()
            bibliography.write_text(original, encoding="utf-8")
            code, _stdout, stderr = self.run_main(
                [
                    "--doi",
                    "10.1/example",
                    "--bib",
                    str(bibliography),
                    "--apply",
                ],
                hits=[self.hit("123", "A Useful Result", doi="10.1/example")],
                bibtex=self.bibtex(),
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(bibliography.read_text(encoding="utf-8"), original)
            self.assertIn("SKIP: DOI 10.1/example already exists", stderr)

    def test_conflicting_key_refuses_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            bibliography = Path(temporary) / "references.bib"
            original = "@article{Example:2024abc, title={Different}}\n"
            bibliography.write_text(original, encoding="utf-8")
            code, _stdout, stderr = self.run_main(
                [
                    "--arxiv",
                    "2401.00001",
                    "--bib",
                    str(bibliography),
                    "--apply",
                ],
                hits=[self.hit("123", "A Useful Result", arxiv="2401.00001")],
                bibtex=self.bibtex(doi="10.1/new"),
            )
            self.assertEqual(code, 1)
            self.assertEqual(bibliography.read_text(encoding="utf-8"), original)
            self.assertIn("BibTeX key Example:2024abc already exists", stderr)
