---
name: scaffold-manuscript-project
description: Scaffold or adopt a portable scientific research and LaTeX manuscript repository with bounded context, citation planning, computation and configuration boundaries, layered environments, and executable structural verification. Use when Codex needs to initialize or retrofit a manuscript project, map active TeX and bibliography sources, preserve inherited-versus-new scientific scope, or establish a complete evidence-aware workspace without inventing project-specific science.
---

# Scaffold Manuscript Project

Build one coherent research workspace around the active manuscript while keeping primary sources, derivations, calculation code, TeX, configurations, and executable verification authoritative.

## Workflow

1. Inspect existing `AGENTS.md`, research and citation plans, context indexes, root TeX candidates, `\input`/`\include` chains, bibliography declarations, figure paths, calculation and verification code, environment files, build commands, project resource-guard commands and policies, and explicitly declared antecedent or out-of-tree scientific references.
2. Distinguish active sources from drafts, generated outputs, caches, exploratory work, and historical alternatives. Preserve established repository conventions when they already fulfill a generated role.
3. Read [references/project-layout.md](references/project-layout.md) for the unified output contract and [references/research-context.md](references/research-context.md) for the bounded result-index and topic-packet contract.
4. Before filling scientific orientation, build a compact inheritance audit:
   - results established by antecedent sources or existing calculations;
   - results established locally in the active project;
   - genuinely new project questions;
   - working hypotheses and pending verification;
   - assumptions whose failure would require reopening an inherited result.

   Read the scientific content of each declared antecedent source, not only its title, abstract, path, or root wrapper. When a source provides a context index, use it to route into the relevant body sections and appendices. Declare each out-of-tree source's mutability and reuse boundaries; treat it as a read-only scientific dependency unless edits are explicitly authorized, and do not silently vendor it or register its expensive workflows as local defaults.
5. If research notes are chronological or iterative, recover the correction chain before synthesizing them. Later explicit user corrections and integrated conclusions supersede earlier exploratory answers. Preserve unresolved disagreements instead of merging incompatible claims.
6. Select the most specific profile only when the user request and inspected sources unambiguously match it; otherwise use `generic`. Preview the scaffold. For an empty repository, omit `--root-tex` so the scaffold can create `paper/main.tex` and the section graph:

   ```bash
   python3 <skill-dir>/scripts/scaffold_project.py \
     --project-root <repo> \
     --profile generic
   ```

   For a repository that already has a manuscript, pass its active root explicitly when discovery or the manifest does not already identify it:

   ```bash
   python3 <skill-dir>/scripts/scaffold_project.py \
     --project-root <repo> \
     --root-tex <relative/path/main.tex>
   ```

   The unified default proposes:

   - repository guidance that routes `$orient-scientific-project`, a research plan, a bounded result index, a starter topic packet, and a citation plan;
   - the manuscript context index beside the root TeX file;
   - documentation, environment, derivation-note, calculation, and configuration contracts;
   - the canonical `calculations/{core,models,workflows,cli}` Python promotion path;
   - a manifest, layered requirement contracts, output exclusions, a verification guide, a verification orchestrator, and a structural context verifier.

   The presence of these paths establishes routing and evidence boundaries; it does not assert that a scientific result, reusable calculation, active configuration, or citation has been established.

   A fresh non-adoption `--apply` also creates an ignored repository-local `env/` using the interpreter that runs the scaffold. Preview never creates it. Bootstrap uses standard-library `venv`, disables system site packages, and neither installs packages nor upgrades pip. Use `--no-bootstrap-environment` only when environment creation is deliberately managed elsewhere.

   Keep the human-facing research notice log explicit. Add `--with-research-notices` only when the user wants the initialized project to maintain that optional navigation aid:

   ```bash
   python3 <skill-dir>/scripts/scaffold_project.py \
     --project-root <repo> \
     --with-research-notices
   ```

   This proposes `RESEARCH_NOTICES.md`, declares it enabled in generated repository guidance, and registers the path for structural review. Without the flag, generated guidance configures project orientation but states that no project-wide notice log is enabled. Adoption also recognizes and preserves an existing `RESEARCH_NOTICES.md` as an established opt-in.
7. For an existing manuscript repository, preserve established files with adoption mode:

   ```bash
   python3 <skill-dir>/scripts/scaffold_project.py \
     --project-root <repo> \
     --root-tex <relative/path/main.tex> \
     --adopt
   ```

   Adoption mode keeps every existing project file and `manuscript-project.toml` intact, uses configured manuscript paths before heuristic discovery, reports missing orientation references, and creates only missing files. Review preserved files semantically; adoption never makes a stale or incomplete contract authoritative.

   Adoption preserves existing environment directories and specifications by default. Use `--bootstrap-environment` with `--adopt` only after confirming that a new repository-local `env/` will not compete with Conda, Poetry, uv, or another established environment contract. Reuse an established manifest interpreter or one unambiguous local virtual environment. When neither exists, use a portable Python launcher as an explicit migration fallback and require review rather than embedding the scaffolder's machine-specific interpreter path. Treat a discovered local environment as structurally selected but unverified until its registered verifier runs.

   Preserve any established memory, scheduler, cluster, or runtime guard during adoption. Surface its authoritative command and thresholds in project guidance when they are already declared; do not infer limits from machine capacity or invent a generic guard for a repository that has none.

   `--mature-research` and `--with-calculation-layout` remain accepted compatibility aliases for the unified default. They do not add or remove outputs and should not be used to describe separate scaffold modes.

   Use `--profile generic|hep-astrophysics|axion-phenomenology` to select a starter. Domain profiles may initialize an empty repository with a compilable RevTeX 4.2 manuscript, bibliography resource, notation starter, and explicit convention guidance without inventing conclusions. The axion-phenomenology profile adds an input contract for axion/ALP conventions, QCD inputs, dark-matter and cosmological priors, experiment releases, inference semantics, coherence, and approximation limits. The portable build uses BibTeX with `apsrev4-2`; review compatibility before adding BibLaTeX-only entry types.

   The isolated `latexmk` build adapter is part of the unified default; an explicit `--adapter latexmk` remains harmless for compatibility. Add any of `--adapter jupyter|sympy|mathematica|slurm` repeatedly when needed. Adapters only generate reviewable files and dependency diagnostics. Local adapters may register commands under `verification.default`. The SLURM adapter never registers `sbatch`, installs software, submits jobs, or polls a scheduler.
8. Review every proposed path, command, dependency, generated-artifact declaration, and section. Apply only after the preview is correct, repeating the same discovery/profile/adoption arguments:

   ```bash
   python3 <skill-dir>/scripts/scaffold_project.py \
     --project-root <repo> \
     --profile generic \
     --apply
   ```

9. Replace generated scientific-orientation prompts using the inheritance audit. Keep inherited results, verified local results, conditional or diagnostic findings, working hypotheses, and unresolved questions distinct. Do not promote a caution, validity condition, or completed antecedent result into a primary project objective unless the new regime violates its assumptions. If the active manuscript is only a scaffold, derive orientation from declared antecedent sources and durable user decisions rather than empty section headings.

   Keep one overview packet unless the audit already exposes distinct durable evidence routes or stopped branches that need separate bounded context. Let those boundaries determine packet names and count; never copy another project's taxonomy. Treat the generic manuscript sections as a neutral integration graph. Rename or restructure them only when the audited material establishes a stable project-specific argument, and keep such section names out of reusable profiles.
10. Perform a cold-start review of the filled guidance. Using only the generated project files, a new session must be able to answer:
    - what the project is trying to determine and why;
    - which results are already established and where;
    - what remains genuinely new or unresolved;
    - which assumptions and validity limits control reuse;
    - which manuscript, bibliography, calculation, configuration, figure, and verification files are active;
    - what the next decisive scientific uncertainty is and what outcome would redirect the project.
    - how to invoke project orientation for a user or subagent, and whether a human-facing notice location is enabled.

    Replace every instructional scientific placeholder before declaring initialization complete. If evidence is unavailable, write `Not established` and the required source check, derivation, computation, or verification rather than leaving a generic prompt. A path-only reference list, bare include map, or one-line topic label is not sufficient scientific orientation.
11. Confirm that idea exploration, literature research, derivation, computation, citation management, result verification, and manuscript editing remain optional routes selected by the scientific question rather than a required sequence. Do not force speculative work into canonical directories or require durable artifacts before they preserve evidence, support reuse, or carry a promoted claim. Populate requirement layers only from active code, selected adapters, or the accepted immediate calculation; never choose a stack from speculative portfolio branches. Install reviewed requirements explicitly in `env/`, requesting network access when downloads are required.
12. Run the generated structural verifier with the repository environment, then the repository build and registered default verification commands. Inspect every failure before relying on the context index:

    ```bash
    env/bin/python verification/verify_context_architecture.py
    env/bin/python verification/verify_all.py
    ```

    `verification.default` is only a command group; it does not imply network isolation. Installing the declared environment, passing structural checks, or compiling the manuscript is implementation validation, not scientific verification.

## Scaffold boundaries

- Create files only inside the selected project root.
- Preview before applying. Do not overwrite an existing file unless the user explicitly requests `--force`.
- Never replace or clear an existing environment as an incidental scaffold action. Environment recreation and dependency installation are separate, reviewable changes.
- Prefer `--adopt` over `--force` for established repositories.
- Never overwrite an existing `manuscript-project.toml` in adoption mode. Review missing optional sections semantically rather than replacing mature verification, seed, cache, artifact, or synchronization configuration.
- Treat generated guidance and the manifest as routing aids, not authority over scientific sources or code.
- Keep implementation validation distinct from conceptual novelty. Reproducing an inherited benchmark may be required before reuse without making its established mechanism an open research question.
- Put project-specific formulas, numerical constants, selected citations, configuration values, expected results, and scientific claims in the project, not in this reusable skill.
- Preserve explicit out-of-tree dependency permissions and project resource guards during adoption; do not replace them with reusable-plugin defaults.
- Keep the research plan lightweight: record durable questions, hypotheses, decisive results, and decisions rather than session logs or artifact registries.
- Protect exploratory freedom: allow cheap prototypes and parallel routes under ignored scratch space, then promote work only when it becomes reusable, claim-bearing, or repeatedly depended upon.
- Treat `calculations/{core,models,workflows,cli}` as a promotion path for durable computation, not a requirement to populate layers. Keep derivation notes under `docs/derivations/` until executable logic belongs in the calculation package.
- Scratch work may keep local inputs near the calculation. Create an active configuration when inputs become reusable or support a promoted claim, and then define its physical or mathematical object, units, schema, boundaries, solver controls, provenance, and observable-level tolerances.
- Keep generated plots, arrays, PDFs, caches, and checkpoints out of scientific evidence inputs by default. Every nonempty generated-artifact manifest entry must name one source and an explicit output list.
- Reject a filled scaffold that does not state what is inherited, what is new, and which evidence would justify revisiting that boundary.
- Keep orientation concise but explanatory. Describe the scientific role and decision relevance of a source or file; do not merely restate its filename, title, or section heading.
- Configure `$orient-scientific-project` in generated repository guidance. Keep human-facing notices opt-in: generate `RESEARCH_NOTICES.md` only for `--with-research-notices`, preserve an existing file during adoption, and never treat it as scientific evidence or a substitute for the result index or research plan.
- Use `$manage-manuscript-citations` to verify citation identity and rationale before bibliography edits. Use `$verify-manuscript-results` when a derived or numerical result is being promoted as reusable or established evidence; provisional analysis and drafting may remain explicitly labeled as such.
