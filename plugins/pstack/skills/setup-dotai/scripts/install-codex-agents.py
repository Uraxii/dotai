#!/usr/bin/env python3
"""Install the dotai worker agent files into a Codex home directory."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


__all__ = ["main"]


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


def parse_args(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    skill_directory = skill_root()
    try:
        check_generated_files(skill_directory)
        install_workers(skill_directory, options.codex_home, options.force)
    except (FileExistsError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
