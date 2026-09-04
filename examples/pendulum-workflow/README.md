# Finite-amplitude pendulum workflow

This reproducible example takes a result through derive → compute → verify → edit.

1. Derive: `Use $derive-scientific-results to derive the finite-amplitude pendulum period through fourth order in theta_0, including assumptions and an applicability test. Update derivation.md only.` Expected change: a checked analytic derivation in `derivation.md`.
2. Compute: `Use $implement-scientific-computations to implement a standard-library numerical quadrature for the exact pendulum period. Write verification/period-data.json and do not edit the manuscript.` Expected change: reproducible numerical data from `compute_period.py`.
3. Verify: `Use $verify-manuscript-results to independently verify the expansion against the numerical result, with explicit tolerances, JSON, and JUnit output.` Expected change: `verification/report.json` and `verification/junit.xml` from `verify_period.py`.
4. Edit: `Use $edit-scientific-manuscripts to write only the verified result, numerical error, and applicability limit into manuscript/main.tex; preserve every caveat.` Expected change: the result and limitation already illustrated in `manuscript/main.tex`.

Run the committed reference workflow:

```bash
python3 compute_period.py
python3 verify_period.py
latexmk -pdf -cd manuscript/main.tex
```

Acceptance: both Python commands exit zero, `verification/report.json` has `passed: true`, JUnit has no failure/error, and `manuscript/main.pdf` compiles. The tested amplitude is 0.2 rad; the manuscript does not extrapolate the series to large amplitudes.
