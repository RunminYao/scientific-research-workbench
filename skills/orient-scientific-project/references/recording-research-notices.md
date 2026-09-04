# Record Consequential Research Notices

Use a human-facing notice only when the project has opted in: `RESEARCH_NOTICES.md` already exists, repository guidance explicitly declares notice logging enabled and names that or another location, or the user requests its creation or update. A path mentioned only as an optional convention and marked disabled is not an opt-in. Otherwise return a candidate notice in the response and do not create a new project artifact.

Notices are navigation for later understanding. Primary sources, derivations, calculations, configurations, and verifiers remain authoritative; the compact result index and research plan keep their existing roles.

## Decide what deserves notice

Use one counterfactual test: if this development were omitted, could a future user or cold-start agent misunderstand the mainline, repeat a costly failed route, or miss a result that changes the research decision?

Good candidates include a route-changing result, a non-obvious equivalence or obstruction, a surprising control that survives adjudication, a newly exposed assumption, or a durable stop or reopening condition. Routine test passes, refactors, parameter attempts, command logs, and every intermediate failure do not need notices.

## Let the result mature

- Preserve momentum through the nearest authorized check that can clarify the development's status.
- Merge closely related observations into one account. Revise the same notice when an apparent obstruction becomes a representation issue, a provisional effect fails a control, or a short chain reaches a clearer decision.
- Retain an earlier interpretation only when it explains why the final judgment matters. Do not append a separate notice for every turn in the chain.

## Write for later recovery

Use natural project prose rather than a mandatory schema. Include enough for a reader to recover what happened, why it matters, the present evidence status, the main limitation or non-claim, and the authoritative route. Add prerequisite background or reopening conditions when their omission would cause misunderstanding.

Do not use notices as an unread queue, a task tracker, or a claim registry. Do not force timestamps, severity labels, fixed headings, or one entry per result unless the project already has such a convention.

In multi-agent work, let workers propose candidate notices. Have the primary agent or designated integrator reconcile overlapping accounts and write the project-wide version so parallel local judgments do not race or fragment the mainline.
