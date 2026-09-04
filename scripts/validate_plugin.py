#!/usr/bin/env python3
"""Validate plugin metadata, skill structure, agent YAML, and resource paths."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def validate_plugin(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / ".codex-plugin/plugin.json"
    schema_path = root / "schemas/plugin.schema.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
            location = ".".join(map(str, error.path)) or "manifest"
            errors.append(f"{location}: {error.message}")
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        return [f"manifest/schema load failed: {exc}"]

    skills_raw = manifest.get("skills", "")
    skills_dir = (root / skills_raw).resolve(strict=False)
    try:
        skills_dir.relative_to(root.resolve())
    except ValueError:
        errors.append(f"skills path escapes repository: {skills_raw}")
        return errors
    if not skills_dir.is_dir():
        errors.append(f"skills directory does not exist: {skills_raw}")
        return errors

    marketplace_path = root / ".agents/plugins/marketplace.json"
    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        if set(marketplace) - {"name", "interface", "plugins"}:
            raise ValueError("unknown top-level marketplace fields")
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or len(plugins) != 1:
            raise ValueError("marketplace must contain exactly the root plugin")
        plugin = plugins[0]
        if plugin.get("name") != manifest.get("name"):
            raise ValueError("marketplace plugin name differs from manifest")
        source = plugin.get("source")
        if source != {"source": "local", "path": "./"}:
            raise ValueError("marketplace source must point to the repository root")
        policy = plugin.get("policy", {})
        if policy.get("installation") not in {"AVAILABLE", "INSTALLED_BY_DEFAULT"}:
            raise ValueError("invalid marketplace installation policy")
        if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
            raise ValueError("invalid marketplace authentication policy")
    except (OSError, json.JSONDecodeError, ValueError, AttributeError) as exc:
        errors.append(f"{marketplace_path.relative_to(root)}: {exc}")

    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_path = skill_dir / "SKILL.md"
        agent_path = skill_dir / "agents/openai.yaml"
        try:
            text = skill_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{skill_path.relative_to(root)}: {exc}")
            continue
        match = FRONTMATTER_RE.match(text)
        if not match:
            errors.append(f"{skill_path.relative_to(root)}: missing YAML frontmatter")
        else:
            try:
                frontmatter = yaml.safe_load(match.group(1))
            except yaml.YAMLError as exc:
                errors.append(f"{skill_path.relative_to(root)}: invalid frontmatter: {exc}")
            else:
                if not isinstance(frontmatter, dict):
                    errors.append(f"{skill_path.relative_to(root)}: frontmatter is not a mapping")
                else:
                    if set(frontmatter) != {"name", "description"}:
                        errors.append(f"{skill_path.relative_to(root)}: frontmatter must contain only name and description")
                    if frontmatter.get("name") != skill_dir.name:
                        errors.append(f"{skill_path.relative_to(root)}: name must match directory")
                    if not isinstance(frontmatter.get("description"), str):
                        errors.append(f"{skill_path.relative_to(root)}: description must be text")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resource = (skill_dir / target).resolve(strict=False)
            try:
                resource.relative_to(skill_dir.resolve())
            except ValueError:
                errors.append(f"{skill_path.relative_to(root)}: linked resource escapes skill: {raw_target}")
                continue
            if not resource.exists():
                errors.append(f"{skill_path.relative_to(root)}: linked resource missing: {raw_target}")
        try:
            agent = yaml.safe_load(agent_path.read_text(encoding="utf-8"))
            interface = agent.get("interface") if isinstance(agent, dict) else None
            if not isinstance(interface, dict):
                raise ValueError("missing interface mapping")
            required = {"display_name", "short_description", "default_prompt"}
            if not required.issubset(interface):
                raise ValueError("interface is missing required fields")
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{agent_path.relative_to(root)}: {exc}")
        for resource_dir in ("assets", "references", "scripts"):
            candidate = skill_dir / resource_dir
            if candidate.exists() and not any(path.is_file() for path in candidate.rglob("*")):
                errors.append(f"{candidate.relative_to(root)}: resource directory is empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_plugin(args.project_root.resolve())
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print("Plugin manifest and skill structure: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
