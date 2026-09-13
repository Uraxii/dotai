#!/usr/bin/env python3
"""Install dotai worker agents and optional Zakia global instructions."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path


__all__ = ["main"]

ZAKIA_START = "<!-- dotai:zakia:start -->"
ZAKIA_END = "<!-- dotai:zakia:end -->"


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_codex_home() -> Path:
    configured_home = os.environ.get("CODEX_HOME")
    return Path(configured_home) if configured_home else Path.home() / ".codex"


def check_generated_files(skill_directory: Path) -> None:
    generator = skill_directory / "scripts" / "generate-agent-configs.py"
    result = subprocess.run(
        [sys.executable, str(generator), "--check"],
        cwd=skill_directory,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def find_collisions(source_dir: Path, destination_dir: Path) -> tuple[Path, ...]:
    collisions = []
    for source in source_dir.glob("*.toml"):
        destination = destination_dir / source.name
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            collisions.append(destination)
    return tuple(collisions)


def install_workers(
    skill_directory: Path, codex_home: Path, force: bool
) -> None:
    source_dir = skill_directory / "assets" / "codex-agents"
    destination_dir = codex_home / "agents"
    collisions = find_collisions(source_dir, destination_dir)
    if collisions and not force:
        joined = "\n".join(str(path) for path in collisions)
        raise FileExistsError(
            "refusing to replace changed personal agent configs:\n" + joined
        )

    destination_dir.mkdir(parents=True, exist_ok=True)
    for source in source_dir.glob("*.toml"):
        destination = destination_dir / source.name
        destination.write_bytes(source.read_bytes())


def zakia_instructions(skill_directory: Path) -> str:
    references = skill_directory / "references"
    manifest_path = references / "agent-definitions.toml"
    with manifest_path.open("rb") as manifest_file:
        agents = tomllib.load(manifest_file)["agents"]
    matches = [
        values
        for values in agents.values()
        if values.get("global_codex_instructions", False)
    ]
    if len(matches) != 1:
        raise ValueError("exactly one global Codex persona must be configured")
    return (references / matches[0]["instructions"]).read_text().rstrip()


def replace_owned_block(existing: str, body: str) -> str:
    block = f"{ZAKIA_START}\n{body}\n{ZAKIA_END}"
    start_count = existing.count(ZAKIA_START)
    end_count = existing.count(ZAKIA_END)
    if start_count == 0 and end_count == 0:
        separator = "\n\n" if existing.rstrip() else ""
        return f"{existing.rstrip()}{separator}{block}\n"
    if start_count != 1 or end_count != 1:
        raise ValueError("global instructions contain malformed Zakia markers")

    start = existing.index(ZAKIA_START)
    end = existing.index(ZAKIA_END) + len(ZAKIA_END)
    return f"{existing[:start]}{block}{existing[end:]}".rstrip() + "\n"


def prepare_zakia_update(
    skill_directory: Path, codex_home: Path
) -> tuple[Path, str, str]:
    destination = codex_home / "AGENTS.md"
    existing = destination.read_text() if destination.exists() else ""
    updated = replace_owned_block(existing, zakia_instructions(skill_directory))
    return destination, existing, updated


def install_zakia(
    codex_home: Path, prepared_update: tuple[Path, str, str]
) -> None:
    destination, existing, updated = prepared_update
    codex_home.mkdir(parents=True, exist_ok=True)
    if existing != updated:
        destination.write_text(updated)

    override = codex_home / "AGENTS.override.md"
    if override.exists() and override.read_text().strip():
        print(f"warning: {override} masks {destination}", file=sys.stderr)


def parse_args(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--install-zakia", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    skill_directory = skill_root()
    try:
        check_generated_files(skill_directory)
        zakia_update = (
            prepare_zakia_update(skill_directory, options.codex_home)
            if options.install_zakia
            else None
        )
        install_workers(skill_directory, options.codex_home, options.force)
        if zakia_update is not None:
            install_zakia(options.codex_home, zakia_update)
    except (FileExistsError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
