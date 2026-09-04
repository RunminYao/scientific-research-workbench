from test_helpers import *  # noqa: F403,F401

class SkillStructureTests(unittest.TestCase):
    EXPECTED_RESEARCH_SKILLS = {
        "calibrate-scientific-evidence",
        "explore-scientific-ideas",
        "orient-scientific-project",
        "research-scientific-literature",
        "derive-scientific-results",
        "implement-scientific-computations",
    }

    def test_repository_markdown_does_not_hard_wrap_prose(self):
        list_marker = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+\S")
        structural = re.compile(
            r"^\s*(?:#{1,6}\s|[-+*]\s+|\d+[.)]\s+|>|\||```|~~~|<|"
            r"\{\{[^}]+\}\}\s*$|\[[^]]+\]:|\$\$|\\\[|\\\]|={3,}\s*$|-{3,}\s*$)"
        )
        violations = []
        ignored_directories = {".git", ".pytest_cache", ".venv", "__pycache__", "env", "venv"}
        paths = sorted(
            path
            for path in PLUGIN.rglob("*")
            if path.is_file()
            and (path.name.endswith(".md") or path.name.endswith(".md.template"))
            and not ignored_directories.intersection(path.relative_to(PLUGIN).parts)
        )
        for path in paths:
            lines = path.read_text(encoding="utf-8").splitlines()
            in_frontmatter = bool(lines and lines[0] == "---")
            in_fence = False
            in_display_math = False
            previous = None
            for line_number, line in enumerate(lines, start=1):
                if in_frontmatter:
                    if line_number > 1 and line == "---":
                        in_frontmatter = False
                    previous = None
                    continue
                if re.match(r"^\s*(```|~~~)", line):
                    in_fence = not in_fence
                    previous = None
                    continue
                if in_display_math:
                    if line.strip() in {r"\]", "$$"}:
                        in_display_math = False
                    previous = None
                    continue
                if line.strip() in {r"\[", "$$"}:
                    in_display_math = True
                    previous = None
                    continue
                if in_fence or not line.strip():
                    previous = None
                    continue
                if previous is not None:
                    previous_number, previous_line = previous
                    if not previous_line.endswith(("  ", "\\")) and not structural.match(line):
                        previous_is_structural = structural.match(previous_line)
                        previous_indent = len(previous_line) - len(previous_line.lstrip())
                        current_indent = len(line) - len(line.lstrip())
                        same_indent_prose = (
                            not previous_is_structural
                            and previous_indent == current_indent
                        )
                        marker = list_marker.match(previous_line)
                        wrapped_list_item = bool(
                            marker and current_indent > len(marker.group(1))
                        )
                        if same_indent_prose or wrapped_list_item:
                            relative = path.relative_to(PLUGIN)
                            violations.append(
                                f"{relative}:{previous_number}-{line_number}"
                            )
                previous = (line_number, line)
        self.assertEqual(violations, [])

    def test_research_skills_are_present_and_complete(self):
        actual = {
            path.parent.name
            for path in (PLUGIN / "skills").glob("*/SKILL.md")
        }
        self.assertTrue(self.EXPECTED_RESEARCH_SKILLS <= actual)

        for name in self.EXPECTED_RESEARCH_SKILLS:
            skill = PLUGIN / "skills" / name / "SKILL.md"
            text = skill.read_text(encoding="utf-8")
            self.assertNotIn("[TODO", text, name)
            self.assertTrue(text.startswith("---\n"), name)
            frontmatter = text.split("---", 2)[1]
            keys = re.findall(r"^([a-z_]+):", frontmatter, flags=re.MULTILINE)
            self.assertEqual(keys, ["name", "description"], name)
            self.assertIn(f"name: {name}\n", frontmatter)

            agent = PLUGIN / "skills" / name / "agents/openai.yaml"
            self.assertTrue(agent.is_file(), name)
            self.assertIn(
                f"$" + name,
                agent.read_text(encoding="utf-8"),
                name,
            )

    def test_orientation_skill_is_adaptive_and_opt_in(self):
        skill_dir = PLUGIN / "skills/orient-scientific-project"
        skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        user_guidance = (
            skill_dir / "references/explaining-to-users.md"
        ).read_text(encoding="utf-8")
        agent_guidance = (
            skill_dir / "references/orienting-agents.md"
        ).read_text(encoding="utf-8")
        notice_guidance = (
            skill_dir / "references/recording-research-notices.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Do not require an explicit audience mode", skill)
        self.assertIn("Do not pause authorized scientific work", skill)
        self.assertIn("do not execute project code", skill)
        self.assertIn("working-tree developments", skill)
        self.assertIn("navigation, never as substitutes", skill)
        self.assertIn("project-specific prerequisites", skill)
        self.assertIn("local-context bias", skill)
        self.assertIn("Do not infer complete project knowledge", user_guidance)
        self.assertIn("Check for local fixation", agent_guidance)
        self.assertIn("return a candidate notice", notice_guidance)
        self.assertIn("rather than a mandatory schema", notice_guidance)
        notice_template = (
            PLUGIN
            / "skills/scaffold-manuscript-project/assets/RESEARCH_NOTICES.md.template"
        )
        self.assertTrue(notice_template.is_file())
        self.assertIn(
            "not scientific evidence",
            notice_template.read_text(encoding="utf-8"),
        )
        scaffold_script = (
            PLUGIN
            / "skills/scaffold-manuscript-project/scripts/scaffold_project.py"
        ).read_text(encoding="utf-8")
        self.assertIn("--with-research-notices", scaffold_script)

        handoff_skills = (
            "explore-scientific-ideas",
            "research-scientific-literature",
            "derive-scientific-results",
            "implement-scientific-computations",
            "verify-manuscript-results",
        )
        for name in handoff_skills:
            text = (PLUGIN / "skills" / name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("$orient-scientific-project", text, name)
            self.assertIn(
                "Do not interrupt authorized nearby adjudication solely to record it.",
                text,
                name,
            )

    def test_evidence_calibration_separates_claim_kinds_and_reranks_drift(self):
        skill_dir = PLUGIN / "skills/calibrate-scientific-evidence"
        skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        cases = (skill_dir / "references/claim-route-cases.md").read_text(
            encoding="utf-8"
        )
        agent = (skill_dir / "agents/openai.yaml").read_text(encoding="utf-8")

        for phrase in (
            "Physical conclusion",
            "Mathematical theorem",
            "Implementation check",
            "Do not collapse these axes into one hierarchy",
            "physical-information gain",
            "downstream consumer",
            "Count milestones, not commits",
            "Before a third consecutive non-observable milestone",
            "closes only itself",
            "not theorem-certified",
            "Work read-only by default",
        ):
            self.assertIn(phrase, skill)

        self.assertIn("Open-boundary second-order response", cases)
        self.assertIn("Strong cancellation or a near-threshold result", cases)
        self.assertIn("Constraint or channel closure failure", cases)
        self.assertIn("before choosing the next research step", cases)
        self.assertIn("$calibrate-scientific-evidence", agent)
        self.assertIn("Match physical claims, assumptions, and rigor", agent)

        for name in (
            "explore-scientific-ideas",
            "derive-scientific-results",
            "implement-scientific-computations",
            "orient-scientific-project",
        ):
            text = (PLUGIN / "skills" / name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("$calibrate-scientific-evidence", text, name)

        agents_template = (
            PLUGIN
            / "skills/scaffold-manuscript-project/assets/AGENTS.md.template"
        ).read_text(encoding="utf-8")
        self.assertIn("$calibrate-scientific-evidence", agents_template)
        self.assertIn("direct calculation, analytic estimation", agents_template)
        self.assertIn("before a third consecutive same-branch milestone", agents_template)
        self.assertIn("read-only scientific dependency", agents_template)
        self.assertIn("project-declared resource guards", agents_template)

    def test_research_handoffs_are_explicit_and_lightweight(self):
        literature = (
            PLUGIN / "skills/research-scientific-literature/SKILL.md"
        ).read_text(encoding="utf-8")
        citations = (
            PLUGIN / "skills/manage-manuscript-citations/SKILL.md"
        ).read_text(encoding="utf-8")
        derivation = (
            PLUGIN / "skills/derive-scientific-results/SKILL.md"
        ).read_text(encoding="utf-8")
        implementation = (
            PLUGIN / "skills/implement-scientific-computations/SKILL.md"
        ).read_text(encoding="utf-8")
        verification = (
            PLUGIN / "skills/verify-manuscript-results/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("CITATION_PLAN.md", literature)
        self.assertIn("$manage-manuscript-citations", literature)
        self.assertIn("$research-scientific-literature", citations)
        self.assertIn("init_citation_plan.py", citations)
        self.assertIn("candidate", citations.lower())

        self.assertIn("verification/", derivation)
        self.assertIn("$verify-manuscript-results", derivation)
        self.assertIn("$verify-manuscript-results", implementation)
        self.assertIn("$derive-scientific-results", verification)
        self.assertIn("$implement-scientific-computations", verification)
        self.assertIn("candidate", verification.lower())

        for text in (literature, derivation, implementation):
            self.assertNotIn("run registry", text.lower())
            self.assertNotIn("artifact database", text.lower())

        citation_template = (
            PLUGIN
            / "skills/manage-manuscript-citations/assets/CITATION_PLAN.md.template"
        ).read_text(encoding="utf-8")
        self.assertIn("Assumption or transfer map", citation_template)
        self.assertIn("Verification performed", citation_template)

        restartable = (
            PLUGIN
            / "skills/implement-scientific-computations/references/restartable-computations.md"
        ).read_text(encoding="utf-8")
        parity = (
            PLUGIN
            / "skills/verify-manuscript-results/references/upstream-parity.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Immutable input binding", restartable)
        self.assertIn("Behavioral parity", parity)

    def test_implementation_skill_is_observable_driven(self):
        implementation = (
            PLUGIN / "skills/implement-scientific-computations/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("target observable", implementation)
        self.assertIn("error budget", implementation)
        self.assertIn("scientific conclusion", implementation)
        self.assertIn("intermediate-state errors", implementation)
        self.assertIn("Stop refinement", implementation)
        self.assertIn("insufficient to decide", implementation)
        self.assertIn("Do not claim a stable conclusion", implementation)
        self.assertIn("Protect exploratory freedom", implementation)
        self.assertIn("calculations/` package", implementation)
        self.assertIn("compare direct execution, optimization cost", implementation)
        self.assertIn("decision-relevant equivalence", implementation)
        self.assertIn("project-declared memory", implementation)

    def test_verification_freshness_is_claim_scoped(self):
        verification = (
            PLUGIN / "skills/verify-manuscript-results/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Scope freshness to the named claim", verification)
        self.assertIn("do not rerun unrelated expensive workflows", verification)
        self.assertIn("full cache-bypass audit", verification)
