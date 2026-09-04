---
name: calibrate-scientific-evidence
description: Calibrate scientific claim types, assumptions, evidence standards, and route priorities before or during research. Use when Codex must distinguish a physical conclusion under stated assumptions from a mathematical theorem or an implementation check; decide whether computation, derivation, or formal proof is the appropriate next step; audit repeated reformulations, contracts, verifiers, or infrastructure that have not changed an observable; or determine exactly what a failed gate blocks.
---

# Calibrate Scientific Evidence

Keep physical conclusions, mathematical theorems, and implementation checks distinct, then choose the smallest route that can establish the intended object. Do not treat mathematical completeness as a higher rung of physical evidence.

## Recover the decision

1. Read repository guidance, the active research decision, and the shortest evidence route relevant to the proposed work.
2. Name the target result before selecting a method: a physical observable or regime decision, a mathematical theorem, or an implementation property.
3. State the assumptions, validity domain, intended consumer, and evidence state needed now rather than for a hypothetical stronger future claim.
4. Inspect stopped and superseded work far enough to distinguish a concrete model failure from a failed representation, proof, solver, or certification route.

## Classify the claim on two independent axes

First classify what is being established. Then classify how far the evidence has progressed. Do not collapse these axes into one hierarchy.

| Claim kind | Object established | Suitable evidence | Does not establish |
| --- | --- | --- | --- |
| Physical conclusion | An observable, scaling, mechanism, hierarchy, or regime statement under declared physical and modeling assumptions | Controlled approximation, analytic estimate, conclusion-driven numerical checks, comparison, or measurement connection | A general existence, uniqueness, or convergence theorem |
| Mathematical theorem | A formal property under explicit hypotheses, spaces, domains, and boundary or initial data | A complete proof or a clearly bounded proof obligation | A detectable, large, or relevant physical effect without an observable bridge |
| Implementation check | Correct behavior of a code path, discretization, transformation, or verifier for a named object | Benchmarks, residuals, invariants, mutation tests, and reproducible execution | Physical validity of the model or truth of a continuum theorem |

Use repository-native evidence labels when available. Otherwise distinguish exploratory or `diagnostic`, assumption-bounded or `conditional`, and established or promoted evidence separately within each claim kind.

## Lock the route before doing the work

- For a physical conclusion, name the observable, decision threshold, controlled approximation, physically motivated assumptions, and checks sufficient to keep the conclusion stable. Do not require a global theorem unless its absence prevents the observable from being defined or its error from being interpreted.
- For a mathematical theorem, state the theorem and hypotheses directly. Do not substitute converged numerics for proof, and do not require the theorem to yield a physical signal when it is an independent mathematical objective.
- For an implementation check, name the implemented object and failure modes. Do not promote a software pass into either of the other claim kinds.
- Keep mathematical and physical routes independently open. Changing the route's claim kind requires an explicit reclassification, not an accumulation of stronger-looking gates.

## Test every proposed mathematical prerequisite

Before making a theorem, regularity lemma, global bound, or certification constant a prerequisite for a physical result, require all of the following:

1. State the exact mathematical conclusion being sought.
2. Map that conclusion to the target observable, its error, or its physical interpretation.
3. Explain which physical conclusion cannot responsibly be made without it.
4. Show why a controlled approximation, sensitivity study, comparison, or direct calculation cannot answer the present decision more cheaply.
5. Give the mathematical route a bounded failure exit.

If any item is missing, keep the mathematical work as an independent branch rather than allowing it to block the physical route.

## Rank candidate routes proportionately

When several routes could establish the requested object, compare feasibility, difficulty, total cost, physical-information gain, and time to the next decision-changing result. Prefer a controlled analytic estimate or the smallest discriminating calculation when it can answer the present question; choose a formal proof when the theorem is the target or when its conclusion is the lowest-cost control of the observable.

Require every expensive route to have a bounded failure exit. Before adding a quantity, invariant, contract, verifier, version, or infrastructure layer, name the scientific decision or downstream consumer it can change; otherwise keep it as a lightweight diagnostic. Repository neatness, a stronger process guarantee, or another invariant at the same anchor is not by itself a scientific payoff.

For a physical claim, use physical question → controlled analytic estimate → smallest discriminating calculation → physical interpretation as a default ordering, not a mandatory pipeline. Add formal closure or workflow machinery only where its absence changes the interpretation.

## Audit route drift

Count logical scientific milestones on the same branch since the last result that computed or bounded the target observable, tested a decisive physical assumption, or discriminated a regime. Count milestones, not commits.

Treat a new representation, theorem, regularity result, norm, contract, verifier, workflow, or solver infrastructure as non-observable work unless it directly changes one of those decision objects.

Before a third consecutive non-observable milestone, stop automatic continuation and compare:

1. a direct assumption-bounded physical calculation;
2. a controlled analytic estimate or limiting case; and
3. continuation of the mathematical or infrastructure route.

Continue the third route only when the next milestone itself changes the physical decision or closes the final named prerequisite for a physical calculation in the immediately following step, and when failure has a declared exit. An independently valuable theorem may continue as a separate mathematical branch, but it must not silently freeze the physical branch.

## Calibrate assumptions

Allow a conditional assumption when it has a physical or source-backed rationale, a declared domain, no contradiction in existing evidence, a consequence if false, and a practical failure signal or sensitivity check.

Do not assume away an observed failure of equation or channel closure, constraints, boundary orientation or compatibility, gauge-safe reconstruction, normalization, conservation, or the definition of the observable. Redirect or repair the affected model or implementation before interpreting that route physically.

Near a cancellation, threshold, instability, or unresolved resonance, strengthen the checks that control the target observable. Do not demand uniform maximal accuracy of unrelated intermediate objects.

## Scope stops and persistence

- A failed mathematical route closes the named theorem or its dependents, not an independently posed conditional physical calculation.
- A failed physical route closes the declared model, regime, or observable claim, not every mathematical formulation or neighboring physical regime.
- A failed implementation closes that implementation unless the evidence also exposes a model-level contradiction.
- An unresolved statistic or diagnostic closes only itself unless it was declared and justified as a prerequisite for a broader claim.
- State both what is blocked and what remains open. Do not translate “not theorem-certified” into “not computable.”
- Work read-only by default. Update a research plan, result index, topic packet, or stop record only when the user asks for persistence or the active task already includes recording a durable decision; use `$orient-scientific-project` for that handoff.

Read [claim-route-cases.md](references/claim-route-cases.md) when a concrete comparison would help distinguish the routes or when testing whether a proposed stop has been scoped correctly.

## Report

Lead with the route decision. State the two-axis claim classification, allowed assumptions and required checks, any drift finding, the ranked alternatives, the smallest decision-changing next result, its stop or escalation condition, and the claims that remain explicitly unblocked.
