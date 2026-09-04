---
name: manage-manuscript-citations
description: Plan, fetch, add, audit, and maintain citations and BibTeX for scientific LaTeX manuscripts. Use when Codex needs authoritative INSPIRE BibTeX for physics, HEP, or astrophysics; citation-key coverage; duplicate DOI or arXiv checks; uncited-entry review; source identity and metadata verification; claim-to-source rationale; citation placement; or a portable citation plan. Prefer exact INSPIRE, arXiv, or DOI identifiers and keep network verification explicit.
---

# Manage Manuscript Citations

Read [references/citation-workflow.md](references/citation-workflow.md) before adding or substantially reorganizing references.

## Accept research handoffs

When `$research-scientific-literature` has added candidate rows to `CITATION_PLAN.md`:

- Preserve the supported-claim rationale and unresolved scope decisions.
- Treat proposed keys, metadata, and placement as unverified until checked in this workflow.
- Reopen the primary source when claim support depends on equations, assumptions, or a restricted validity domain; do not validate from the candidate summary alone.
- Promote only the selected, verified candidates into BibTeX and manuscript citations. Leave deferred candidates in the plan with their reason rather than forcing coverage.

## Workflow

1. Locate the active root TeX file and bibliography. Exclude historical drafts unless explicitly in scope.
2. When a citation plan is needed and none exists, preview its standard template before applying:

   ```bash
   python3 <skill-dir>/scripts/init_citation_plan.py \
     --project-root <repo>
   ```

   Review the preview, then rerun with `--apply`. Preserve an existing plan; do not use `--force` merely to normalize its prose.
3. Audit locally before network access:

   ```bash
   python3 <skill-dir>/scripts/audit_bibliography.py \
     --project-root <repo> \
     --root-tex <main.tex> \
     --bib <references.bib>
   ```

   Repeat `--bib` for every active BibLaTeX resource. The audit uses Pybtex, checks duplicate keys/DOIs/arXiv IDs across files, and excludes non-direct `xdata`/`set` entries from uncited warnings. Add `--strict` when unsupported LaTeX syntax must make the audit fail rather than remain incomplete.

4. For a physics, HEP, or astrophysics entry, preview authoritative INSPIRE BibTeX by exact identifier:

   ```bash
   python3 <skill-dir>/scripts/fetch_inspire_bibtex.py \
     --arxiv <arXiv-id> \
     --bib <references.bib>
   ```

   Use `--doi` when that is the exact identifier. For title fallback, add `--title`, optionally `--author`, inspect the candidates, and rerun with an explicit `--choose`. Use `--key` when the INSPIRE key does not match the repository convention. After reviewing the preview, add `--apply`; never treat a title match alone as identity proof.
5. Confirm title, authors, identifiers, publication status, and the claim the source supports.
6. Add the entry using the repository's established key convention. The fetch helper refuses duplicate keys, DOI values, and arXiv identifiers before writing.
7. Place citations directly on supported claims. Do not cite a review as the primary source when the manuscript makes an original-result attribution that requires the original paper.
8. Update the citation ledger only when the project maintains one.
9. Run optional identity verification only when network access is appropriate:

   ```bash
   python3 <skill-dir>/scripts/audit_bibliography.py \
     --root-tex <main.tex> \
     --bib <references.bib> \
     --online \
     --key <citation-key>
   ```

10. Rebuild and inspect undefined citations.

## Boundaries

- A candidate citation-plan row is not a verified bibliography entry.
- Local structural failures and online service failures are distinct.
- Online checks prefer INSPIRE and fall back to exact Crossref or arXiv identities when needed.
- INSPIRE fetching is preview-only unless `--apply` is explicit; title queries require an explicit candidate choice.
- Do not silently rewrite metadata from fuzzy matches.
- Do not send manuscript prose to external services; online checks transmit only identifiers or bibliographic titles.
- Treat uncited entries as review items, not automatic deletion candidates.
