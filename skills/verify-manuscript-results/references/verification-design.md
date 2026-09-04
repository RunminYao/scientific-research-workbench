# Manuscript Verification Design

## Verification layers

Keep four claims distinct:

1. Symbolic identity: an exact residual simplifies to zero under declared assumptions.
2. Numerical agreement: independently computed values agree within named tolerances.
3. Approximation validity: scale separation and neglected terms are justified in a stated domain.
4. Physical interpretation: the mathematical result answers the claimed observable problem.

Scripts establish the first two. They can expose evidence for the latter two but cannot prove them automatically.

## Symbolic checks

- Construct both sides independently where practical.
- Check a residual rather than reproducing the manuscript expression verbatim.
- Declare symbol assumptions explicitly.
- Report nonzero residuals and the check name.
- Test matrices componentwise.
- Avoid substitutions that assume the conclusion.

Use `assets/verify_formulas.py.template` as a pattern. Keep actual formulas in the manuscript repository.

## Numerical checks

- Recompute from fresh inputs rather than plot caches.
- Record parameters, units, algorithm, solver tolerances, expected value, and acceptance tolerance.
- Use both absolute and relative tolerance where scale can vary.
- Separate physics parameters from display-only settings.
- Import numerical modules only when they have controlled import behavior; otherwise expose a library function or CLI.
- Make generated files deterministic and document their relationship to manuscript figures.

Use `assets/verify_numerics.py.template` as a pattern.

## Orchestration

Store verification commands as arrays in `manuscript-project.toml`:

```toml
[verification]
default = [
  ["python3", "verification/verify_all.py"],
]
online = [
  ["python3", "verification/verify_bibliography.py", "--online"],
]
inputs = ["paper/main.tex", "paper/ref.bib"]
packages = ["sympy", "numpy", "scipy"]
provenance_python = ".venv/bin/python"
seeds = { numerical_scan = 12345 }
cache_policy = "bypass caches for quoted-value verification"
```

Keep declared network checks out of the default group. The name `default` is a selection convention, not a network boundary. Inspect repository-controlled commands before executing them.

Run with `--report verification/report.json --junit verification/junit.xml` to persist the Git state, configuration hash, input hashes, selected package versions, seeds, cache policy, bounded stdout/stderr, command durations, and exit codes. The runner passes a filtered environment by default; this is not a sandbox or network isolation. Use `--inherit-env` only after inspecting why a check requires additional variables. Child output is captured in reports and is not automatically secret-redacted.

## Failure contract

- Return zero only when all selected assertions pass.
- Return nonzero on failed identities, tolerance violations, missing dependencies, or incomplete required inputs.
- Distinguish scientific assertion failures from operational failures.
- Print enough context to reproduce the failure without exposing secrets.
