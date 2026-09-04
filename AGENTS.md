# Repository Guidelines

## Project Structure & Module Organization

This repository packages reusable Codex workflows for scientific research and manuscript work. Plugin metadata lives in `.codex-plugin/plugin.json`. Each feature is isolated under `skills/<skill-name>/`: `SKILL.md` defines the workflow, `agents/openai.yaml` supplies its interface, and optional `scripts/`, `references/`, or `assets/` hold executable helpers, supporting guidance, and generated-file templates. Regression coverage is grouped by behavior under `tests/`. Keep new resources beside the skill that owns them; do not create a general-purpose module unless multiple skills truly share it.

## Build, Test, and Development Commands

There is no packaging or compile build step. Use Python 3 from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills shared scripts tests examples
```

The first command runs the complete behavioral suite. The second catches syntax errors in Python scripts and templates that use a `.py` suffix. For scaffold-style commands, run the documented preview first, then repeat with `--apply`; tests depend on preview mode remaining read-only.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` for functions and variables, `PascalCase` for `unittest.TestCase` classes, type hints, `pathlib.Path`, and explicit UTF-8 file handling. Follow the existing standard-library-first Python style; no formatter or linter is configured. Skill directories use lowercase kebab-case, and their YAML `name` must match the directory. Preserve the exact `SKILL.md` frontmatter keys `name` and `description`. Name templates with `.template` and tests with `test_<behavior>`.

## Testing Guidelines

Add focused `unittest` cases to the nearest relevant `tests/test_*.py` module. Exercise CLI behavior through temporary directories, assert return codes and file contents, and cover both preview and mutation paths. Mock network access so the default suite remains deterministic and offline. No numeric coverage threshold is enforced; every behavior change should have a regression test.

## Commit & Pull Request Guidelines

Use short, imperative commit subjects such as `Add bibliography crossref fallback`, and keep each commit scoped to one workflow. Pull requests should explain the user-visible change, list affected skills, include the commands run, and call out generated-template or plugin-metadata changes. Link relevant issues; include screenshots only for interface metadata changes where visual review helps.

## Security & Configuration

Never commit credentials, live API responses, caches, or generated manuscript artifacts. Keep online verification explicit and preserve existing secret-redaction behavior in command previews and provenance output.
