# Unified Manuscript Project Layout

## Sources of truth

Use this precedence:

1. Explicit user instructions.
2. Primary literature, active derivations, TeX, calculation source, configurations, and executable verification.
3. Repository build and dependency files.
4. `AGENTS.md`, research and citation plans, context indexes, topic packets, and the project manifest.
5. Historical drafts, discussion exports, generated products, and caches.

Descriptions follow source changes; source must not be distorted to satisfy stale documentation.

## Default project contract

The unified scaffold creates the following paths when they are missing:

```text
.
├── AGENTS.md
├── RESEARCH_PLAN.md
├── SCIENTIFIC_PROGRESS.md
├── CITATION_PLAN.md
├── manuscript-project.toml
├── .gitignore
├── requirements.txt
├── requirements-runtime.txt
├── requirements-verification.txt
├── requirements-plot.txt
├── env/                         # local, ignored virtual environment
├── docs/
│   ├── README.md
│   ├── ENVIRONMENT.md
│   ├── context/
│   │   ├── README.md
│   │   └── project-overview.md
│   └── derivations/
│       └── README.md
├── calculations/
│   ├── README.md
│   ├── __init__.py
│   ├── core/__init__.py
│   ├── models/__init__.py
│   ├── workflows/__init__.py
│   └── cli/__init__.py
├── configs/
│   └── README.md
├── verification/
│   ├── README.md
│   ├── verify_all.py
│   └── verify_context_architecture.py
└── <root-TeX-directory>/
    └── MANUSCRIPT_CONTEXT.md
```

Profile and adapter outputs remain conditional. A generated directory is an available boundary, not evidence that it contains a mature scientific object. Adoption mode preserves every existing file and creates only missing paths.

`RESEARCH_NOTICES.md` is an optional output, not part of the unified default. Create and register it only with `--with-research-notices`, or recognize and preserve it when adopting a repository that already has one. Generated `AGENTS.md` always configures `$orient-scientific-project`; when the notice file is absent it explicitly leaves project-wide notice logging disabled.

For a fresh non-adoption apply, the scaffold also creates the ignored `env/` with the Python interpreter used to run the scaffold. This bootstrap is offline, does not enable system site packages, and does not install or upgrade project dependencies. Preview remains read-only. Adoption preserves any existing environment scheme unless bootstrap is explicitly requested after review. Generated adoption commands reuse an established manifest interpreter or one unambiguous local virtual environment; otherwise they expose the portable platform Python launcher as a migration fallback rather than silently claiming that `env/` exists or embedding a machine-specific absolute path. Local virtual environments are selected by structural inspection only and remain unverified until the registered verifier runs.

## Project-file roles

- `AGENTS.md`: cold-start scope, two-hop routing, scientific inheritance, durable invariants, and actual build and validation commands.
- `RESEARCH_PLAN.md`: lightweight record of the central question, candidate branches, decisive results, durable decisions, and the next result that would change direction.
- `SCIENTIFIC_PROGRESS.md`: compact discovery index for durable result keys and stop/go decisions. It routes to topic packets but is not evidence.
- `RESEARCH_NOTICES.md`, when explicitly enabled: human-facing navigation to consequential developments. It is neither evidence nor a second result index, plan, task queue, or session log.
- `docs/context/*.md`: bounded topic packets loaded only when a routing condition matches the task.
- `MANUSCRIPT_CONTEXT.md`: section navigation recovered from active TeX, including definitions, dependencies, artifact links, and current evidentiary status.
- `CITATION_PLAN.md`: claim-to-source rationale, assumption transfer, identity status, placement, and rejected-source decisions; it does not duplicate the bibliography.
- `docs/README.md`: documentation entry point and routing map.
- `docs/ENVIRONMENT.md` and `requirements-*.txt`: reproducible environment contract separated into runtime, independent verification, and plot-only layers.
- `docs/derivations/README.md`: index and evidence boundary for focused derivation notes. Derivations themselves remain authoritative.
- `calculations/`: promotion path for reusable scientific code.
- `configs/`: versioned scientific inputs created when reuse, shared review, or a promoted claim requires their schema and semantics to be durable.
- `verification/`: fresh-input structural, symbolic, numerical, and cross-artifact assertions.
- `manuscript-project.toml`: machine-readable active paths, commands, input declarations, generated-artifact provenance, and review rules.
- `.gitignore`: excludes build products, local environments, scratch material, caches, and generated verification outputs without hiding active scientific source.

Names are defaults. In adoption mode, preserve an established equivalent rather than overwriting it, and report any missing routes that require manual reconciliation.

## Research workflow

Use the research plan as shared decision context, not as a task database. Idea exploration, literature research, derivation, computation, citation management, result verification, and manuscript editing are available routes, not a required sequence. Choose only the routes that directly serve the scientific question, and update the plan only when a question, hypothesis, decisive result, or research decision will matter in a later session.

Search `SCIENTIFIC_PROGRESS.md`, load one matching topic packet, then inspect the linked scientific source or verifier. The default context should remain small enough for cold start; do not load every packet or the full research plan automatically.

Use `$orient-scientific-project` when a user or cold-start agent needs that evidence chain explained as a decision-centered mainline. If notices are enabled, use them only to locate developments worth explaining and reconcile them against authoritative sources before relying on them.

## Calculation and derivation boundaries

Allow cheap scripts, parallel prototypes, provisional manuscript text, and temporary branches under ignored scratch space while assumptions or observables are unsettled. Match configuration and verification effort to the strength, reuse, and decision relevance of the claim. Promote only work that is reusable, claim-bearing, or repeatedly depended upon.

The canonical calculation package is:

```text
calculations/
├── core/       # domain-light numerical and runtime primitives
├── models/     # equations, conventions, units, and parameterization
├── workflows/  # reproducible composition into research tasks
└── cli/        # thin command-line adapters
```

Prefer the dependency direction `cli -> workflows -> models/core`; keep `core` independent of project models and interfaces. A promoted calculation should define inputs, outputs, units, tolerances, failure modes, and verification routes. Do not move a narrative or unsettled derivation into package code merely to fill a layer. Keep focused analytic work under `docs/derivations/` until executable logic has a stable consumer.

## Environment and output layers

`requirements-runtime.txt` contains packages required by claim-bearing calculations. `requirements-verification.txt` contains independent analytic, test, and bibliography-audit dependencies. `requirements-plot.txt` contains figure-generation dependencies. `requirements.txt` composes the complete default environment.

Populate those layers only from active code, selected adapters, or the accepted immediate calculation. Do not infer a numerical stack from a portfolio of speculative branches. Installation is a separate reviewed action because it may use the network; never upgrade pip merely as an initialization side effect.

Generated plots, tables, arrays, PDFs, checkpoints, and caches are outputs, never evidence inputs by default. A nonempty `artifacts.generated` entry uses the contract:

```toml
{ source = "relative/path/to/generator", outputs = ["relative/path/to/output"] }
```

The source must be an active generator or workflow. Output paths may be absent before execution. If a generated object becomes an input to a claim, register the source workflow and a fresh-input verifier rather than treating the cached file as authority.

## Antecedent work and evolving notes

When a project builds on earlier manuscripts, codebases, or calculations, record their scientific role rather than listing only paths. For each antecedent source, identify:

- the result that the new project inherits;
- the assumptions and validity domain attached to that result;
- the reusable equations, data, code, or benchmarks;
- the specific new ingredient introduced by the active project;
- the condition that would force the inherited result to be revisited.

Do not equate implementation validation with conceptual uncertainty. A benchmark can require local reproduction while its mechanism and classification remain established upstream.

Treat exported chats and chronological research notes as evolving records. Recover explicit user corrections and later integrated conclusions before synthesizing them. Do not use repetition or keyword salience to resolve contradictions. Label a disagreement unresolved when no later decision settles it.

If the active TeX is only an empty scaffold, do not infer a scientific narrative from section names. Use declared antecedent sources and durable user decisions, and mark unsupported project-specific claims `Not established`.

The six generic section files are a neutral integration graph, not a universal scientific outline. Rename or restructure them only when the audited sources already establish a stable project-specific argument. Keep topic-specific section names out of reusable domain profiles.

## Cold-start orientation standard

The initialized guidance is complete only when it supports a new session that cannot see the scaffolding conversation. Require the following:

- Every antecedent source has a short description of its role, established result, reusable objects, validity limits, and relation to the new project.
- The project gap names the new regime, mechanism, observable, or decision rather than saying only that an earlier method will be applied.
- Every active manuscript section has a purpose and expected content; bare include paths are only a machine-discovered starting point.
- The research plan distinguishes accepted upstream results from local reproduction tasks and states the smallest decisive next result.
- Unknown scientific content is marked `Not established` with a route to establish it. Generic prompts must not remain in a project declared initialized.

Prefer one informative paragraph or several precise bullets per item. Do not inflate guidance into a second manuscript or duplicate full derivations.

## Cross-artifact and portability rules

- Store project paths relative to the repository root.
- Keep commands as argument arrays rather than shell strings in the manifest.
- Keep online checks separate from the default command group. `default` is not a network-isolation guarantee.
- Treat sync rules as review prompts. Mark `required = true` only for a mechanical contract.
- Register a generated figure or table only when its source and output paths are explicit.
- Do not classify a file as active merely because it is named `main.tex`; inspect include relationships, build configuration, guidance, and output dependencies.
- Keep scientific formulas, constants, expected values, selected references, and domain conventions in the project.
