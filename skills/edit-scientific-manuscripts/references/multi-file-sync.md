# Multi-file Synchronization

## Authority

Treat TeX, bibliography, numerical source, and verification assertions as primary. Treat `AGENTS.md`, manuscript indexes, citation plans, captions, and workflow descriptions as dependent artifacts. Update descriptions after source changes; never alter science merely to make a stale description true.

## Dependency classes

- Manuscript structure: root TeX, include lists, section names, appendix order, active draft paths.
- Scientific dependencies: definitions, equations, claims, caveats, tables, and appendix derivations.
- Numerical dependencies: parameters, algorithms, cache fingerprints, generated filenames, plotted quantities, and quoted values.
- Bibliographic dependencies: BibTeX entries, citation keys, claim placement, and citation rationale.
- Workflow dependencies: build commands, verification commands, required packages, and output locations.

## Procedure

1. Inspect the current Git diff and untracked files.
2. Run `audit_artifact_sync.py` when `manuscript-project.toml` exists.
3. Read each changed source and the companion context before deciding whether synchronization is needed.
4. Update only descriptions whose facts changed.
5. Keep a focused diff. Do not touch companion files solely to silence an optional review rule.
6. Run the relevant build and executable checks.

## Rule semantics

Each `[[sync.rules]]` entry contains:

- `sources`: changed-file glob patterns;
- `companions`: relative paths to review;
- `reason`: the factual dependency;
- `required`: whether an unchanged companion is a mechanical failure.
- `anchors`: optional companion-to-heading or token mappings that must remain present.

Use `required = false` for semantic review prompts. Use `required = true` only when the repository defines a deterministic synchronization contract.

Use `--base <revision>` to audit a branch or multi-commit change against a stable Git revision. Anchor checks verify that a companion still exposes the expected synchronization location; they do not establish that its prose is semantically current.
