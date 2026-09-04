---
name: explore-scientific-ideas
description: Explore scientific mechanisms, research questions, possible derivations, required results, and the implications of different outcomes. Use when Codex needs to reason with the user before a focused literature search, detailed derivation, numerical implementation, or manuscript edit, especially when assumptions and decisive next steps are not yet clear.
---

# Explore Scientific Ideas

Develop the idea far enough to identify what is known, what is conjectured, and which result would change the research decision.

## Recover context

1. Read repository guidance and the active research plan when present.
2. When a compact result index exists, search it by mechanism, observable, script, or result key, load only the matching topic packet, and inspect any stopped or superseded route before proposing new work.
3. Inspect the specific equations, source passages, code, or previous results needed for the question. Do not reload the whole project without a reason.
4. Treat primary scientific sources and executable results as authoritative over discussion notes.

## Reason

1. Restate the scientific question precisely enough to expose hidden choices.
2. Separate:
   - results established by sources or existing calculations;
   - consequences derived in the current analysis;
   - working hypotheses;
   - unresolved factual or semantic questions.
3. Identify the relevant physical or mathematical objects, assumptions, evolution problem, observables, and validity domain.
4. Compare plausible mechanisms or approaches using discriminating criteria rather than listing possibilities.
5. Determine the smallest decisive result: a derivation, limiting case, literature fact, benchmark, or computation.
6. Explain what each materially different outcome would imply. Include reasons to stop or redirect the line of work when they are apparent.

## Continue the work

- Answer the current conceptual question before proposing follow-up work.
- Use `$calibrate-scientific-evidence` before choosing between a conditional physical result and a mathematical theorem, or when two consecutive same-branch milestones have not changed an observable, tested a decisive assumption, or discriminated a regime.
- Use `$research-scientific-literature` for source-dependent questions, `$derive-scientific-results` for a detailed derivation, and `$implement-scientific-computations` for code or numerical experiments.
- Use `$verify-manuscript-results` only when a result is ready to become a reproducible claim.
- Consume downstream evidence when returning to the idea: distinguish candidate citations from citation-verified sources and exploratory checks from formally executed verification.
- Preserve a durable stop decision only when its scope and reopening condition will prevent invalid reuse or costly repetition. Do not relax a negative gate merely to produce a positive continuation.
- When a result would materially change how a future user or agent understands the research mainline, use `$orient-scientific-project` to preserve or update a human-facing notice if the project has opted into one. Do not interrupt authorized nearby adjudication solely to record it.
- Do not create planning files, registries, or status artifacts by default. Update an existing research plan only when the user asks or when the task explicitly includes preserving a durable decision.

## Report

- State the current best-supported conclusion.
- Label assumptions and inferences explicitly.
- Give the next decisive task and the criterion it should resolve.
- Keep unresolved alternatives visible; do not manufacture consensus.
