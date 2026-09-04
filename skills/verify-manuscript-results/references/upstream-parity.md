# Upstream Scientific Source Parity

Use this workflow when a project copies, wraps, accelerates, or replaces an authoritative scientific implementation from another repository.

## Identity and authority

- Keep the antecedent source read-only when possible.
- Record the exact source path, revision or release identity, and SHA-256 of the file actually executed.
- Mark local snapshots as convenience copies, not new authorities.
- Inspect license and redistribution conditions before copying source into the project or plugin.

## Behavioral parity

Source identity is necessary but insufficient. Compare the upstream and local implementations in the same units, basis, initial state, ordering convention, and numerical controls. Include one exact or zero-coupling limit, one nontrivial benchmark, and one failure or out-of-domain control.

Target parity at the transfer, state, observable, or output object that the replacement claims to supply. Agreement in a derived scalar does not establish matrix or history parity when downstream consumers require the latter.

## Change handling

Fail closed when the pinned source hash changes. Inspect the upstream diff, rerun behavioral parity, and update the recorded hash only after the new source and its assumptions are accepted. Do not weaken tolerances merely to accommodate an unexplained upstream or accelerator difference.

Register the parity command in the default verification group when it is required for manuscript claims. Keep optional workspace-presence checks separate when the antecedent repository is not portable.
