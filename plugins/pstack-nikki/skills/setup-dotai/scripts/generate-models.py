#!/usr/bin/env python3
"""Stamp plugins/pstack-nikki/models.json into every skill file that names
a role from it.

models.json is the single source of model picks. A row's "models" is an
ordered preference list, or the name of a shared list under "panels". This
script finds, in each markdown file under plugins/pstack-nikki/skills, every
role name from models.json that the file's prose mentions (outside fenced
code), and stamps a "## Models" block listing that role's current models
between marker comments. Rerun after editing models.json; `--check` fails
without writing when a stamped block is stale.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


__all__ = ["main"]

START = "<!-- dotai:models:start -->"
END = "<!-- dotai:models:end -->"
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_roles(models_path: Path) -> list[tuple[str, list[str]]]:
    data = json.loads(models_path.read_text())
    panels = data.get("panels", {})
    roles = []
    for row in data["roles"]:
        models = row["models"]
        if isinstance(models, str):
            models = panels[models]
        roles.append((row["role"], list(models)))
    return roles


def role_pattern(role: str) -> re.Pattern[str]:
    words = [re.escape(word) for word in role.split(" ")]
    return re.compile(r"\s+".join(words))


def strip_fenced_code(text: str) -> str:
    return FENCE_RE.sub("", text)


def remove_owned_block(text: str) -> str:
    start_count = text.count(START)
    end_count = text.count(END)
    if start_count == 0 and end_count == 0:
        return text
    if start_count != 1 or end_count != 1:
        raise ValueError("malformed dotai:models markers")
    start = text.index(START)
    end = text.index(END) + len(END)
    before = text[:start].rstrip("\n")
    after = text[end:].lstrip("\n")
    if before and after:
        return f"{before}\n\n{after}"
    return f"{before}{after}".rstrip("\n") + ("\n" if (before or after) else "")


def replace_owned_block(text: str, body: str) -> str:
    block = f"{START}\n{body}\n{END}"
    start_count = text.count(START)
    end_count = text.count(END)
    if start_count == 0 and end_count == 0:
        stripped = text.rstrip("\n")
        separator = "\n\n" if stripped else ""
        return f"{stripped}{separator}{block}\n"
    if start_count != 1 or end_count != 1:
        raise ValueError("malformed dotai:models markers")
    start = text.index(START)
    end = text.index(END) + len(END)
    return f"{text[:start]}{block}{text[end:]}".rstrip("\n") + "\n"


def render_body(models_json_label: str, matched: list[tuple[str, list[str]]]) -> str:
    lines = [
        "## Models",
        "",
        f"Stamped from `{models_json_label}` (edit there, rerun "
        "`generate-models.py`). Row absent -> omit `model`, child inherits.",
        "",
    ]
    for role, models in matched:
        rendered = ", ".join(f"`{model}`" for model in models)
        lines.append(f"- `{role}`: {rendered}")
    return "\n".join(lines)


def matched_roles(
    text: str, roles: list[tuple[str, list[str]]]
) -> list[tuple[str, list[str]]]:
    scannable = strip_fenced_code(remove_owned_block(text))
    return [
        (role, models)
        for role, models in roles
        if role_pattern(role).search(scannable)
    ]


def expected_files(
    skills_dir: Path, roles: list[tuple[str, list[str]]], models_json_label: str
) -> dict[Path, str]:
    expected = {}
    for path in sorted(skills_dir.rglob("*.md")):
        text = path.read_text()
        matched = matched_roles(text, roles)
        if matched:
            expected[path] = replace_owned_block(
                text, render_body(models_json_label, matched)
            )
        elif START in text or END in text:
            expected[path] = remove_owned_block(text)
    return expected


def check_files(expected: dict[Path, str]) -> tuple[Path, ...]:
    return tuple(path for path, content in expected.items() if path.read_text() != content)


def write_files(expected: dict[Path, str]) -> None:
    for path, content in expected.items():
        if path.read_text() != content:
            path.write_text(content)


def parse_args(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when a stamped Models block is missing or stale.",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    root = plugin_root()
    roles = load_roles(root / "models.json")
    expected = expected_files(root / "skills", roles, "plugins/pstack-nikki/models.json")

    if not options.check:
        write_files(expected)
        return 0

    stale = check_files(expected)
    for path in stale:
        print(f"stale Models block: {path}", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
