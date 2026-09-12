"""Converge one lab container with podman, and nothing else.

INVARIANT, enforced by review: every function in this module that reaches a
subprocess takes `list[str]` and passes it straight to `subprocess.run`
without `shell=True`. No function in this file builds a command by string
concatenation or f-string interpolation. A caller who needs a shell passes
`["bash", "-lc", script]` and owns that script itself. This closes the
injection the previous version opened by interpolating a branch name into a
remote `bash -lc` string.

podman is the only engine. There is no engine detection and no docker path,
because "works anywhere podman works" is a wider bar than any detection
logic bought, and the branching cost real lines in every call site.

State lives in one podman label, `lab.spec`, holding the JSON of a LabSpec.
There is no state file. The container is the state: if somebody removes it
with `podman rm`, the label goes with it, so the tool cannot believe in a
lab that no longer exists. A state file would drift from reality and would
have to be reconciled; a label cannot.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from lab_profile import Profile

SPEC_LABEL = "lab.spec"
MOUNT_SOURCE_READONLY = "/src-ro"
MOUNT_WORK = "/work"
PERSISTENT_DISPLAY = ":99"


class LabError(Exception):
    """podman refused, or the container is not in a state the command needs."""


@dataclass(frozen=True)
class LabSpec:
    """Everything that decides whether a container must be recreated.

    This is the value stored in the `lab.spec` label. `up` compares the
    stored spec against the wanted spec; any difference recreates the
    container. Adding a field here is how a new knob joins the converge
    check, so a knob cannot be forgotten.
    """

    repo: str
    branch: str
    profile: str
    port: int | None
    image: str
    recipe_sha256: str

    def to_label(self) -> str:
        """Serialise to the JSON stored in the `lab.spec` label."""
        raise NotImplementedError

    @staticmethod
    def from_label(text: str) -> LabSpec | None:
        """Parse a stored label, or None when it is absent or unreadable."""
        raise NotImplementedError


@dataclass(frozen=True)
class Lab:
    """A named lab, and the podman object names derived from that name.

    The name is the only identity. Everything else is a pure function of it,
    so two commands never disagree about which container or volume they mean.
    """

    name: str

    @property
    def container(self) -> str:
        """`lab-<name>`. Prefixed so `podman ps` reads without a filter."""
        raise NotImplementedError

    @property
    def volume(self) -> str:
        """`lab-<name>-work`, the private clone's writable home."""
        raise NotImplementedError

    def clone_path(self, repo: Path) -> str:
        """`/work/<repo basename>`, the path of the clone in the container."""
        raise NotImplementedError


@dataclass(frozen=True)
class ConvergeReport:
    """What `up` did, so its one output line can be printed by the caller.

    `changed` is the count of steps that altered something. A second `up`
    with no input change reports 0, which is the property an agent relies on
    to re-run `up` without paying for a rebuild.
    """

    lab: Lab
    spec: LabSpec
    clone_path: str
    head: str
    changed: int


def podman(args: list[str], check: bool = True) -> str:
    """Run `podman` with `args` and return its stdout, stripped.

    The single choke point for every podman call. Raises LabError on a
    non-zero exit when `check`, with podman's own stderr in the message.
    """
    raise NotImplementedError


def require_podman() -> str:
    """Return podman's version, or raise LabError naming what is missing."""
    raise NotImplementedError


def read_spec(lab: Lab) -> LabSpec | None:
    """Read the `lab.spec` label, or None when the container is absent."""
    raise NotImplementedError


def build_image(profile: Profile, base: Profile | None) -> bool:
    """Build the profile's image unless it already matches its recipe hash.

    Converges `base` first when given, then folds base's recipe hash into
    this profile's image label, so a change to `base` rebuilds every profile
    derived from it. Returns True when a build ran.
    """
    raise NotImplementedError


def create_container(lab: Lab, spec: LabSpec, repo: Path) -> None:
    """Create the container for `spec`, stopped.

    Mounts the repo read-only at `/src-ro` and the named volume at `/work`.
    The clone lives in a named volume rather than a host bind mount, so no
    uid mapping is needed and no container-owned file can land on the host.
    Publishes `spec.port` as `127.0.0.1:<port>:<port>` when set, so nothing
    on the local network reaches it. Exports `LAB_PORT` into the container
    so a profile's setup and ready hooks read the port instead of hardcoding
    it.
    """
    raise NotImplementedError


def start_container(lab: Lab) -> bool:
    """Start the container unless it is already running. True when started."""
    raise NotImplementedError


def sync_clone(lab: Lab, repo: Path, branch: str, head: str) -> bool:
    """Make the clone's HEAD equal `head`, cloning from `/src-ro` if absent.

    Every git call is a separate argument list run inside the container. The
    branch name is an argv element, never part of a command string.

    Destructive: resets the branch to `head` and discards container-side
    commits on that branch.
    """
    raise NotImplementedError


def run_setup(lab: Lab, profile: Profile, workdir: str) -> bool:
    """Run the profile's `setup` argv once, from the clone directory.

    Skipped when the spec label already records a successful setup for this
    recipe hash, which is what keeps `up` idempotent for a profile that
    mutates the clone. Raises LabError on a non-zero exit.
    """
    raise NotImplementedError


def wait_ready(lab: Lab, profile: Profile) -> bool:
    """Poll the profile's `ready` argv until it exits 0.

    Returns False when `ready` is absent. Raises LabError naming the lab and
    `ready_timeout_sec` when the deadline passes, because a lab that never
    became ready must fail here rather than at the agent's first real call.
    """
    raise NotImplementedError


def exec_argv(lab: Lab, argv: list[str], workdir: str) -> int:
    """Run `argv` in the container at `workdir`, streaming to this process.

    Returns the command's exit code so the caller can exit with it. Does not
    wrap `argv` in a shell: a caller that wants pipes passes
    `["bash", "-lc", "..."]` and owns that string.
    """
    raise NotImplementedError


def copy_out(lab: Lab, container_path: str, host_path: Path) -> None:
    """Copy one file out of the container to `host_path`."""
    raise NotImplementedError


def destroy(lab: Lab) -> None:
    """Remove the container and its volume. Does not fail on an absent lab."""
    raise NotImplementedError
