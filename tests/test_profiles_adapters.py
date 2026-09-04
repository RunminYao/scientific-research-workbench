from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "skills/scaffold-manuscript-project/scripts/scaffold_project.py"
ADAPTERS = ("latexmk", "jupyter", "sympy", "mathematica", "slurm")


def command(project: Path, *arguments: str, empty_path: bool = False) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if empty_path:
        environment["PATH"] = ""
    command_arguments = list(arguments)
    if not any(
        item in {"--bootstrap-environment", "--no-bootstrap-environment"}
        for item in command_arguments
    ):
        command_arguments.append("--no-bootstrap-environment")
    return subprocess.run(
        [
            sys.executable,
            str(SCAFFOLD),
            "--project-root",
            str(project),
            *command_arguments,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )


def profile_arguments() -> list[str]:
    result = ["--profile", "hep-astrophysics"]
    for adapter in ADAPTERS:
        result.extend(["--adapter", adapter])
    return result


class ProfileAdapterTests(unittest.TestCase):
    def test_axion_profile_preview_then_apply(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            arguments = ["--profile", "axion-phenomenology"]
            preview = command(project, *arguments)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(list(project.iterdir()), [])
            self.assertIn(
                "rerun with --apply --profile axion-phenomenology",
                preview.stdout,
            )

            applied = command(project, *arguments, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            profile = (
                project / "AXION_PHENOMENOLOGY_PROFILE.md"
            ).read_text(encoding="utf-8")
            for expected in (
                "Natural units and electromagnetic conversions",
                "Metric, Fourier, and polarization conventions",
                "Axion-photon coupling definitions",
                "QCD mass--decay-constant relation",
                "Local dark matter and phase space",
                "Cosmological history and abundance",
                "Statistical semantics",
                "Experimental data and apparatus",
                "Coherent and incoherent regimes",
                "Approximation failure gates",
            ):
                self.assertIn(expected, profile)
            self.assertIn("Not established", profile)
            self.assertIn(
                "No numerical constant, benchmark model, exclusion, sensitivity, "
                "or conclusion is established by this profile.",
                profile,
            )
            self.assertTrue((project / "paper/main.tex").is_file())
            self.assertTrue((project / "paper/references.bib").is_file())
            for name in (
                "introduction",
                "formalism",
                "methods",
                "results",
                "discussion",
                "conclusion",
            ):
                self.assertTrue(
                    (project / f"paper/sections/{name}.tex").is_file(),
                    name,
                )
                self.assertIn(
                    rf"\input{{sections/{name}}}",
                    (project / "paper/main.tex").read_text(encoding="utf-8"),
                )
            self.assertTrue((project / "verification/verify_all.py").is_file())
            self.assertTrue((project / "requirements.txt").is_file())
            notation = json.loads(
                (project / "notation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(notation["profile"], "axion-phenomenology")
            self.assertEqual(notation["items"], [])

    def test_profile_and_all_adapters_preview_then_apply(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            arguments = profile_arguments()
            preview = command(project, *arguments, empty_path=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(list(project.iterdir()), [])
            for adapter in ("latexmk", "mathematica", "slurm"):
                self.assertIn(f"optional dependency for {adapter} was not found", preview.stderr)
            for adapter in ("jupyter", "sympy"):
                self.assertIn(
                    f"optional Python dependency for {adapter} must be",
                    preview.stderr,
                )

            applied = command(project, *arguments, "--apply", empty_path=True)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            expected = (
                "paper/main.tex", "paper/references.bib", "notation.json",
                ".latexmkrc", "verification/verify_notebook.ipynb",
                "verification/verify_sympy.py", "verification/verify_mathematica.wl",
                "verification/slurm_worker.py", "verification/verify.sbatch",
            )
            for relative in expected:
                self.assertTrue((project / relative).is_file(), relative)
            self.assertIn("revtex4-2", (project / "paper/main.tex").read_text(encoding="utf-8"))
            json.loads((project / "notation.json").read_text(encoding="utf-8"))
            notebook = json.loads(
                (project / "verification/verify_notebook.ipynb").read_text(encoding="utf-8")
            )
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    compile("".join(cell["source"]), "verify_notebook.ipynb", "exec")
            with (project / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            commands = manifest["verification"]["default"]
            environment_python = "py" if sys.platform == "win32" else "python3"
            self.assertEqual(
                commands[0],
                [environment_python, "verification/verify_all.py"],
            )
            latexmk = next(row for row in commands if row[0] == "latexmk")
            self.assertIn("-cd", latexmk)
            self.assertIn("-outdir=../build", latexmk)
            self.assertEqual(latexmk[-1], "paper/main.tex")
            self.assertTrue(any(row[0] == "wolframscript" for row in commands))
            self.assertFalse(any(row[0] == "sbatch" for row in commands))
            self.assertEqual(
                sum(
                    row[:2]
                    == [environment_python, "verification/verify_sympy.py"]
                    for row in commands
                ),
                1,
            )
            self.assertTrue(
                any(
                    row[:3] == [environment_python, "-m", "jupyter"]
                    for row in commands
                )
            )
            self.assertNotIn(
                '\n    "verify_sympy.py",',
                (project / "verification/verify_all.py").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertEqual(
                manifest["artifacts"]["generated"],
                [],
            )
            self.assertNotIn(
                "build/main.pdf",
                manifest["verification"]["inputs"],
            )

    def test_adopt_preserves_profile_and_adapter_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            arguments = profile_arguments()
            self.assertEqual(command(project, *arguments, "--apply").returncode, 0)
            marker = "% user-owned profile manuscript\n"
            (project / "paper/main.tex").write_text(marker, encoding="utf-8")
            adopted = command(project, *arguments, "--adopt", "--apply")
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            self.assertEqual((project / "paper/main.tex").read_text(encoding="utf-8"), marker)

    def test_second_apply_without_adopt_or_force_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            self.assertEqual(command(project, "--profile", "hep-astrophysics", "--apply").returncode, 0)
            repeated = command(project, "--profile", "hep-astrophysics", "--apply")
            self.assertEqual(repeated.returncode, 1)
            self.assertIn("refusing to overwrite", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
