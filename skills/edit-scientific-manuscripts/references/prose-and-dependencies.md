# Prose, Notation, and Dependency Checks

Use this reference for sentence style, terminology, transitions, technical hierarchy, symbol definitions, and cross-section dependency order.

## Contents

- Technical hierarchy
- Definition and dependency order
- Reproducible first-use procedure
- Inflated or generic academic phrasing
- Weak transitions
- Local grammar and polish
- Dependency and prose audit

## Technical hierarchy

Problem: Related objects are used interchangeably even though they belong to different levels of description.

Common examples include:

- coupling constants, shell-matrix elements, and action-normalized envelope couplings;
- modes, branches, eigenvectors, amplitudes, and envelopes;
- full Fourier-rung coefficients and projected resonant coordinates.

Operations:

- Define the hierarchy once in a compact paragraph.
- Use one term consistently for each level.
- Avoid redefining the hierarchy later.
- Flag an ambiguity when the intended object cannot be inferred safely.

## Definition and dependency order

Problem: A symbol, concept, approximation, distinction, or result is used before the manuscript supplies enough information to interpret it.

Check for:

- symbols first appearing in equations, tables, or captions before definition;
- acronyms, branch labels, approximations, or distinctions explained only later;
- paragraphs depending on unstated conventions or later results;
- forward references that omit the minimum local definition;
- moved material that leaves definitions after their first operative use.

Apply these rules:

- Define each item at or before its first operative use.
- If the derivation belongs later, give a minimal operational definition locally and point forward for details.
- Allow an introduction to preview a named concept, but do not let a derivation rely on undefined notation or properties.
- Trace dependencies across included sections, appendices, figures, captions, and tables.

## Reproducible first-use procedure

Use this procedure whenever symbols, terminology, definitions, or section order change.

1. Recover manuscript order from the root TeX file and its `\input` or `\include` chain.
2. List every affected symbol, acronym, concept, approximation, and named distinction.
3. Run the bundled deterministic audit for affected symbols:

   ```bash
   python3 <skill-dir>/scripts/audit_notation.py \
     --root <root-tex-file> \
     --symbol '<token>'
   ```

   Use a JSON specification when canonical forms, variants, or definition patterns are known. The report recovers include order, records literal occurrences, identifies definition candidates, and flags use before a candidate definition. Use `rg -n -F '<token>'` as a fallback or cross-check when the TeX include graph cannot be resolved.
4. Inspect prose, displayed equations, tables, captions, and appendix occurrences in manuscript order.
5. Record a compact dependency ledger:

   | Item | Kind | Definition | First operative use | Required dependency | Status |
   |---|---|---|---|---|---|

6. Classify an occurrence as a preview, definition, or operative use. A preview may precede the full definition; an operative use may not depend on unexplained notation or properties.
7. Move or add the smallest sufficient definition. Do not duplicate a full derivation merely to remove a forward reference.
8. Rerun the audit after editing and verify that every ledger item passes.

When the search scope is uncertain, search the current manuscript before older drafts or alternate directories.

## Inflated or generic academic phrasing

Replace broad rhetoric with the concrete scientific consequence.

Avoid relying on phrases such as:

- “plays a crucial role”;
- “provides deep insight”;
- “reveals rich dynamics”;
- “has significant implications”;
- “it is important to note”;
- “sheds light on”;
- “paves the way”.

Prefer:

> The reduced normal form separates bounded conversion from exponential growth by the signature of the two crossing modes.

to a generic claim that the framework provides insight.

## Weak transitions

Problem: A transition repeats the previous point instead of showing causality, contrast, or dependency.

Replace generic transitions with the next concrete claim.

Prefer:

> Consequently, the same local coupling produces a temporal instability in one reduction but a spatial stop band in another.

to a sentence stating only that the distinction is important.

## Local grammar and polish

After structural issues are resolved, check:

- subject-verb agreement;
- singular and plural consistency;
- punctuation after displayed equations;
- repeated words;
- awkward noun strings;
- overlong sentences;
- ambiguous pronouns;
- inconsistent terminology;
- incorrect technical pluralization.

Preserve the author's technical voice and density unless the user requests a different audience or style.

## Dependency and prose audit

Verify that:

- every affected item is defined before its first operative use;
- forward references provide the minimum local definition;
- technical levels are named consistently;
- transitions advance the argument;
- generic rhetoric has been replaced by concrete claims;
- equations, labels, citations, notation, and scope conditions are preserved;
- ambiguous scientific points are reported rather than silently rewritten.
