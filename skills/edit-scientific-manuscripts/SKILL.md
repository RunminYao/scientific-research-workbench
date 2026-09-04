---
name: edit-scientific-manuscripts
description: Edit, review, and audit scientific manuscripts, academic papers, and LaTeX sources while preserving technical meaning and synchronizing dependent project descriptions. Use for prose revision, section restructuring, notation and first-use checks, cross-section consistency, figure discussion, or edits that may require corresponding updates to scripts, AGENTS.md, manuscript context indexes, citation plans, verification files, and numerical descriptions. Prefer a repository-specific manuscript-editing skill when one is available unless this skill is explicitly invoked.
---

# Edit Scientific Manuscripts

## Preserve technical content

- Preserve claims, equations, labels, citations, numerical values, symbols, commands, assumptions, caveats, and validity domains unless explicitly asked to change them.
- Flag ambiguous scientific meaning instead of guessing.
- Default to minimal, targeted edits.
- Keep the active source authoritative over summaries and guidance files.
- Preserve research status when integrating upstream work: do not present candidate citations as verified sources or exploratory checks as validated results.

## Load relevant guidance

- Read [references/structural-diagnostics.md](references/structural-diagnostics.md) for section structure, paragraph roles, derivation flow, caveats, parallel cases, or figures.
- Read [references/prose-and-dependencies.md](references/prose-and-dependencies.md) for prose, terminology, notation hierarchy, definitions, first use, or cross-section dependencies.
- Read [references/multi-file-sync.md](references/multi-file-sync.md) when an edit can affect project maps, scripts, citations, figures, build commands, or verification.
- When `SCIENTIFIC_PROGRESS.md` exists, locate the claim's result key and load only its matching topic packet before editing. Treat `diagnostic`, `conditional`, `open/blocked`, and `superseded` as manuscript constraints, not prose labels that can be softened away.

## Execute

1. Recover manuscript order from the root TeX include graph and identify the selected passage's role.
2. Read enough surrounding, preceding, and dependent material to recover definitions and assumptions.
3. For notation work, run:

   ```bash
   python3 <skill-dir>/scripts/audit_notation.py \
     --root <root.tex> \
     --symbol '<token>'
   ```

   When the project has a notation table, generate a precise specification instead of auditing broad base symbols:

   ```bash
   python3 <skill-dir>/scripts/generate_notation_spec.py \
     --project-root <repo> \
     --table <notation_table.tex> \
     --preview-path '*/introduction.tex' \
     --output <notation-audit.json>
   ```

   Review the preview, apply it explicitly, then pass the generated file through `--spec`. Treat manually authored `definition_patterns` as trusted local configuration; generate or inspect specifications instead of accepting patterns from untrusted sources. Declare preview paths only for sections that introduce terminology without relying operationally on it. Use `--definition-window 1` only when definitions are line-wrapped.

4. Diagnose structure before sentence-level polish.
5. Check the manuscript context's claim-readiness gate. Require an exact antecedent source for inherited claims and a registered fresh-input verifier for numerical claims; preserve assumptions, non-claims, averaging, and data-interface limitations.
6. Apply the lightest effective operation.
7. Compare the result against the source and audit technical preservation.
8. If `manuscript-project.toml` exists, audit companion files:

   ```bash
   python3 <skill-dir>/scripts/audit_artifact_sync.py \
     --project-root <repo>
   ```

9. Audit labels, references, graphics, and configured script outputs:

   ```bash
   python3 <skill-dir>/scripts/audit_manuscript_links.py \
     --project-root <repo> \
     --root <root.tex> \
     --config manuscript-project.toml
   ```

10. Inspect every reported dependency. Update a companion only when its factual description changed; do not touch it merely to satisfy the checker.
11. Run the narrowest relevant build and verification commands.

## Report

- Identify changed scientific meaning, if any.
- List synchronized companion files and explain why each changed.
- Report unresolved semantic decisions separately from deterministic script findings.
