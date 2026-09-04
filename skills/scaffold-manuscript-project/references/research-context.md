# Bounded Research Context

The unified scaffold uses this architecture from initialization onward. At first it contains only one project-overview packet and one `open/blocked` result entry. During initialization, split that starter only when the inheritance audit already exposes distinct durable results, stopped branches, or topic-specific evidence routes that would otherwise make the default context unwieldy. Packet names and counts remain project-specific.

## Roles

- `AGENTS.md` routes work and preserves repository-wide invariants; it must not become a numerical-results ledger.
- `SCIENTIFIC_PROGRESS.md` is a compact discovery index of durable results and stop/go decisions; it points to evidence but is not evidence.
- `docs/context/README.md` explains the packet contract and lists available routes.
- `docs/context/*.md`, excluding `README.md`, contains bounded topic packets loaded only when their routing condition matches the task.
- `RESEARCH_PLAN.md` records forward questions, candidate routes, durable decisions, and the next scientific uncertainty; it does not duplicate completed-result detail.
- `RESEARCH_NOTICES.md`, when explicitly enabled, preserves a small human-facing map of consequential developments; it remains navigation rather than evidence and does not duplicate the result index or research plan.
- Calculations, derivations, TeX, configurations, verification, and primary sources remain authoritative.

## Evidence levels

- `inherited`: established in an antecedent source and reused within its assumptions.
- `verified`: reproduced by a registered project-local check for the named object.
- `conditional`: a controlled decision inside declared priors, grids, approximations, or stress assumptions.
- `diagnostic`: useful for mechanism or engineering but not promotable as a physical result.
- `open/blocked`: required evidence or an admission condition is missing.
- `superseded`: retained only to prevent reuse or repetition.

Do not promote a result merely because a script ran, a plot looks plausible, a manuscript compiles, or an implementation test passes. Promotion requires the source, assumptions, object being verified, and verifier to agree.

## Two-hop rule

1. Search `SCIENTIFIC_PROGRESS.md` by concept, result key, calculation, or intended claim.
2. Load one matching topic packet.
3. Inspect one linked source, derivation, calculation, configuration, or verifier.
4. Load a second packet only when the first exposes a genuine dependency.

Do not make every packet part of default context. `AGENTS.md` and `SCIENTIFIC_PROGRESS.md` are the standard cold-start pair; the research plan and manuscript context are task-specific.

Use `$orient-scientific-project` to turn this bounded evidence route into an explanation or an agent task brief. An enabled notice file may help choose the route, but it never replaces the packet or linked authority.

Keep every retained result key directly searchable in `SCIENTIFIC_PROGRESS.md`. When one packet accumulates distinct `Load when` conditions or independent evidence boundaries, split it horizontally and route the affected keys directly to the new packets. Compact the discovery catalogue and refine packet boundaries before raising context budgets; do not introduce nested result indexes by default.

## Topic-packet contract

Each packet contains these headings in this order:

1. `## Load when`
2. `## Established results`
3. `## Limits and non-claims`
4. `## Rejected or superseded routes`
5. `## Evidence routes`
6. `## Active gap`

The packet records routing conditions, evidence status, validity limits, non-claims, stopped routes, and the smallest active gap. Exact values belong in active calculations and verifiers. A packet may link a citation-plan row, but primary literature and verified source metadata remain authoritative.

## Stop decisions

Preserve a negative or stopped route only when its scope and rationale will prevent invalid reuse or costly repetition. State what new source, observable, physical branch, assumption failure, or algorithm could reopen it. Do not relabel a stopped route as positive progress without new evidence that addresses its stated reason.

## Promotion and maintenance

Update the matching packet when a durable result, limitation, evidence route, or active gap changes. Update the discovery index only when result discovery or a stop/go decision changes. Update the research plan only when forward priorities, candidate ordering, hypotheses, or durable decisions change. Provisional manuscript prose may precede verification when its status is explicit; only established claims require the corresponding evidence boundary.

The starter `initialization` entry stays `open/blocked` until a project-specific result has an authoritative source and its claimed status is justified. Remove generic prompts when orientation is filled, but do not manufacture evidence to make the scaffold look complete.
