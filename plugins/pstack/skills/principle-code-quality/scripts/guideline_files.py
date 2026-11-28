"""Guideline files: frontmatter parsing, languages, keyword matching."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

REQUIRED_KEYS = ("id", "languages", "scope", "severity", "enabled", "detectors")
LIST_KEYS = ("keywords", "paths", "exclude")
ALLOWED_VALUES = {
    "scope": ("global", "contextual"),
    "severity": ("block", "warn"),
    "enabled": ("true", "false"),
}

class GuidelineError(ValueError):
    """A guideline file that breaks the frontmatter rules."""


class Guideline(NamedTuple):
    id: str
    languages: frozenset[str]
    scope: str
    severity: str
    enabled: bool
    detectors: tuple[tuple[str, str], ...]
    keywords: tuple[str, ...]
    paths: tuple[str, ...]
    exclude: tuple[str, ...]
    body: str

    @property
    def ambient(self) -> bool:
        """Sent when its language is first seen: it has no other trigger."""
        return self.scope == "global" or not (self.detectors or self.keywords)

    @property
    def label(self) -> str:
        return self.severity if self.scope == "global" else "warn"


def comma_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise GuidelineError("no frontmatter")
    end = lines.index("---", 1)
    keys: dict[str, str] = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        if key in keys:
            raise GuidelineError(f"duplicate key {key}")
        if key not in REQUIRED_KEYS + LIST_KEYS:
            raise GuidelineError(f"unknown key {key}")
        keys[key] = value.strip()
    return keys, "\n".join(lines[end + 1:]).strip()


def parse_detectors(value: str) -> tuple[tuple[str, str], ...]:
    pairs = [item.partition(":") for item in comma_list(value)]
    if not all(tool and code for tool, _, code in pairs):
        raise GuidelineError("bad value for detectors")
    return tuple((tool, code) for tool, _, code in pairs)


def parse_guideline(text: str) -> Guideline:
    keys, body = frontmatter(text)
    for key in REQUIRED_KEYS:
        if key not in keys:
            raise GuidelineError(f"missing key {key}")
    for key, allowed in ALLOWED_VALUES.items():
        if keys[key] not in allowed:
            raise GuidelineError(f"bad value for {key}")
    if not keys["id"] or not keys["languages"] or not body:
        raise GuidelineError("empty id, languages, or body")
    return Guideline(
        id=keys["id"],
        languages=frozenset(comma_list(keys["languages"])),
        scope=keys["scope"],
        severity=keys["severity"],
        enabled=keys["enabled"] == "true",
        detectors=parse_detectors(keys["detectors"]),
        keywords=comma_list(keys.get("keywords", "")),
        paths=comma_list(keys.get("paths", "")),
        exclude=comma_list(keys.get("exclude", "")),
        body=body,
    )


def load_guidelines(directory: Path) -> tuple[list[Guideline], list[str]]:
    """Return the valid guidelines and one notice per invalid file."""
    guidelines, notices = [], []
    for path in sorted(directory.iterdir()):
        if path.suffix != ".md":
            continue
        try:
            guidelines.append(parse_guideline(path.read_text("utf-8")))
        except (GuidelineError, ValueError) as error:
            notices.append(
                f"Notice: skipped invalid guideline file {path.name}: {error}"
            )
    return guidelines, notices


def load_extensions(languages_toml: Path) -> dict[str, str]:
    """Map each file extension in languages.toml to its language id."""
    tables = tomllib.loads(languages_toml.read_text("utf-8"))
    return {
        extension: language
        for language, table in tables.items()
        for extension in table["extensions"]
    }


def language_of(name: str, extensions: Mapping[str, str]) -> str | None:
    """Pick the language of the longest extension the file name ends with."""
    lowered = name.lower()
    matches = [ext for ext in extensions if lowered.endswith(ext)]
    return extensions[max(matches, key=len)] if matches else None


def keyword_matches(keyword: str, lowered_text: str) -> bool:
    pattern = r"(?<![a-z0-9_])" + re.escape(keyword) + r"(?![a-z0-9_])"
    return re.search(pattern, lowered_text) is not None
