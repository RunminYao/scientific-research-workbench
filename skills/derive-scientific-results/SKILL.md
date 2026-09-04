---
name: derive-scientific-results
description: Derive scientific equations, approximations, scaling relations, limiting cases, and analytic estimates while preserving conventions and assumptions. Use when Codex needs to work through mathematical details, reconcile formulas, translate a mechanism into a new physical setting, identify an approximation domain, or determine what an analytic result actually implies.
---

# Derive Scientific Results

Make the derivation auditable without turning exploratory work into manuscript infrastructure.

## Establish the problem

1. Read the local source that defines the notation and the minimum surrounding material needed to recover assumptions.
2. When a result index exists, inspect the matching topic packet and any superseded derivation before repeating or extending it.
3. State the mathematical problem, dependent variables, evolution variable, initial or boundary conditions, and requested observable.
4. Declare conventions that can change signs or interpretation, including metric, Fourier phase, polarization basis, normalization, and fixed-frequency versus fixed-momentum evolution.
5. Separate source-given equations from relations introduced in the current derivation.
6. Use `$calibrate-scientific-evidence` when the requested physical argument begins expanding into a distinct theorem program or when a mathematical prerequisite is proposed without an explicit bridge to the target observable or interpretation.

## Derive

1. Define symbols before operative use.
2. Keep the dependency order visible: setup, reduction, approximation, result, interpretation.
3. Show steps that introduce a new assumption, discard a term, change representation, or select a solution branch. Compress routine algebra that does none of these.
4. Track dimensions and expansion parameters.
5. Check relevant zero-coupling, static, symmetry, high- or low-frequency, and known-result limits.
6. State the domain in which every approximation is controlled. Do not infer validity solely from numerical agreement at one benchmark.

## Use computation proportionately

- Use a short symbolic or numerical check when algebra is fragile or a limiting case is ambiguous.
- Keep paper-specific formulas and checks in the project, not in this reusable skill.
- Do not generate derivation ledgers, equation registries, or new notes by default.

## Hand off candidate checks

When a derivation will be reused, resolves fragile algebra, or may support a manuscript claim:

1. Express an exact result as a named residual expected to simplify to zero. Express a numerical result with explicit parameters, units, expected value, and absolute or relative tolerance.
2. If the repository already has a `verification/` layout, create or extend the narrowest project-local check there. Make failure return nonzero and print the residual or tolerance violation.
3. If no verification layout exists, use `$verify-manuscript-results` to preview and apply its scaffold before adding the check. Do not invent a parallel test hierarchy.
4. Treat the new script as a candidate check. Continue with `$verify-manuscript-results` when the task includes formalization: review independence, register the command, execute it from fresh inputs, and connect it to the claim.

The derivation skill may generate the candidate script, but it must not claim that approximation validity or physical interpretation has been proven by a symbolic pass.

Do not promote a result index entry from diagnostic or open status solely because a candidate derivation check passes. Formal verification must identify the exact object established, while approximation validity and interpretation retain separate evidence.

## Preserve meaning

- Do not silently change conventions, gauge, approximation hierarchy, evolution problem, or observable.
- Treat algebraic identity, numerical agreement, approximation validity, and physical interpretation as distinct claims.
- When a result would materially change how a future user or agent understands the research mainline, use `$orient-scientific-project` to preserve or update a human-facing notice if the project has opted into one. Do not interrupt authorized nearby adjudication solely to record it.
- Flag ambiguous source notation instead of resolving it by guesswork.

## Report

- Present the result together with its assumptions and validity domain.
- Identify which checks passed and which were only argued qualitatively.
- Distinguish an exploratory calculation, a candidate verification script, and a formally executed verification check.
- Explain the physical implication at the scope justified by the derivation.
- Edit TeX or research notes only when requested; use `$edit-scientific-manuscripts` when the task includes integrating the result into the active paper.
