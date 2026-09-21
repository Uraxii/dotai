#!/usr/bin/env python3
"""Check that plugins/pstack/models.json only names models it can back.

models.json is the single source of model picks, and nothing copies it any
more: skills point at it by path, and a user overrides a role for one harness
in that harness's own sheet (`~/.claude/pstack-models.md` on Claude Code,
`~/.codex/pstack-models.md` on Codex; see the `setup-pstack` skill).

A role's "models" is an object keyed by harness (`claude`, `codex`,
`copilot`), each value an ordered preference list for that harness, or the
name of a shared list under "panels". This script catches the two mistakes
that shape allows: a harness key outside the three, and a slug placed under a
harness whose "available" list does not carry it, which is how a `gpt-*` name
ends up pinned on Claude Code where it resolves to nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


__all__ = ["main", "validate_models_json"]

# Harness keys, the only ones models.json may use.
HARNESSES: tuple[str, ...] = ("claude", "codex", "copilot")


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def available_slugs(data: dict) -> dict[str, set[str]]:
    return {
        harness: {entry["slug"] for entry in entries}
        for harness, entries in data["available"].items()
    }


def validate_harness_models(models: dict, avail: dict[str, set[str]], context: str) -> None:
    for harness, slugs in models.items():
        if harness not in HARNESSES:
            raise ValueError(f"{context}: unknown harness {harness!r}")
        for slug in slugs:
            if slug not in avail.get(harness, set()):
                raise ValueError(
                    f"{context}: {slug!r} is not in available[{harness!r}]"
                )


def validate_models_json(data: dict) -> None:
    """Raise ValueError on any harness key or slug models.json cannot back."""
    for harness in data["available"]:
        if harness not in HARNESSES:
            raise ValueError(f"available: unknown harness {harness!r}")
    avail = available_slugs(data)

    panels = data.get("panels", {})
    for name, models in panels.items():
        validate_harness_models(models, avail, f"panels.{name}")

    for row in data["roles"]:
        models = row["models"]
        if isinstance(models, str):
            if models not in panels:
                raise ValueError(f"role {row['role']!r}: unknown panel {models!r}")
            continue
        validate_harness_models(models, avail, f"role {row['role']!r}")


def main(arguments: list[str] | None = None) -> int:
    models_path = plugin_root() / "models.json"
    try:
        validate_models_json(json.loads(models_path.read_text()))
    except ValueError as error:
        print(f"invalid models.json: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
