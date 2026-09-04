import tomllib
import venv

from test_helpers import *  # noqa: F403,F401


class ScaffoldProjectTests(unittest.TestCase):
    SCRIPT = "skills/scaffold-manuscript-project/scripts/scaffold_project.py"
    CONTEXT_AUDIT = (
        "skills/scaffold-manuscript-project/scripts/audit_research_context.py"
    )
    SYNC_AUDIT = "skills/edit-scientific-manuscripts/scripts/audit_artifact_sync.py"
    UNIFIED_FILES = (
        "AGENTS.md",
        "RESEARCH_PLAN.md",
        "SCIENTIFIC_PROGRESS.md",
        "CITATION_PLAN.md",
        "ADAPTERS.md",
        "manuscript-project.toml",
        "paper/MANUSCRIPT_CONTEXT.md",
        "docs/README.md",
        "docs/ENVIRONMENT.md",
        "docs/derivations/README.md",
        "docs/context/README.md",
        "docs/context/project-overview.md",
        "calculations/README.md",
        "calculations/__init__.py",
        "calculations/core/__init__.py",
        "calculations/models/__init__.py",
        "calculations/workflows/__init__.py",
        "calculations/cli/__init__.py",
        "configs/README.md",
        "verification/README.md",
        "verification/verify_all.py",
        "verification/verify_context_architecture.py",
        ".gitignore",
        ".latexmkrc",
        "requirements.txt",
        "requirements-runtime.txt",
        "requirements-verification.txt",
        "requirements-plot.txt",
    )

    def make_project(self, root: Path, tex_directory: str = "paper") -> str:
        root_tex = f"{tex_directory}/main.tex"
        write(
            root / root_tex,
            r"""
            \documentclass{article}
            \begin{document}
            \input{sections/introduction}
            \bibliography{references}
            \end{document}
            """,
        )
        write(root / tex_directory / "sections/introduction.tex", "Introduction.\n")
        write(root / tex_directory / "references.bib", "@article{A, title={A}}\n")
        return root_tex

    @staticmethod
    def tree_bytes(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def apply_default(self, root: Path, root_tex: str | None = None):
        arguments: list[object] = ["--project-root", root]
        if root_tex is not None:
            arguments.extend(["--root-tex", root_tex])
        arguments.extend(["--no-bootstrap-environment", "--apply"])
        return run_script(self.SCRIPT, *arguments)

    def test_preview_is_read_only_and_default_creates_unified_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            before = self.tree_bytes(root)

            preview = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--root-tex",
                root_tex,
                "--no-bootstrap-environment",
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(self.tree_bytes(root), before)
            for relative in self.UNIFIED_FILES:
                self.assertIn(relative, preview.stdout)

            applied = self.apply_default(root, root_tex)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            for relative in self.UNIFIED_FILES:
                self.assertTrue((root / relative).is_file(), relative)

            for package in ("", "core", "models", "workflows", "cli"):
                path = root / "calculations" / package / "__init__.py"
                compile(path.read_text(encoding="utf-8"), str(path), "exec")

            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("## Two-hop context protocol", agents)
            self.assertIn("cli -> workflows -> models/core", agents)
            self.assertIn("$explore-scientific-ideas", agents)
            self.assertIn("$orient-scientific-project", agents)
            self.assertIn("$calibrate-scientific-evidence", agents)
            self.assertIn("read-only scientific dependency", agents)
            self.assertIn("project-declared resource guards", agents)
            self.assertNotIn("8 GiB", agents)
            self.assertIn("## Project orientation and research notices", agents)
            self.assertIn(
                "No project-wide research notice log is enabled",
                agents,
            )
            self.assertFalse((root / "RESEARCH_NOTICES.md").exists())
            self.assertIn("not a required sequence", agents)
            self.assertIn(
                "Match configuration and verification effort to the strength",
                agents,
            )
            self.assertNotIn(
                "only when the relevant claim-readiness gate passes",
                agents,
            )

            research_plan = (root / "RESEARCH_PLAN.md").read_text(encoding="utf-8")
            self.assertIn("## Candidate routes", research_plan)
            self.assertIn("next scientific uncertainty", research_plan)
            self.assertNotIn("admission gate", research_plan)
            self.assertNotIn("acceptance criterion", research_plan)

            progress = (root / "SCIENTIFIC_PROGRESS.md").read_text(encoding="utf-8")
            self.assertIn(
                "| Result key | Evidence | Decision tag | Packet |",
                progress,
            )
            self.assertIn(
                "| `initialization` | open/blocked | "
                "No durable project-specific result | "
                "[project-overview.md](<docs/context/project-overview.md>) |",
                progress,
            )
            self.assertNotIn("Authoritative check", progress)

            manuscript_context = (
                root / "paper/MANUSCRIPT_CONTEXT.md"
            ).read_text(encoding="utf-8")
            self.assertIn("## Claim status and evidence", manuscript_context)
            self.assertNotIn("## Claim-readiness gates", manuscript_context)

            configuration = (
                root / "configs/README.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Scratch calculations may keep local inputs", configuration)
            self.assertNotIn("Create a versioned configuration only after", configuration)
            derivations = (
                root / "docs/derivations/README.md"
            ).read_text(encoding="utf-8")
            self.assertIn("## When a derivation note helps", derivations)
            self.assertNotIn("## Admission contract", derivations)

            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            environment_python = "py" if sys.platform == "win32" else "python3"
            self.assertEqual(
                manifest["manuscript"]["context_docs"],
                ["AGENTS.md", "SCIENTIFIC_PROGRESS.md"],
            )
            self.assertEqual(
                manifest["verification"]["default"][0],
                [environment_python, "verification/verify_all.py"],
            )
            self.assertEqual(
                manifest["context"]["result_index_max_bytes"],
                16 * 1024,
            )
            self.assertEqual(manifest["verification"]["packages"], [])
            self.assertFalse((root / "docs/SCAFFOLD_ADOPTION.md").exists())
            registered = set(manifest["verification"]["inputs"])
            routing_only = {
                ".gitignore",
                ".latexmkrc",
                "ADAPTERS.md",
                "manuscript-project.toml",
            }
            missing = sorted(
                set(self.UNIFIED_FILES).difference(routing_only, registered)
            )
            self.assertEqual(missing, [])

    def test_result_index_limit_is_configurable_and_legacy_compatible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            applied = self.apply_default(root, root_tex)
            self.assertEqual(applied.returncode, 0, applied.stderr)

            manifest_path = root / "manuscript-project.toml"
            original_manifest = manifest_path.read_text(encoding="utf-8")
            context_path = root / "paper/MANUSCRIPT_CONTEXT.md"
            context_text = context_path.read_text(encoding="utf-8")
            context_path.write_text(
                context_text.replace(
                    "## Claim status and evidence",
                    "## Claim-readiness gates",
                ),
                encoding="utf-8",
            )
            verifier = root / "verification/verify_context_architecture.py"

            legacy_manifest = original_manifest.replace(
                "result_index_max_bytes = 16384\n",
                "",
            )
            manifest_path.write_text(legacy_manifest, encoding="utf-8")
            legacy_verified = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(legacy_verified.returncode, 0, legacy_verified.stderr)
            self.assertIn("result index", legacy_verified.stdout)

            legacy_audit = run_script(
                self.CONTEXT_AUDIT,
                "--project-root",
                root,
            )
            self.assertEqual(legacy_audit.returncode, 0, legacy_audit.stderr)
            self.assertIn("result index", legacy_audit.stdout)
            self.assertIn("largest packet", legacy_audit.stdout)

            legacy_adoption = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--adopt",
            )
            self.assertEqual(legacy_adoption.returncode, 0, legacy_adoption.stderr)
            self.assertNotIn(
                "set context.result_index_max_bytes",
                legacy_adoption.stdout,
            )

            legacy_sync = run_script(
                self.SYNC_AUDIT,
                "--project-root",
                root,
                "--changed",
                "paper/main.tex",
                "--changed",
                "configs/example.toml",
                "--format",
                "json",
            )
            self.assertEqual(legacy_sync.returncode, 0, legacy_sync.stderr)
            sync_report = json.loads(legacy_sync.stdout)
            statuses = {
                companion["status"]
                for rule in sync_report["rules"]
                for companion in rule["companions"]
            }
            self.assertNotIn("anchor-missing", statuses)

            result_index_size = (root / "SCIENTIFIC_PROGRESS.md").stat().st_size
            exact_manifest = original_manifest.replace(
                "result_index_max_bytes = 16384",
                f"result_index_max_bytes = {result_index_size}",
            )
            manifest_path.write_text(exact_manifest, encoding="utf-8")
            exact_verified = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(exact_verified.returncode, 0, exact_verified.stderr)
            self.assertIn(
                f"result index {result_index_size}/{result_index_size} bytes",
                exact_verified.stdout,
            )
            exact_audit = run_script(
                self.CONTEXT_AUDIT,
                "--project-root",
                root,
            )
            self.assertEqual(exact_audit.returncode, 0, exact_audit.stderr)

            too_small = result_index_size - 1
            failing_manifest = original_manifest.replace(
                "result_index_max_bytes = 16384",
                f"result_index_max_bytes = {too_small}",
            )
            manifest_path.write_text(failing_manifest, encoding="utf-8")
            failed_verifier = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed_verifier.returncode, 1)
            self.assertIn(
                f"SCIENTIFIC_PROGRESS.md exceeds its {too_small}-byte limit",
                failed_verifier.stderr,
            )
            failed_audit = run_script(
                self.CONTEXT_AUDIT,
                "--project-root",
                root,
            )
            self.assertEqual(failed_audit.returncode, 1)
            self.assertIn(
                f"SCIENTIFIC_PROGRESS.md exceeds its {too_small}-byte limit",
                failed_audit.stderr,
            )

            for invalid_value in ("0", "-1", '"invalid"', "1.5", "false"):
                with self.subTest(invalid_value=invalid_value):
                    invalid_manifest = original_manifest.replace(
                        "result_index_max_bytes = 16384",
                        f"result_index_max_bytes = {invalid_value}",
                    )
                    manifest_path.write_text(invalid_manifest, encoding="utf-8")
                    invalid_verifier = subprocess.run(
                        [sys.executable, str(verifier)],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(invalid_verifier.returncode, 1)
                    self.assertIn(
                        "context.result_index_max_bytes must be a positive integer",
                        invalid_verifier.stderr,
                    )
                    invalid_audit = run_script(
                        self.CONTEXT_AUDIT,
                        "--project-root",
                        root,
                    )
                    self.assertEqual(invalid_audit.returncode, 1)
                    self.assertIn(
                        "context.result_index_max_bytes must be a positive integer",
                        invalid_audit.stderr,
                    )

    def test_empty_generic_project_gets_sectioned_tex_and_runnable_verifiers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            note = root / "research-note.md"
            note.write_text("A chronological research discussion.\n", encoding="utf-8")
            before = self.tree_bytes(root)
            preview = run_script(self.SCRIPT, "--project-root", root)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(self.tree_bytes(root), before)
            self.assertFalse((root / "env").exists())
            self.assertIn("ENVIRONMENT PLAN: create env/", preview.stdout)

            applied = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--apply",
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(note.read_text(encoding="utf-8"), before["research-note.md"].decode())
            self.assertIn("CREATED virtual environment: env/", applied.stdout)

            environment_python = (
                root / "env/Scripts/python.exe"
                if sys.platform == "win32"
                else root / "env/bin/python"
            )
            self.assertTrue(environment_python.is_file())
            configuration = (root / "env/pyvenv.cfg").read_text(
                encoding="utf-8"
            ).lower()
            self.assertIn("include-system-site-packages = false", configuration)
            prefix = subprocess.run(
                [
                    str(environment_python),
                    "-c",
                    "import pathlib, sys; print(pathlib.Path(sys.prefix).resolve())",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(prefix.returncode, 0, prefix.stderr)
            self.assertEqual(Path(prefix.stdout.strip()), (root / "env").resolve())

            main = (root / "paper/main.tex").read_text(encoding="utf-8")
            section_names = (
                "introduction",
                "formalism",
                "methods",
                "results",
                "discussion",
                "conclusion",
            )
            for name in section_names:
                self.assertIn(rf"\input{{sections/{name}}}", main)
                self.assertTrue((root / f"paper/sections/{name}.tex").is_file())

            context = subprocess.run(
                [
                    str(environment_python),
                    str(root / "verification/verify_context_architecture.py"),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("PASS: context architecture", context.stdout)

            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            default_verifier = manifest["verification"]["default"][0]
            all_checks = subprocess.run(
                default_verifier,
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(all_checks.returncode, 0, all_checks.stderr)
            self.assertIn("PASS: all project verifications", all_checks.stdout)

            audit = run_script(
                self.CONTEXT_AUDIT,
                "--project-root",
                root,
            )
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertIn("PASS: research context", audit.stdout)
            environment_docs = (root / "docs/ENVIRONMENT.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("pip install --upgrade pip", environment_docs)

    def test_research_notices_require_explicit_opt_in_and_are_registered(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)

            applied = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--root-tex",
                root_tex,
                "--with-research-notices",
                "--no-bootstrap-environment",
                "--apply",
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)

            notices = (root / "RESEARCH_NOTICES.md").read_text(encoding="utf-8")
            self.assertIn("optional file is enabled", notices)
            self.assertIn("not scientific evidence", notices)

            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(
                "research notices are enabled at `RESEARCH_NOTICES.md`",
                agents,
            )
            docs = (root / "docs/README.md").read_text(encoding="utf-8")
            self.assertIn(
                "[RESEARCH_NOTICES.md](../RESEARCH_NOTICES.md) is enabled",
                docs,
            )
            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            self.assertIn(
                "RESEARCH_NOTICES.md",
                manifest["verification"]["inputs"],
            )

    def test_adoption_recognizes_and_preserves_existing_research_notices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            original = "# Existing notices\n\nUser-owned consequential result.\n"
            write(root / "RESEARCH_NOTICES.md", original)

            adopted = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--root-tex",
                root_tex,
                "--adopt",
                "--no-bootstrap-environment",
                "--apply",
            )
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            self.assertEqual(
                (root / "RESEARCH_NOTICES.md").read_text(encoding="utf-8"),
                original,
            )
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(
                "research notices are enabled at `RESEARCH_NOTICES.md`",
                agents,
            )
            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            self.assertIn(
                "RESEARCH_NOTICES.md",
                manifest["verification"]["inputs"],
            )

    def test_invalid_existing_env_is_preserved_and_blocks_bootstrap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "research-note.md", "Research note.\n")
            write(root / "env/user-owned.txt", "do not replace\n")

            applied = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--apply",
            )
            self.assertEqual(applied.returncode, 2)
            self.assertIn(
                "not a recognizable executable virtual environment",
                applied.stderr,
            )
            self.assertEqual(
                (root / "env/user-owned.txt").read_text(encoding="utf-8"),
                "do not replace\n",
            )
            self.assertFalse((root / "AGENTS.md").exists())

    def test_output_path_conflict_is_detected_before_environment_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "research-note.md", "Research note.\n")
            write(root / "docs", "not a directory\n")

            applied = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--apply",
            )
            self.assertEqual(applied.returncode, 2)
            self.assertIn(
                "output parent exists but is not a directory: docs",
                applied.stderr,
            )
            self.assertFalse((root / "env").exists())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_failed_environment_creation_cleans_partial_target(self):
        module = load_module("scaffold_environment_failure", self.SCRIPT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def fail_after_partial_create(target: Path) -> None:
                target.mkdir()
                (target / "partial").write_text("partial\n", encoding="utf-8")
                raise RuntimeError("simulated venv failure")

            with mock.patch.object(
                module.venv.EnvBuilder,
                "create",
                side_effect=fail_after_partial_create,
            ):
                with self.assertRaisesRegex(
                    ValueError, "could not create repository virtual environment"
                ):
                    module.create_environment(root)
            self.assertFalse((root / "env").exists())

    def test_existing_recursive_include_graph_is_registered_and_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            write(
                root / "paper/sections/introduction.tex",
                r"""
                Introduction.
                \input{nested/detail}
                \input{sections/root-relative-detail}
                """,
            )
            write(
                root / "paper/sections/nested/detail.tex",
                "Nested active content.\n",
            )
            write(
                root / "paper/sections/root-relative-detail.tex",
                "Root-TeX-directory-relative active content.\n",
            )

            applied = self.apply_default(root, root_tex)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            inputs = manifest["verification"]["inputs"]
            self.assertIn("paper/sections/introduction.tex", inputs)
            self.assertIn("paper/sections/nested/detail.tex", inputs)
            self.assertIn("paper/sections/root-relative-detail.tex", inputs)
            context = (root / "paper/MANUSCRIPT_CONTEXT.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("`paper/sections/nested/detail.tex`", context)
            self.assertIn(
                "`paper/sections/root-relative-detail.tex`",
                context,
            )

            verifier = subprocess.run(
                [sys.executable, str(root / "verification/verify_all.py")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verifier.returncode, 0, verifier.stderr)

            context_module = load_python_path(
                "generated_context_depth",
                root / "verification/verify_context_architecture.py",
            )
            write(root / "paper/depth-zero.tex", "\\input{depth-one}\n")
            write(root / "paper/depth-one.tex", "\\input{depth-two}\n")
            write(root / "paper/depth-two.tex", "Too deep.\n")
            with mock.patch.object(context_module, "MAX_INCLUDE_DEPTH", 2):
                with self.assertRaisesRegex(
                    AssertionError, "manuscript include depth exceeds 2"
                ):
                    context_module.manuscript_include_graph("paper/depth-zero.tex")

    def test_include_graph_is_unique_and_still_reports_cycles(self):
        module = load_module("scaffold_include_graph", self.SCRIPT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "main.tex", "\\input{left}\n\\input{right}\n")
            write(root / "left.tex", "\\input{shared}\n")
            write(root / "right.tex", "\\input{shared}\n")
            write(root / "shared.tex", "\\input{main}\n")

            files, warnings = module.include_graph(root / "main.tex", root)

            self.assertEqual(
                [path.name for path in files],
                ["main.tex", "left.tex", "shared.tex", "right.tex"],
            )
            self.assertEqual(len(warnings), 1)
            self.assertIn("include cycle skipped", warnings[0])

            write(root / "depth-zero.tex", "\\input{depth-one}\n")
            write(root / "depth-one.tex", "\\input{depth-two}\n")
            write(root / "depth-two.tex", "Too deep.\n")
            with mock.patch.object(module, "MAX_INCLUDE_DEPTH", 2):
                files, warnings = module.include_graph(root / "depth-zero.tex", root)
            self.assertEqual(
                [path.name for path in files],
                ["depth-zero.tex", "depth-one.tex"],
            )
            self.assertEqual(len(warnings), 1)
            self.assertIn("include depth exceeds 2", warnings[0])

    def test_symlinked_project_root_is_canonicalized(self):
        module = load_module("scaffold_symlinked_root", self.SCRIPT)
        with tempfile.TemporaryDirectory() as temporary:
            actual = Path(temporary) / "actual"
            actual.mkdir()
            alias = Path(temporary) / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            write(actual / "main.tex", "\\input{child}\n")
            write(actual / "child.tex", "\\input{main}\n")

            self.assertEqual(
                module.inside(alias, alias / "env"), actual.resolve() / "env"
            )
            files, warnings = module.include_graph(alias / "main.tex", alias)

            self.assertEqual([path.name for path in files], ["main.tex", "child.tex"])
            self.assertEqual(len(warnings), 1)
            self.assertIn("include cycle skipped", warnings[0])

    def test_legacy_layout_flags_are_deprecated_no_op_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            normal = base / "normal/project"
            legacy = base / "legacy/project"
            normal.mkdir(parents=True)
            legacy.mkdir(parents=True)
            normal_tex = self.make_project(normal)
            legacy_tex = self.make_project(legacy)

            normal_result = self.apply_default(normal, normal_tex)
            legacy_result = run_script(
                self.SCRIPT,
                "--project-root",
                legacy,
                "--root-tex",
                legacy_tex,
                "--mature-research",
                "--with-calculation-layout",
                "--no-bootstrap-environment",
                "--apply",
            )
            self.assertEqual(normal_result.returncode, 0, normal_result.stderr)
            self.assertEqual(legacy_result.returncode, 0, legacy_result.stderr)
            self.assertIn("--mature-research is deprecated", legacy_result.stderr)
            self.assertIn(
                "--with-calculation-layout is deprecated",
                legacy_result.stderr,
            )
            self.assertEqual(self.tree_bytes(normal), self.tree_bytes(legacy))

    def test_adopt_preserves_user_owned_files_and_reports_migration_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            manifest = textwrap.dedent(
                f"""
                [manuscript]
                root_tex = "{root_tex}"
                bibliography = "paper/references.bib"
                context_docs = ["AGENTS.md"]

                [verification]
                default = [["{sys.executable}", "verification/custom_check.py"]]
                online = []
                inputs = ["{root_tex}", "paper/references.bib"]
                packages = ["custom-package==1.2.3"]
                provenance_python = "{sys.executable}"
                seeds = {{ benchmark = 7 }}
                cache_policy = "fresh"

                [artifacts]
                generated = ["build/main.pdf"]
                """
            ).lstrip()
            write(root / "manuscript-project.toml", manifest)
            write(root / "AGENTS.md", "existing agent guidance\n")
            write(root / "RESEARCH_PLAN.md", "existing research plan\n")
            write(root / "SCIENTIFIC_PROGRESS.md", "existing index\n")
            write(root / "docs/context/custom-topic.md", "existing custom packet\n")
            write(
                root / "calculations/models/__init__.py",
                '"""Existing model package."""\n',
            )
            write(root / "requirements.txt", "user-owned-package==9.9\n")
            preserved_paths = (
                "paper/main.tex",
                "paper/sections/introduction.tex",
                "paper/references.bib",
                "manuscript-project.toml",
                "AGENTS.md",
                "RESEARCH_PLAN.md",
                "SCIENTIFIC_PROGRESS.md",
                "docs/context/custom-topic.md",
                "calculations/models/__init__.py",
                "requirements.txt",
            )
            before = {relative: (root / relative).read_bytes() for relative in preserved_paths}

            adopted = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--adopt",
                "--apply",
            )
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            for relative, content in before.items():
                self.assertEqual((root / relative).read_bytes(), content, relative)
            self.assertFalse((root / "docs/context/project-overview.md").exists())
            self.assertTrue((root / "docs/context/README.md").is_file())
            self.assertTrue((root / "calculations/core/__init__.py").is_file())
            self.assertIn("ADOPT existing topic packets: 1", adopted.stdout)
            self.assertIn(
                "ADOPT existing environment specifications: requirements.txt",
                adopted.stdout,
            )
            self.assertIn("MIGRATION REVIEW:", adopted.stdout)
            self.assertIn("set manuscript.context_docs", adopted.stdout)
            self.assertIn("register verification/verify_all.py", adopted.stdout)
            self.assertIn("register unified verification inputs", adopted.stdout)
            self.assertIn(
                "replace every artifacts.generated path string",
                adopted.stdout,
            )
            self.assertIn(
                "restore the ordered topic-packet heading contract",
                adopted.stdout,
            )

    def test_adopted_local_environment_drives_new_commands_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            venv.EnvBuilder(
                system_site_packages=False,
                clear=False,
                symlinks=False,
                with_pip=False,
            ).create(root / ".venv")
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted((root / ".venv").rglob("*"))
                if path.is_file()
            }

            adopted = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--root-tex",
                root_tex,
                "--adopt",
                "--apply",
            )
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted((root / ".venv").rglob("*"))
                if path.is_file()
            }
            self.assertEqual(after, before)
            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            expected = (
                ".venv/Scripts/python.exe"
                if sys.platform == "win32"
                else ".venv/bin/python"
            )
            self.assertEqual(
                manifest["verification"]["default"][0],
                [expected, "verification/verify_all.py"],
            )
            self.assertEqual(
                manifest["verification"]["provenance_python"],
                expected,
            )
            self.assertIn(
                f"generated commands use {expected}",
                adopted.stdout,
            )
            self.assertIn(
                ".venv/ was discovered by structural inspection only",
                adopted.stderr,
            )
            verified = subprocess.run(
                manifest["verification"]["default"][0],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertIn("PASS: all project verifications", verified.stdout)

    def test_adopt_and_force_are_rejected_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            result = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--adopt",
                "--force",
                "--apply",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("mutually exclusive", result.stderr)
            self.assertFalse((root / "AGENTS.md").exists())

    def test_adopt_reports_context_limits_and_complete_artifact_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            write(
                root / "docs/context/project-overview.md",
                """
                # Overview
                ## Load when
                - Orienting.
                ## Established results
                - None.
                ## Limits and non-claims
                - No claims.
                ## Rejected or superseded routes
                - None.
                ## Evidence routes
                - Pending.
                ## Active gap
                - First result.
                """,
            )
            headings = list(
                (
                    "## Load when",
                    "## Established results",
                    "## Limits and non-claims",
                    "## Rejected or superseded routes",
                    "## Evidence routes",
                    "## Active gap",
                )
            )
            write(
                root / "manuscript-project.toml",
                f"""
                [manuscript]
                root_tex = "{root_tex}"
                bibliography = "paper/references.bib"
                context_docs = ["AGENTS.md", "SCIENTIFIC_PROGRESS.md"]

                [context]
                result_index = "SCIENTIFIC_PROGRESS.md"
                packets = ["docs/context/project-overview.md"]
                required_packet_headings = {json.dumps(headings)}
                result_index_max_bytes = false
                default_context_max_bytes = 0
                packet_max_bytes = false

                [verification]
                default = [["env/bin/python", "verification/verify_all.py"]]
                online = []
                inputs = []

                [artifacts]
                generated = [
                  {{ source = "missing.py", outputs = ["../escape", "missing.py", "duplicate.dat"], extra = "invalid" }},
                  {{ source = "{root_tex}", outputs = ["duplicate.dat"] }},
                ]
                """,
            )
            adopted = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--adopt",
            )
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            for expected in (
                "set context.result_index_max_bytes to a positive integer",
                "set context.default_context_max_bytes to a positive integer",
                "set context.packet_max_bytes to a positive integer",
                "limit artifacts.generated[0] to exactly source and outputs",
                "restore generated-artifact source file: missing.py",
                "keep generated-artifact output inside the project: ../escape",
                "generated artifact must not overwrite its source: missing.py",
                "declare generated output only once: duplicate.dat",
            ):
                self.assertIn(expected, adopted.stdout)

    def test_adopted_packet_with_spaces_has_valid_dynamic_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root_tex = self.make_project(root)
            packet_name = "custom packet (one).md"
            write(
                root / "docs/context" / packet_name,
                """
                # Custom packet
                ## Load when
                - Testing paths.
                ## Established results
                - Not established.
                ## Limits and non-claims
                - Structural test only.
                ## Rejected or superseded routes
                - None.
                ## Evidence routes
                - Pending.
                ## Active gap
                - First result.
                """,
            )
            adopted = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--root-tex",
                root_tex,
                "--adopt",
                "--apply",
            )
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            packet_index = (root / "docs/context/README.md").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                f"[custom packet (one).md](<{packet_name}>)",
                packet_index,
            )
            verified = subprocess.run(
                [sys.executable, str(root / "verification/verify_all.py")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_latexmk_command_is_build_isolated_and_preserves_space_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project with spaces"
            root.mkdir()
            root_tex = self.make_project(root, "paper source")
            source = root / "paper source/main.tex"
            spaced = root / "paper source/main manuscript.tex"
            source.rename(spaced)
            root_tex = "paper source/main manuscript.tex"

            result = self.apply_default(root, root_tex)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (root / "manuscript-project.toml").open("rb") as handle:
                manifest = tomllib.load(handle)
            latex = next(
                command
                for command in manifest["verification"]["default"]
                if command[0] == "latexmk"
            )
            self.assertEqual(latex[-1], root_tex)
            self.assertIn("-outdir=../build", latex)
            self.assertIn("-cd", latex)
            self.assertNotIn("build/main.pdf", manifest["verification"]["inputs"])
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("'paper source/main manuscript.tex'", agents)

    def test_generated_artifact_schema_is_documented_and_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            applied = self.apply_default(root)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            manifest_path = root / "manuscript-project.toml"
            original = manifest_path.read_text(encoding="utf-8")
            self.assertIn(
                '# Each nonempty entry must be { source = "...", outputs = ["..."] }.',
                original,
            )
            with manifest_path.open("rb") as handle:
                manifest = tomllib.load(handle)
            self.assertEqual(manifest["artifacts"]["generated"], [])

            invalid = original.replace(
                "generated = []",
                'generated = ["build/main.pdf"]',
            )
            manifest_path.write_text(invalid, encoding="utf-8")
            verifier = root / "verification/verify_context_architecture.py"
            failed = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertIn("source and outputs", failed.stderr)

            valid = original.replace(
                "generated = []",
                (
                    'generated = [{ source = "paper/main.tex", '
                    'outputs = ["build/main.pdf"] }]'
                ),
            )
            manifest_path.write_text(valid, encoding="utf-8")
            passed = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_verify_all_uses_explicit_allowlist_and_excludes_online_scripts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            applied = self.apply_default(root)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            marker = root / "online-script-ran"
            write(
                root / "verification/verify_online_probe.py",
                (
                    "from pathlib import Path\n"
                    f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n"
                ),
            )
            orchestrator = (root / "verification/verify_all.py").read_text(
                encoding="utf-8"
            )
            self.assertIn("verify_context_architecture.py", orchestrator)
            self.assertNotIn("glob(", orchestrator)
            checked = subprocess.run(
                [sys.executable, str(root / "verification/verify_all.py")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertFalse(marker.exists())

    def test_context_audit_infers_conventional_existing_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "AGENTS.md", "# Guide\n")
            write(
                root / "SCIENTIFIC_PROGRESS.md",
                """
                # Scientific Progress Discovery Index
                ## Current state
                - Open.
                ## Evidence levels
                - `open/blocked`.
                ## Topic map
                - Overview.
                ## Retained result catalogue
                | Result key | Evidence |
                | --- | --- |
                | `initialization` | open/blocked |
                ## Stop and do-not-repeat decisions
                - None.
                ## Maintenance contract
                - Keep bounded.
                """,
            )
            write(
                root / "docs/context/overview.md",
                """
                # Overview
                ## Load when
                - Orienting.
                ## Established results
                - None.
                ## Limits and non-claims
                - No claims.
                ## Rejected or superseded routes
                - None.
                ## Evidence routes
                - Pending.
                ## Active gap
                - First result.
                """,
            )
            write(
                root / "manuscript-project.toml",
                """
                [manuscript]
                root_tex = "paper/main.tex"
                bibliography = ""
                context_docs = ["AGENTS.md", "SCIENTIFIC_PROGRESS.md"]
                """,
            )
            audit = run_script(
                self.CONTEXT_AUDIT,
                "--project-root",
                root,
            )
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertIn("inferred conventional layout", audit.stdout)

    def test_auto_discovery_scores_active_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_project(root)
            write(root / "notes/main.tex", "archived fragment\n")
            result = run_script(
                self.SCRIPT,
                "--project-root",
                root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("paper/main.tex", result.stdout)

    def test_root_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            outside = root.parent / "main.tex"
            write(outside, r"\documentclass{article}")
            result = run_script(
                self.SCRIPT,
                "--project-root",
                root,
                "--root-tex",
                "../main.tex",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("escapes project root", result.stderr)

    def test_scaffold_documents_unified_contract_and_inheritance_review(self):
        skill = (
            PLUGIN / "skills/scaffold-manuscript-project/SKILL.md"
        ).read_text(encoding="utf-8")
        layout = (
            PLUGIN
            / "skills/scaffold-manuscript-project/references/project-layout.md"
        ).read_text(encoding="utf-8")
        agents = (
            PLUGIN
            / "skills/scaffold-manuscript-project/assets/AGENTS.md.template"
        ).read_text(encoding="utf-8")
        research = (
            PLUGIN
            / "skills/scaffold-manuscript-project/assets/RESEARCH_PLAN.md.template"
        ).read_text(encoding="utf-8")
        context = (
            PLUGIN
            / "skills/scaffold-manuscript-project/assets/MANUSCRIPT_CONTEXT.md.template"
        ).read_text(encoding="utf-8")
        research_context = (
            PLUGIN
            / "skills/scaffold-manuscript-project/references/research-context.md"
        ).read_text(encoding="utf-8")

        self.assertIn("unified default", skill)
        self.assertIn("For an empty repository, omit `--root-tex`", skill)
        self.assertIn("inheritance audit", skill)
        self.assertIn("Later explicit user corrections", skill)
        self.assertIn("implementation validation", skill)
        self.assertIn("accepted compatibility aliases", skill)
        self.assertIn("optional routes selected by the scientific question", skill)
        self.assertIn("--with-research-notices", skill)
        self.assertIn("resource-guard commands and policies", skill)
        self.assertIn("read-only scientific dependency", skill)
        self.assertIn("do not infer limits from machine capacity", skill)
        self.assertIn("$orient-scientific-project", agents)
        self.assertIn("$calibrate-scientific-evidence", agents)
        self.assertIn("## Project orientation and research notices", agents)
        self.assertIn("Default project contract", layout)
        self.assertIn("calculations/", layout)
        self.assertIn("Environment and output layers", layout)
        self.assertIn("Antecedent work and evolving notes", layout)
        self.assertIn("not a required sequence", layout)
        self.assertIn("Scientific inheritance and project gap", agents)
        self.assertIn("## Two-hop context protocol", agents)
        self.assertIn("## Build and validation", agents)
        self.assertIn("## Research boundary", research)
        self.assertIn("Completed antecedent work that should not be repeated", research)
        self.assertIn("## Immediate next decision", research)
        self.assertIn("inherited scientific foundation", context)
        self.assertIn("## Reference and evidence map", context)
        self.assertIn("## Claim status and evidence", context)
        self.assertIn("## Two-hop rule", research_context)
        self.assertIn("## Stop decisions", research_context)
        self.assertIn("do not introduce nested result indexes by default", research_context)
