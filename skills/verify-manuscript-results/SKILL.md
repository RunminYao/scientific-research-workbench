---
name: verify-manuscript-results
description: Design, scaffold, and run reproducible symbolic and numerical checks for scientific manuscript results. Use when Codex needs to formalize algebraic identities, compare analytic formulas with fresh numerical calculations, validate quoted values and tolerances, connect equations to executable assertions, avoid stale caches, or orchestrate default and network-dependent manuscript verification separately.
---

# Verify Manuscript Results

Read [references/verification-design.md](references/verification-design.md) before adding checks. Read [references/upstream-parity.md](references/upstream-parity.md) when a local implementation copies, wraps, accelerates, or replaces an authoritative scientific source.

## Accept research handoffs

When `$derive-scientific-results` or `$implement-scientific-computations` has produced a candidate check:

- Inspect the derivation, assumptions, expected result, parameters, units, tolerances, inputs, and cache behavior before registering it.
- Check that the assertion is independent enough to detect the suspected error. Refactor or replace a script that merely restates the target expression.
- Keep ordinary implementation tests in their native test suite. Register only checks that substantiate a manuscript equation, value, curve, or stated approximation domain.
- Do not treat the existence or local success of a candidate script as formal verification until it is registered, executed from the declared inputs, and reviewed under this workflow.

## Workflow

1. Map each manuscript claim to one of:
   - exact symbolic identity;
   - numerical value or curve;
   - approximation-domain statement;
   - physical interpretation.
2. Automate the first two. Keep assumptions and interpretations as explicit human-review items.
3. Scaffold project-local checks when needed:

   ```bash
   python3 <skill-dir>/scripts/scaffold_verification.py \
     --project-root <repo>
   ```

   Review the preview, then rerun with `--apply`.
4. Implement symbolic checks as residuals that simplify to zero.
5. Implement numerical checks from fresh calculations with named absolute and relative tolerances. Bypass plot caches when verifying quoted values.
6. Register commands in `manuscript-project.toml`.
7. Inspect configured commands before execution:

   ```bash
   python3 <skill-dir>/scripts/run_verification.py \
     --project-root <repo>
   ```

8. Execute default checks explicitly after reviewing every configured command:

   ```bash
   python3 <skill-dir>/scripts/run_verification.py \
     --project-root <repo> \
     --execute
   ```

   `--execute` runs arbitrary repository-controlled code. It is not a sandbox and does not provide network isolation. For a reproducible record, add `--report <report.json> --junit <junit.xml>`. Declare input files, package names, seeds, and cache policy in `manuscript-project.toml`.

9. Add `--online` only for declared network-dependent checks. The runner passes only an environment-variable allowlist by default; this is not isolation. Inspect the repository before opting into the higher-risk `--inherit-env` mode.
10. When a bounded result index exists, update the matching topic packet only after the registered command has run successfully from declared inputs. Update the discovery index only when the result's discoverability or a stop/go decision changes; state exactly which object moved evidence level.
11. When a result would materially change how a future user or agent understands the research mainline, use `$orient-scientific-project` to preserve or update a human-facing notice if the project has opted into one. Do not interrupt authorized nearby adjudication solely to record it.

## Validation contract

- Candidate checks from upstream skills receive no automatic trust.
- A failed assertion must return nonzero and identify the residual or tolerance.
- A symbolic pass does not validate approximation domains.
- A numerical agreement does not prove uniqueness or physical interpretation.
- Scope freshness to the named claim and its declared inputs, code, dependencies, and cache policy. Recompute the claim-bearing object from fresh inputs, but do not rerun unrelated expensive workflows merely because a commit, claim, or scoped release is new; use a full cache-bypass audit only when explicitly requested or when dependency invalidation requires it.
- Keep domain formulas and expected values in the manuscript repository, never in this reusable plugin.
