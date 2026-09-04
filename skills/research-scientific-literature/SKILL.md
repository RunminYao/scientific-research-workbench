---
name: research-scientific-literature
description: Research a focused scientific question using primary literature, authoritative data, and precise source attribution. Use when Codex needs to establish what is known, compare methods or assumptions across papers, verify a literature-dependent statement, locate an original result, or assess whether a proposed research direction is novel or already constrained.
---

# Research Scientific Literature

Answer the research question from evidence rather than producing a catalogue of paper summaries.

## Scope the search

1. Read the relevant project guidance, research notes, manuscript passage, or citation plan when present.
2. Translate the request into concrete claims or comparisons that sources must resolve.
3. Record material scope choices in the response: subject, regime, date range, and excluded adjacent topics. Ask only when a missing choice would substantially change the result.

## Gather evidence

1. Search exact arXiv IDs, DOIs, titles, or authors before using broad queries when identifiers are available.
2. Prefer original papers, official experiment releases, and authoritative databases. Use reviews to navigate the field, not to replace original-result attribution.
3. Read the relevant equations, methods, assumptions, data definitions, and caveats. Do not infer a paper's result from a search snippet or abstract when the question depends on details.
4. Check whether apparently conflicting papers use different conventions, observables, evolution variables, parameter priors, or validity domains.
5. Distinguish explicitly:
   - what a source states or demonstrates;
   - what follows by a transparent comparison;
   - what remains an inference or open question.

## Synthesize

1. Organize sources by their role in answering the question, not chronologically by default.
2. Attach citations to the smallest supported claim.
3. Identify the result most directly relevant to the user's model and the assumptions required to transfer it.
4. State evidence gaps, unresolved disagreements, and the next source or calculation needed.

## Hand off candidate citations

When the task includes preserving sources for likely manuscript use:

1. Update the existing `CITATION_PLAN.md` with only the sources that support a concrete prospective claim. Record the exact identifier or proposed key, supported claim, source role, likely manuscript location, selection rationale, verification performed, and open decision.
2. Mark uncertain identity, publication metadata, claim scope, or citation placement explicitly. A literature-search result is a candidate until those fields are resolved.
3. Preserve negative selection decisions only when they will prevent a repeated mistake, such as a scope mismatch or superseded result.
4. Hand the candidate rows to `$manage-manuscript-citations` when the user wants verified BibTeX, final citation placement, duplicate checks, or bibliography integration.

If no citation plan exists, create one only when the user asks to retain the survey or the task explicitly includes manuscript citation planning. Use the citation-management skill's template rather than inventing a new format.

## Artifact policy

- Default to a cited answer in the conversation.
- Do not create literature databases, evidence registries, or new planning documents unless asked.
- When a result would materially change how a future user or agent understands the research mainline, use `$orient-scientific-project` to preserve or update a human-facing notice if the project has opted into one. Do not interrupt authorized nearby adjudication solely to record it.
- A citation-plan handoff may contain source rationale and claim support, but it must not silently add unverified BibTeX or citations to the manuscript.
- Keep online service failures separate from negative scientific evidence.

## Report

- Lead with the evidence-backed answer.
- List the few sources that materially support it and explain their roles.
- Label extrapolations to the user's problem.
- Report candidate citation-plan changes separately from verified bibliography changes.
- Report search or access limitations that affect confidence.
