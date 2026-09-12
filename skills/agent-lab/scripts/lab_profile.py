"""Find an environment profile on disk and read what it declares.

A profile is a directory that podman can use as a build context. It must
contain a `Containerfile`. Everything else is optional.

Search order, first match wins:

1. `<repo>/.nikki-agents/lab/profiles/<name>/`
2. `~/.config/agent-lab/profiles/<name>/`
3. `<this skill>/profiles/<name>/`

The skill ships exactly one profile, `base`. It holds no per-profile code:
a new environment is a new directory, never an edit to this file.

The optional `profile.json` beside the Containerfile declares four things,
each of which has a default:

    {
      "port": 6551,
      "setup": ["/usr/local/bin/godot-lab-setup"],
      "ready": ["/usr/local/bin/godot-lab-ready"],
      "ready_timeout_sec": 180
    }

`setup` and `ready` are argument lists run inside the container, never
shell strings. See `references/profile-contract.md`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

BUILTIN_PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
USER_PROFILES_DIR = Path.home() / ".config" / "agent-lab" / "profiles"
PROJECT_PROFILES_SUBPATH = Path(".nikki-agents") / "lab" / "profiles"

MANIFEST_NAME = "profile.json"
RECIPE_NAME = "Containerfile"
DEFAULT_READY_TIMEOUT_SEC = 180


class ProfileError(Exception):
    """A profile is missing, or its profile.json does not match the contract."""


@dataclass(frozen=True)
class Profile:
    """One environment a lab can run, as read from disk.

    `directory` is handed to podman as the build context, so every file in
    it reaches the image. `recipe_sha256` covers that whole directory, which
    is why editing a profile's setup script rebuilds the image.

    `setup` runs once after the private clone exists and must exit 0.
    `ready` is polled until it exits 0 or `ready_timeout_sec` elapses.
    Both are argument lists. An empty tuple means the hook is absent.
    """

    name: str
    directory: Path
    port: int | None
    setup: tuple[str, ...]
    ready: tuple[str, ...]
    ready_timeout_sec: int
    recipe_sha256: str

    @property
    def image(self) -> str:
        """The image tag this profile builds, for example `agent-lab/base`."""
        raise NotImplementedError


def search_path(repo: Path) -> tuple[Path, ...]:
    """Return the profile directories to search, nearest project first."""
    raise NotImplementedError


def load(name: str, repo: Path) -> Profile:
    """Find profile `name` and parse it, or raise ProfileError.

    Raises ProfileError when no directory matches, when the matching
    directory has no Containerfile, or when profile.json is not an object
    whose keys match the contract.
    """
    raise NotImplementedError


def parse_manifest(text: str) -> dict[str, object]:
    """Parse profile.json text into validated, defaulted fields.

    This is the only boundary where profile.json is untyped. It rejects
    unknown keys, a non-integer `port`, a `setup` or `ready` that is not a
    list of strings, and an empty string inside either list. Callers past
    this point trust the Profile fields.
    """
    raise NotImplementedError


def hash_directory(directory: Path) -> str:
    """Hash every file under `directory` into one stable digest.

    Walks in sorted relative-path order and feeds the path, the owner
    execute bit, and the bytes of each file into one sha256. Sorting makes
    the digest independent of filesystem order, so the same profile hashes
    the same on every machine. The execute bit is included because a setup
    script that loses `+x` changes behaviour without changing bytes.
    """
    raise NotImplementedError


def available(repo: Path) -> tuple[str, ...]:
    """Return every profile name found on the search path, for error text."""
    raise NotImplementedError
