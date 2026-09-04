# Claim-route calibration cases

Use these cases to test the distinction between physical establishment, mathematical proof, and implementation validation before choosing the next research step. They are patterns, not domain-specific claim templates.

## Open-boundary second-order response

### Situation

A project asks whether a second-order return amplitude changes the sign or scale of a named output for a smooth source, finite observation time, fixed channel truncation, and declared open-boundary prescription. A separate possible project would prove a uniform continuum stability theorem for the same evolution operator.

### Correct route split

- Classify the output question as a conditional physical conclusion. Compute the finite-model return, vary the material truncation and boundary controls, check constraints and flux or action normalization, and judge the stated output at its own error scale.
- Classify the uniform stability statement as a mathematical theorem. Specify its spaces, domains, boundary data, and bound, and pursue it independently when it has mathematical value.
- Make the theorem a prerequisite for the physical result only if a bridge test shows that no controlled finite-time assumption or observable-level check can bound the present conclusion.

### Wrong move

Do not begin the physical task by constructing an unrestricted semigroup, trace, adjoint, and posterior theorem merely because those objects would support a stronger future statement. Do not reinterpret failure of that proof program as evidence that the finite conditional response is uncomputable.

## Strong cancellation or a near-threshold result

### Situation

A physical observable is a difference or interference of larger terms, and the current numerical movement is comparable to the decision margin.

### Correct route split

- Keep the claim physical and strengthen controls that propagate to the observable: phase and normalization checks, separate variation of material discretization controls, a second formulation or reduced model, and an uncertainty statement at the cancellation scale.
- Report the physical question as unresolved when reasonable variations can change the sign, hierarchy, or threshold decision.
- Escalate to a mathematical bound only when that bound controls the observed amplification or cancellation more directly than the available physical checks.

### Wrong move

Do not demand uniform high-precision convergence of every intermediate state, and do not accumulate unrelated invariants or verification machinery after the observable-level uncertainty is already decisive.

## Constraint or channel closure failure

### Situation

A refined calculation shows a growing constraint residual, omits a channel required by the claimed flux relation, or uses boundary data inconsistent with the intended physical process.

### Correct route split

- Treat the affected conditional physical claim as blocked in that formulation. Repair or redirect the model or implementation and repeat the closure test before interpretation.
- Preserve any independent mathematical theorem only at the scope of the operator and boundary problem it actually treats.
- Reopen the physical route only when new evidence addresses the observed defect rather than renaming the representation or weakening the check.

### Wrong move

Do not list an observed closure failure as a plausible physical assumption. Do not use a theorem about a different abstract operator or a successful software smoke test to certify the failed physical formulation.
