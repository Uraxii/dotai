#!/usr/bin/env python3
"""Generate Claude and Codex agent configurations from one manifest."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


__all__ = ["AgentDefinition", "load_definitions", "main"]

SUPPORTED_TARGETS = frozenset({"claude", "codex"})


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    color: str
    instructions: str
    targets: frozenset[str]
    global_codex_instructions: bool


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_definitions(skill_directory: Path) -> tuple[AgentDefinition, ...]:
    references = skill_directory / "references"
    manifest_path = references / "agent-definitions.toml"
    with manifest_path.open("rb") as manifest_file:
        manifest = tomllib.load(manifest_file)
    if manifest.get("schema_version") != 1:
        raise ValueError("agent-definitions.toml must use schema_version = 1")

    definitions = []
    for name, values in manifest["agents"].items():
        targets = frozenset(values["targets"])
        unknown_targets = targets - SUPPORTED_TARGETS
        if unknown_targets:
            joined = ", ".join(sorted(unknown_targets))
            raise ValueError(f"{name} has unsupported targets: {joined}")
        instructions_path = references / values["instructions"]
        definitions.append(
            AgentDefinition(
                name=name,
                description=values["description"],
                color=values["color"],
                instructions=instructions_path.read_text(),
                targets=targets,
                global_codex_instructions=values.get(
                    "global_codex_instructions", False
                ),
            )
        )
    return tuple(definitions)


def render_claude(definition: AgentDefinition) -> str:
    description = json.dumps(definition.description, ensure_ascii=False)
    body = definition.instructions.rstrip()
    return (
        "---\n"
        f"name: {definition.name}\n"
        f"description: {description}\n"
        f"color: {definition.color}\n"
        "---\n\n"
        f"{body}\n"
    )


def render_codex(definition: AgentDefinition) -> str:
    if "'''" in definition.instructions:
        raise ValueError(f"{definition.name} instructions contain three apostrophes")
    name = json.dumps(definition.name, ensure_ascii=False)
    description = json.dumps(definition.description, ensure_ascii=False)
    body = definition.instructions.rstrip()
    return (
        f"name = {name}\n"
        f"description = {description}\n"
        "developer_instructions = '''\n"
        f"{body}\n"
        "'''\n"
    )


def expected_files(skill_directory: Path) -> dict[Path, str]:
    plugin_root = skill_directory.parents[1]
    expected = {}
    for definition in load_definitions(skill_directory):
        if "claude" in definition.targets:
            expected[plugin_root / "agents" / f"{definition.name}.md"] = (
                render_claude(definition)
            )
        if "codex" in definition.targets:
            output_dir = skill_directory / "assets" / "codex-agents"
            expected[output_dir / f"{definition.name}.toml"] = render_codex(
                definition
            )
    return expected


def check_files(expected: dict[Path, str]) -> tuple[Path, ...]:
    return tuple(
        path
        for path, content in expected.items()
        if not path.exists() or path.read_text() != content
    )


def write_files(expected: dict[Path, str]) -> None:
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text() != content:
            path.write_text(content)


def parse_args(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when a generated file is missing or stale.",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    expected = expected_files(skill_root())
    if not options.check:
        write_files(expected)
        return 0

    stale_files = check_files(expected)
    for path in stale_files:
        print(f"stale generated agent config: {path}", file=sys.stderr)
    return 1 if stale_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
