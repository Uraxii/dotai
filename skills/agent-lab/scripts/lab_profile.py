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
import stat
from dataclasses import dataclass
from pathlib import Path

BUILTIN_PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
USER_PROFILES_DIR = Path.home() / ".config" / "agent-lab" / "profiles"
PROJECT_PROFILES_SUBPATH = Path(".nikki-agents") / "lab" / "profiles"

MANIFEST_NAME = "profile.json"
RECIPE_NAME = "Containerfile"
DEFAULT_READY_TIMEOUT_SEC = 180

IMAGE_TAG_PREFIX = "agent-lab/"
IMAGE_TAG_SUFFIX = ":latest"
ARGV_KEYS = ("setup", "ready")
INTEGER_KEYS = ("port", "ready_timeout_sec")


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
        return f"{IMAGE_TAG_PREFIX}{self.name}{IMAGE_TAG_SUFFIX}"


def search_path(repo: Path) -> tuple[Path, ...]:
    """Return the profile directories to search, nearest project first."""
    return (
        repo / PROJECT_PROFILES_SUBPATH,
        USER_PROFILES_DIR,
        BUILTIN_PROFILES_DIR,
    )


def load(name: str, repo: Path) -> Profile:
    """Find profile `name` and parse it, or raise ProfileError.

    Raises ProfileError when no directory matches, when the matching
    directory has no Containerfile, or when profile.json is not an object
    whose keys match the contract.
    """
    directory = first_match(name, repo)
    if directory is None:
        known = ", ".join(available(repo)) or "none"
        raise ProfileError(f"no profile named {name}. Found: {known}")
    if not (directory / RECIPE_NAME).is_file():
        raise ProfileError(f"{directory} holds no {RECIPE_NAME}")
    manifest = directory / MANIFEST_NAME
    text = manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
    try:
        fields = parse_manifest(text)
    except ProfileError as err:
        raise ProfileError(f"{manifest}: {err}") from err
    return Profile(
        name=name,
        directory=directory,
        port=fields["port"],
        setup=fields["setup"],
        ready=fields["ready"],
        ready_timeout_sec=fields["ready_timeout_sec"],
        recipe_sha256=hash_directory(directory),
    )


def first_match(name: str, repo: Path) -> Path | None:
    """Return the first directory on the search path named `name`."""
    for parent in search_path(repo):
        candidate = parent / name
        if candidate.is_dir():
            return candidate
    return None


def parse_manifest(text: str) -> dict[str, object]:
    """Parse profile.json text into validated, defaulted fields.

    This is the only boundary where profile.json is untyped. It rejects
    unknown keys, a non-integer `port`, a `setup` or `ready` that is not a
    list of strings, and an empty string inside either list. Callers past
    this point trust the Profile fields.
    """
    fields: dict[str, object] = {
        "port": None,
        "setup": (),
        "ready": (),
        "ready_timeout_sec": DEFAULT_READY_TIMEOUT_SEC,
    }
    if not text.strip():
        return fields
    try:
        declared = json.loads(text)
    except ValueError as err:
        raise ProfileError(f"not valid JSON: {err}") from err
    if not isinstance(declared, dict):
        raise ProfileError("must hold a JSON object")
    unknown = sorted(set(declared) - set(fields))
    if unknown:
        raise ProfileError(f"unknown keys: {', '.join(unknown)}")
    for key in INTEGER_KEYS:
        if key in declared:
            fields[key] = as_integer(declared[key], key)
    for key in ARGV_KEYS:
        if key in declared:
            fields[key] = as_argv(declared[key], key)
    return fields


def as_integer(value: object, key: str) -> int:
    """Return `value` as an int, rejecting bools and every other type."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileError(f"{key} must be an integer")
    return value


def as_argv(value: object, key: str) -> tuple[str, ...]:
    """Return `value` as an argument list of non-empty strings."""
    if not isinstance(value, list):
        raise ProfileError(f"{key} must be a list of strings")
    for element in value:
        if not isinstance(element, str) or not element:
            raise ProfileError(f"{key} must hold non-empty strings only")
    return tuple(value)


def hash_directory(directory: Path) -> str:
    """Hash every file under `directory` into one stable digest.

    Walks in sorted relative-path order and feeds the path, the owner
    execute bit, and the bytes of each file into one sha256. Sorting makes
    the digest independent of filesystem order, so the same profile hashes
    the same on every machine. The execute bit is included because a setup
    script that loses `+x` changes behaviour without changing bytes.
    """
    found = [
        (path.relative_to(directory).as_posix(), path)
        for path in directory.rglob("*")
        if path.is_file()
    ]
    digest = hashlib.sha256()
    for relative, path in sorted(found):
        content = path.read_bytes()
        executable = int(bool(path.stat().st_mode & stat.S_IXUSR))
        header = f"{relative}\0{executable}\0{len(content)}\0"
        digest.update(header.encode("utf-8"))
        digest.update(content)
    return digest.hexdigest()


def available(repo: Path) -> tuple[str, ...]:
    """Return every profile name found on the search path, for error text."""
    found = []
    for parent in search_path(repo):
        if not parent.is_dir():
            continue
        for candidate in sorted(parent.iterdir()):
            if (candidate / RECIPE_NAME).is_file():
                found.append(candidate.name)
    return tuple(dict.fromkeys(found))
