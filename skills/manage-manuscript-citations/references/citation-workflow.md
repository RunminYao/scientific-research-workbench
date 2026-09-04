# Scientific Citation Workflow

## Source selection

1. State the exact claim needing support.
2. Decide whether it requires an original result, standard method, review, dataset, software citation, or contextual comparison.
3. Prefer exact DOI or arXiv identifiers. For physics, HEP, and astrophysics, prefer authoritative INSPIRE BibTeX when available.
4. Check that the cited source actually supports the nearby claim at the stated scope.
5. Distinguish attribution from background reading.

## Entry handling

- Preserve the repository's citation-key convention.
- Verify title, authors, DOI, arXiv identifier, year, and publication metadata.
- Preview bundled INSPIRE BibTeX before applying it; use exact identifiers when available and explicitly choose title-search candidates.
- Do not replace a valid entry solely because punctuation or title capitalization differs.
- Treat title-only fuzzy matches as review candidates, never automatic identity proof.
- Keep duplicate DOI and arXiv identifiers out of the bibliography.

## Citation placement

- Attach a citation to the smallest complete claim it supports.
- Keep citations through sentence moves and paragraph restructuring.
- Avoid placing one citation after several unrelated claims.
- Preserve caveats when a source applies only in a restricted regime.

## Citation ledger

Use a ledger for selection rationale, not as a copy of BibTeX. Record:

- citation key or proposed identifier;
- supported claim;
- source role;
- manuscript location;
- assumptions and validity conditions required to transfer the result;
- why this source was selected;
- verification actually performed, distinguishing identity checks from full-text claim checks;
- unresolved decisions.

Use `assets/CITATION_PLAN.md.template` when a project needs a new ledger.

## Validation

Run local key and duplicate checks first. Run online identity checks separately because service outages are operational errors, not evidence that an entry is false. Rebuild LaTeX after changes and inspect undefined citations.
