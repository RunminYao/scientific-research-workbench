# Restartable Scientific Computations

Use this pattern only when work is long-running, decomposes into independent nodes or deterministic chunks, and interruption recovery materially saves computation. Keep ordinary tests and short calculations in their native workflow.

## Immutable input binding

Build one canonical JSON mapping containing every scientific input and material numerical control. Hash its deterministic serialization and bind all checkpoints to that fingerprint. Refuse resume when the mapping changes; a filename, timestamp, or partial parameter subset is not sufficient identity.

Use `assets/node_checkpoint_store.py.template` as a project-local starting point when no equivalent checkpoint layer exists. Preserve its atomic metadata-last array commit, payload hashes, dtype and shape checks, and changed-input rejection.

## Response-blind work plan

Declare the complete node set and deterministic partitions before evaluating the response. Use `assets/chunk_plan.py.template` when two nested grids need stable paired labels. Never refine, omit, or prioritize nodes because preliminary responses look interesting unless the scientific method explicitly defines and verifies an adaptive algorithm.

## Execution and aggregation

- Limit nested numerical-library threads before spawning process workers.
- Stream output or emit periodic heartbeats when an external supervisor may treat silence as failure.
- Write scratch products only under a declared recoverable workspace.
- Persist node-level states or observables with their original global weights and identities.
- Construct a partial-completion report, but never present a partial grid as the final observable.
- Aggregate only after exact-once coverage of the declared complete node set; do not renormalize weights inside chunks.

## Evidence boundary

A valid resume proves continuity of the declared computation, not convergence or physical interpretation. A complete aggregate remains diagnostic until its observable-level error budget and formal verifier pass. Generated checkpoints are never independent verification inputs for values they helped produce.
