# Scientific Research Workbench

[简体中文](README.zh-CN.md)

[![CI](https://github.com/RunminYao/scientific-research-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RunminYao/scientific-research-workbench/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**An evidence-aware Codex workflow for long-horizon scientific research.**

Scientific Research Workbench is a Codex plugin that keeps scientific questions, assumptions, evidence, derivations, computations, citations, and LaTeX manuscripts aligned across a research project.

```text
Scientific question
    -> Project orientation
    -> Evidence calibration
    -> Literature / derivation / computation
    -> Independent verification
    -> Citation and manuscript consistency
```

## Problems addressed

- Prevent the original scientific target from drifting during long agent-assisted work.
- Keep physical conclusions distinct from mathematical theorems and implementation checks.
- Detect mismatches between derivations and code, and between results and manuscripts, before they become conclusions.
- Make unsupported syntax, incomplete evidence, and provenance gaps visible instead of guessing through them.

> [!IMPORTANT]
> This is a conservative text and structure auditing toolkit. It is **not a LaTeX AST**, a complete TeX macro expander, or a TeX compiler. Unsupported constructs are reported; use a TeX engine as the authority for compilation.

## Requirements and supported surfaces

- Python 3.11, 3.12, or 3.13.
- Codex CLI 0.144.6 or newer.
- Runtime dependency ranges from `requirements.txt`; CI uses the exact versions in `requirements-ci.txt`.
- Ubuntu and macOS are tested. Windows is not currently supported.
- Support is promised for Codex CLI and the latest stable ChatGPT desktop/Codex surfaces. Codex plugins are not currently supported by the IDE extension; see the [official plugin documentation](https://developers.openai.com/codex/plugins).

## Install

Install the tagged release marketplace and plugin:

```bash
codex plugin marketplace add RunminYao/scientific-research-workbench --ref v0.5.0
codex plugin add scientific-research-workbench@scientific-research-workbench
```

For local development, clone the repository, install dependencies in a virtual environment, add the local marketplace, and install the plugin:

```bash
git clone https://github.com/RunminYao/scientific-research-workbench.git
cd scientific-research-workbench
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
codex plugin marketplace add "$PWD"
codex plugin add scientific-research-workbench@scientific-research-workbench
python scripts/self_check.py
```

## One-minute quick start

```bash
cd examples/minimal
latexmk -pdf main.tex
codex 'Use $edit-scientific-manuscripts to review main.tex conservatively; report unsupported syntax and do not invent scientific claims.'
```

The minimal project is in [`examples/minimal`](examples/minimal). A complete derive → compute → verify → edit walkthrough is in [`examples/pendulum-workflow`](examples/pendulum-workflow).

## Orient a complex research project

Recover the current scientific mainline without assuming that the reader has followed every recent derivation or failed route:

```bash
codex 'Use $orient-scientific-project to explain where this project stands, what consequential results I may have missed, and what background I need.'
```

The same skill can give Codex or a subagent a cold-start task brief, check whether local work still affects the project decision, and synthesize a human-facing notice when a project has explicitly opted into `RESEARCH_NOTICES.md`. Notices remain routing aids rather than scientific evidence, and the skill does not require research to pause while a nearby result is being adjudicated.

## Calibrate scientific evidence and route choice

Separate a physical conclusion under stated assumptions from a mathematical theorem and an implementation check before choosing the next research step:

```bash
codex 'Use $calibrate-scientific-evidence to classify this claim, audit whether the route is drifting away from its observable, and choose the smallest decision-changing result.'
```

The skill keeps claim kind independent from evidence status, tests whether a proposed theorem really controls the target observable, and forces a route comparison before a third consecutive same-branch milestone that has produced only representations, proofs, contracts, verifiers, or infrastructure. It ranks alternatives by decision value and total cost, remains read-only by default, and does not create research ledgers.

## Initialize or adopt a manuscript project

Ask Codex to inspect the repository and preview the appropriate scaffold before writing anything:

```bash
codex 'Use $scaffold-manuscript-project to inspect this repository and preview initialization or adoption of a scientific research and manuscript workspace. Do not apply changes until I approve the preview.'
```

To run the preview directly, use the Python CLI. For an existing manuscript:

```bash
python skills/scaffold-manuscript-project/scripts/scaffold_project.py \
  --project-root /path/to/project \
  --root-tex paper/main.tex
# repeat with --apply after reviewing every proposed file and command
```

For an empty repository, omit `--root-tex` so the scaffold can create the sectioned manuscript:

```bash
python skills/scaffold-manuscript-project/scripts/scaffold_project.py \
  --project-root /path/to/project \
  --profile generic
```

Generated repository guidance configures `$orient-scientific-project` by default. To explicitly enable its optional human-facing attention log, add `--with-research-notices`; without that flag the scaffold does not create `RESEARCH_NOTICES.md`. Adoption recognizes and preserves an existing notice file.

The default scaffold connects:

- cold-start guidance with project orientation, a research plan, a bounded result index, topic packets, and citation rationale;
- the active TeX include graph, bibliography, and manuscript context;
- derivation notes, the canonical `calculations/{core,models,workflows,cli}` promotion path, and scientific configuration boundaries;
- layered requirement contracts, an ignored repository-local `env/`, generated-output isolation, a project manifest, and executable structural verification.

On a fresh `--apply`, the scaffold creates `env/` offline with the interpreter running the command. It does not install packages or upgrade pip. Use `--no-bootstrap-environment` only when another tool owns environment creation. Adoption preserves existing environment schemes by default and routes newly generated commands through a manifest-declared or unambiguous local interpreter when one exists.

For an established repository, add `--adopt`. Adoption preserves every existing file and manifest, reports missing orientation routes, and creates only absent paths. The legacy `--mature-research` and `--with-calculation-layout` flags remain accepted compatibility aliases; the result index, topic packet, and calculation layout are now part of the unified default.

An empty generic project receives a domain-neutral sectioned manuscript. Select `--profile hep-astrophysics` or `--profile axion-phenomenology` when an explicit domain convention contract is useful. Generated prompts never establish project-specific claims: fill scientific orientation from active sources, write `Not established` where evidence is absent, and run the generated structural verifier through the repository environment before relying on its routing.

## Verification execution and security boundary

Preview registered commands first:

```bash
python skills/verify-manuscript-results/scripts/run_verification.py --project-root examples/pendulum-workflow
```

> [!WARNING]
> `--execute` executes arbitrary programs controlled by the current repository. It is equivalent to running repository code. Review the repository and the preview before using it.

The runner's default environment mode only filters inherited environment variables through a whitelist. It is **not** a sandbox, container, permission boundary, or network isolation mechanism. `--inherit-env` exposes more host state and is higher risk. Process groups are terminated on timeout, but descendants that daemonize or create a new session may escape. Reports contain bounded stdout/stderr, and subprocess output is not automatically secret-redacted; treat JSON and JUnit reports as potentially sensitive.

Execute the pendulum checks and write stable JSON/JUnit reports:

```bash
python skills/verify-manuscript-results/scripts/run_verification.py \
  --project-root examples/pendulum-workflow --execute \
  --report verification/runner-report.json \
  --junit verification/runner-junit.xml
```

`[verification].default` means the normal command set. It does not mean offline and provides no network isolation. The removed `[verification].offline` key is rejected with a migration message.

## Audits

Preview authoritative INSPIRE BibTeX for a physics, HEP, or astrophysics reference before writing it:

```bash
python skills/manage-manuscript-citations/scripts/fetch_inspire_bibtex.py \
  --arxiv 1207.7214 --bib paper/references.bib
# review the record, key, and duplicate checks; then repeat with --apply
```

Bibliography auditing uses Pybtex and accepts multiple resources:

```bash
python skills/manage-manuscript-citations/scripts/audit_bibliography.py \
  --root-tex paper/main.tex --bib paper/references.bib --bib shared/library.bib --strict
```

Notation auditing reports `literal` and `macro-generated-possibility` occurrences separately, and distinguishes `explicit-definition`, `heuristic-candidate`, and `none` evidence. Dynamic includes, include cycles, repeated canonical include paths, include chains deeper than 256 files, parameterized macros, `\csname`, `\edef`/`\xdef`, catcode changes, and other unsupported syntax make JSON reports incomplete and fail `--strict`; each canonical TeX file is scanned at most once.

## Profiles and optional adapters

Preview before applying a domain profile or adapter:

```bash
python skills/scaffold-manuscript-project/scripts/scaffold_project.py \
  --project-root /path/to/project \
  --profile axion-phenomenology \
  --adapter latexmk --adapter sympy
# repeat with --apply after review
```

Available profiles are `generic`, `hep-astrophysics`, and `axion-phenomenology`. The axion profile records project-selected particle, cosmology, halo, apparatus, statistical, coherence, and validity conventions without supplying project-specific numerical conclusions.

The isolated `latexmk` adapter is part of the unified default; explicitly selecting it again is harmless. Add `jupyter`, `sympy`, `mathematica`, or `slurm` only when needed. Adapters generate files and dependency diagnostics only. Nothing is installed or submitted; SLURM submission is always manual.

## Development and release checks

```bash
python -m unittest discover -s tests -v
python -m compileall -q skills shared scripts tests examples
python scripts/check_templates.py
python scripts/validate_plugin.py
python scripts/self_check.py
```

Version policy and migration notes are in [`CHANGELOG.md`](CHANGELOG.md). The project is licensed under Apache-2.0; third-party fixture notices are recorded separately.
