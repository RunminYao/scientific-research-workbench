---
name: implement-scientific-computations
description: Implement, extend, and diagnose scientific numerical or symbolic calculations from equations and research requirements, using observable-level error budgets and conclusion-driven convergence. Use when Codex needs to reproduce a paper benchmark, translate a model into code, add observables, design a focused parameter scan, compare analytic and numerical results, or determine whether a computational result is trustworthy.
---

# Implement Scientific Computations

Build the smallest calculation that answers the scientific question at sufficient, not maximal, accuracy and leaves a reproducible path for the next step.

## Recover the computational contract

1. Inspect repository guidance, existing code, tests, configuration, and the equations that define the calculation.
2. When a result index exists, inspect the matching topic packet and any stopped or superseded route before launching a scan or building a parallel implementation.
3. Identify the target observable, benchmark, independent variables, initial or boundary conditions, units, conventions, expected limiting behavior, and the scientific conclusion or decision the result must support.
4. Define the observable-level accuracy needed to distinguish the relevant outcomes. Use a named absolute or relative tolerance when justified; otherwise bracket the conclusion with sensitivity variations or bounds and report the unresolved uncertainty instead of inventing a threshold.
5. Build a lightweight error budget that separates numerical error, model or approximation error, and input uncertainty. Identify which intermediate-state errors can materially propagate to the target observable, violate a required invariant, or destabilize the calculation.
6. Distinguish physics parameters, numerical controls, and presentation-only settings.
7. Prefer the active implementation when it is a natural fit. Allow a parallel prototype when it helps compare assumptions, methods, or observables without prematurely reshaping mature code.
8. Use `$calibrate-scientific-evidence` when an absent theorem is being used to block an assumption-bounded calculation, when the intended claim kind is unclear, or when repeated infrastructure work no longer changes the observable-level decision.

## Research workspace aesthetic

Protect exploratory freedom while keeping durable knowledge understandable.

- Let exploratory scripts and parallel prototypes remain lightweight while the scientific direction is unsettled.
- Consolidate only after an artifact becomes reusable, claim-bearing, or repeatedly depended upon.
- When work becomes durable, make its authoritative source and scientific role reasonably easy to discover.
- Preserve decision-relevant negative conclusions, but do not formalize every abandoned experiment.
- Organize when organization lowers the cost of the next scientific decision; otherwise continue exploring.

## Implement

1. Start with one minimal benchmark that can fail informatively.
2. Choose the least costly method, resolution, and precision that can satisfy the target observable's error budget.
3. Do not require uniform high-precision convergence of intermediate states. Tighten them only when their errors materially affect the target observable, a required conservation or normalization relation, numerical stability, a strong cancellation, or a threshold decision.
4. Keep model equations, solver logic, analysis, and plotting separable enough to test.
5. Make physics parameters and numerical controls explicit in code or a simple existing configuration format. Use numerical controls to estimate relevant error, not to accumulate thresholds for their own sake.
6. Use deterministic seeds for stochastic calculations and report them with the run command.
7. Avoid hidden import-time execution, stale plot caches, and silent fallback behavior.
8. Add abstractions when they clarify the current calculation or an emerging repeated use; do not require exploratory work to predict its final architecture.

When a project benefits from a layered `calculations/` package, use `core/` for reusable numerical and runtime primitives, `models/` for scientific equations and parameterization, `workflows/` for reproducible composition, and `cli/` for thin command-line adapters. Treat this as an optional promotion path, not a prerequisite for exploratory scripts or small projects.

Before a calculation that is clearly long-running or likely to be repeated, compare direct execution, optimization cost, an equivalence benchmark, and optimized production execution. Optimize only when the expected reuse or runtime reduction justifies the added validation work, and establish decision-relevant equivalence before relying on optimized output.

Follow project-declared memory, scheduler, cluster, and runtime guards for every covered execution path, including exploratory entry points. Before overriding a declared limit, record a measured or defensible resource estimate and preserve the project-required headroom; do not invent universal thresholds in this reusable skill.

For a long-running independent-node calculation that must survive interruption, read [references/restartable-computations.md](references/restartable-computations.md). Use input-bound checkpoints and deterministic response-blind partitions only when restartability is materially needed; do not turn routine calculations into run registries.

## Check

Use the checks appropriate to the problem:

- analytic or source benchmark reproduction;
- zero-coupling, symmetry, conservation, normalization, or asymptotic limits;
- sensitivity of the target observable and scientific conclusion to solver tolerance, step size, resolution, volume, or parameter grid;
- separate variation of material numerical controls, with conservative combination when their effects cannot be isolated cleanly;
- intermediate-state convergence only when its error can propagate materially, violate a required invariant, or destabilize the calculation;
- independent formulation or reduced model for a high-risk result;
- explicit residuals and actionable failure output.

Estimate numerical uncertainty at the target observable. Stop refinement when it is below the observable's error budget and reasonable numerical variations cannot change the sign, trend, parameter exclusion, significance, or ordering that supports the scientific conclusion.

If the result lies near a decision boundary, depends on strong cancellation, or has enough uncertainty to change the conclusion, tighten the relevant calculation or report that the current computation is insufficient to decide. Do not claim a stable conclusion.

Run the narrowest tests that cover the change, then the relevant end-to-end benchmark. Neither a successful plot nor uniformly high-precision convergence of every intermediate state is, by itself, a validation criterion or research objective.

## Artifact policy

- Modify the requested code and its focused tests; do not introduce run registries, provenance databases, experiment schemas, or report files unless asked.
- Use Git state, explicit configuration, deterministic seeds, and documented commands as the default lightweight provenance.
- Retain helper scripts freely during exploration; promote and clarify them when they constrain a repeated or error-prone calculation or become a dependency of durable work.
- Register a stable build or verification command in existing project guidance only when it will remain part of the workflow.
- Focused code tests remain with the implementation. When a benchmark, curve, or numerical value is ready to substantiate a manuscript claim, hand its fresh-calculation check, parameters, units, and tolerances to `$verify-manuscript-results` for registration and formal execution.
- When a result would materially change how a future user or agent understands the research mainline, use `$orient-scientific-project` to preserve or update a human-facing notice if the project has opted into one. Do not interrupt authorized nearby adjudication solely to record it.
- Update a topic packet only when a durable result, limitation, or active gap changes. Update a result index only when discovery or a stop/go decision changes; never promote an implementation success directly into a manuscript claim.

## Report

- State what was implemented, the target observable, and the scientific conclusion or decision it can support.
- Give the exact command or test used, the benchmark result, and relevant tolerances.
- Report the error budget, estimated numerical uncertainty, and dominant error source.
- Give the evidence that the scientific conclusion is stable and explain why refinement stopped or why the current computation remains insufficient.
- Identify materially unconverged intermediate states and explain why they do or do not affect the target observable.
- Identify any check handed to formal verification and whether it is still a candidate or has been executed through the verification workflow.
- Separate numerical error, model or approximation error, input uncertainty, and physical interpretation.
- Report unsupported regimes, failed checks, and modeling decisions that still require the user.
