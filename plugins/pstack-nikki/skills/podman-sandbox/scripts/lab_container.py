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

A podman label cannot be changed after a container is created, so the one
thing `up` must remember across runs is a sentinel file in the work volume.
It includes the recipe hash and current container start. `down` deletes it
with the clone whose state it describes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from lab_profile import RECIPE_NAME, Profile

SPEC_LABEL = "lab.spec"
MOUNT_SOURCE_READONLY = "/src-ro"
MOUNT_GIT_COMMON_READONLY = "/git-common-ro"
MOUNT_WORK = "/work"
PERSISTENT_DISPLAY = ":99"

RECIPE_LABEL = "lab.recipe.sha256"
SPEC_QUERY = '{{index .Config.Labels "' + SPEC_LABEL + '"}}'
RECIPE_QUERY = '{{index .Config.Labels "' + RECIPE_LABEL + '"}}'
RUNNING_QUERY = "{{.State.Running}}"
SETUP_SENTINEL_PREFIX = MOUNT_WORK + "/.lab-setup-"
READY_POLL_SEC = 2.0
PORT_TAKEN_SIGNS = ("address already in use", "port is already allocated")
PORT_TAKEN_HINT = (
    "the host port this lab publishes is already taken by another lab or "
    "process. Give this lab its own port with --port N"
)


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
    git_common_dir: str

    def to_label(self) -> str:
        """Serialise to the JSON stored in the `lab.spec` label."""
        return json.dumps(asdict(self), sort_keys=True)

    @staticmethod
    def from_label(text: str) -> LabSpec | None:
        """Parse a stored label, or None when it is absent or unreadable."""
        if not text.strip():
            return None
        try:
            stored = json.loads(text)
            return LabSpec(**stored)
        except (ValueError, TypeError):
            return None


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
        return f"lab-{self.name}"

    @property
    def volume(self) -> str:
        """`lab-<name>-work`, the private clone's writable home."""
        return f"lab-{self.name}-work"

    def clone_path(self, repo: Path) -> str:
        """`/work/<repo basename>`, the path of the clone in the container."""
        return f"{MOUNT_WORK}/{repo.name}"


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


def run(args: list[str]) -> subprocess.CompletedProcess:
    """Run `podman` with `args`, capturing both streams. The only call site."""
    return subprocess.run(["podman"] + args, capture_output=True, text=True,
                          check=False)


def podman(args: list[str], check: bool = True) -> str:
    """Run `podman` with `args` and return its stdout, stripped.

    The single choke point for every podman call. Raises LabError on a
    non-zero exit when `check`, with podman's own stderr in the message.
    """
    done = run(args)
    if check and done.returncode != 0:
        detail = done.stderr.strip() or done.stdout.strip()
        raise LabError(f"podman {' '.join(args)} failed: {detail}")
    return done.stdout.strip()


def podman_status(args: list[str]) -> int:
    """Return the exit code of `podman args`, discarding its output."""
    return run(args).returncode


def require_podman() -> str:
    """Return podman's version, or raise LabError naming what is missing."""
    if shutil.which("podman") is None:
        raise LabError("podman is not on PATH")
    return podman(["version", "--format", "{{.Client.Version}}"])


def read_spec(lab: Lab) -> LabSpec | None:
    """Read the `lab.spec` label, or None when the container is absent."""
    query = ["inspect", lab.container, "--format", SPEC_QUERY]
    return LabSpec.from_label(podman(query, check=False))


def recipe_sha256(profile: Profile, base: Profile | None) -> str:
    """Return the hash identifying the image `profile` builds.

    Folds `base`'s own hash in when this profile derives from base, so
    editing `base` changes the identity of every image built on it.
    """
    if base is None:
        return profile.recipe_sha256
    both = f"{base.recipe_sha256}\0{profile.recipe_sha256}"
    return hashlib.sha256(both.encode("utf-8")).hexdigest()


def build_image(profile: Profile, base: Profile | None) -> bool:
    """Build the profile's image unless it already matches its recipe hash.

    Converges `base` first when given, then folds base's recipe hash into
    this profile's image label, so a change to `base` rebuilds every profile
    derived from it. Returns True when a build ran.
    """
    changed = build_image(base, None) if base is not None else False
    wanted = recipe_sha256(profile, base)
    query = ["image", "inspect", profile.image, "--format", RECIPE_QUERY]
    built = podman(query, check=False)
    if built == wanted:
        return changed
    podman(["build", "--label", f"{RECIPE_LABEL}={wanted}",
            "--tag", profile.image,
            "--file", str(profile.directory / RECIPE_NAME),
            str(profile.directory)])
    return True


def create_container(
        lab: Lab, spec: LabSpec, repo: Path, git_common_dir: Path) -> None:
    """Create the container for `spec`, stopped, replacing any older one.

    Mounts the repo read-only at `/src-ro`, its common git directory at
    `/git-common-ro`, and the named volume at `/work`.
    The clone lives in a named volume rather than a host bind mount, so no
    uid mapping is needed and no container-owned file can land on the host.
    Publishes `spec.port` as `127.0.0.1:<port>:<port>` when set, so nothing
    on the local network reaches it. Exports `LAB_PORT` into the container
    so a profile's setup and ready hooks read the port instead of hardcoding
    it.

    The volume outlives the container, so recreating a lab for a new branch
    or a rebuilt image keeps the clone.
    """
    podman(["rm", "--force", lab.container], check=False)
    args = ["create", "--name", lab.container,
            "--label", f"{SPEC_LABEL}={spec.to_label()}",
            "--security-opt", "label=disable",
            "--volume", f"{repo}:{MOUNT_SOURCE_READONLY}:ro",
            "--volume", f"{git_common_dir}:{MOUNT_GIT_COMMON_READONLY}:ro",
            "--volume", f"{lab.volume}:{MOUNT_WORK}",
            "--workdir", MOUNT_WORK]
    if spec.port is not None:
        args += ["--publish", f"127.0.0.1:{spec.port}:{spec.port}",
                 "--env", f"LAB_PORT={spec.port}"]
    podman(args + [spec.image])


def start_container(lab: Lab) -> bool:
    """Start the container unless it is already running. True when started."""
    query = ["inspect", lab.container, "--format", RUNNING_QUERY]
    if podman(query, check=False) == "true":
        return False
    try:
        podman(["start", lab.container])
    except LabError as err:
        if any(sign in str(err) for sign in PORT_TAKEN_SIGNS):
            raise LabError(f"{err}\n{PORT_TAKEN_HINT}") from err
        raise
    return True


def exec_capture(lab: Lab, argv: list[str], workdir: str) -> str:
    """Run `argv` in the container at `workdir` and return its stdout."""
    return podman(["exec", "--workdir", workdir, lab.container] + argv)


def exec_status(lab: Lab, argv: list[str], workdir: str) -> int:
    """Return the exit code of `argv` run in the container at `workdir`."""
    return podman_status(["exec", "--workdir", workdir, lab.container] + argv)


def sync_clone(lab: Lab, repo: Path, branch: str, head: str) -> bool:
    """Make the clone's HEAD equal `head`, cloning from `/src-ro` if absent.

    Every git call is a separate argument list run inside the container. The
    branch name is an argv element, never part of a command string.

    A branch is reset to `head`; a tag, SHA, or detached HEAD checks out
    detached at `head`.
    """
    clone = lab.clone_path(repo)
    cloned = exec_status(lab, ["test", "-d", f"{clone}/.git"], MOUNT_WORK) == 0
    if cloned and at_revision(lab, clone, branch, head):
        return False
    if not cloned:
        exec_capture(lab, ["git", "clone", MOUNT_GIT_COMMON_READONLY, clone], MOUNT_WORK)
    else:
        exec_capture(lab, ["git", "fetch", "--quiet", MOUNT_GIT_COMMON_READONLY, head], clone)
        container_ref = has_container_only_commits(lab, clone, head)
        if container_ref:
            raise LabError(
                f"lab {lab.name} has commits only in the container on "
                f"{container_ref}. "
                "Create a git bundle before running up again."
            )
    if not cloned:
        exec_capture(lab, ["git", "fetch", "--quiet", MOUNT_GIT_COMMON_READONLY, head], clone)
    if is_branch(branch):
        exec_capture(lab, ["git", "checkout", "--quiet", "-B",
                           branch_name(branch), head], clone)
    else:
        exec_capture(lab, ["git", "checkout", "--quiet", "--detach", head], clone)
    exec_capture(lab, ["git", "update-ref", f"refs/lab/synced/{head}", head], clone)
    return True


def has_container_only_commits(lab: Lab, clone: str, head: str) -> str | None:
    """Return a lab ref containing a commit a reset to `head` would lose."""
    commit = exec_capture(lab, [
        "git", "rev-list", "--max-count=1", "HEAD", "--branches", "--not",
        head, "--glob=refs/lab/synced/*", "--remotes",
    ], clone)
    if not commit:
        return None
    refs = exec_capture(lab, [
        "git", "for-each-ref", "--format=%(refname)", "--contains", commit,
        "refs/heads",
    ], clone).splitlines()
    return refs[0] if refs else "HEAD"


def is_branch(reference: str) -> bool:
    """True when `reference` names a local branch rather than a revision."""
    return reference.startswith("refs/heads/")


def branch_name(reference: str) -> str:
    """Return the local branch name stored after the heads ref prefix."""
    prefix = "refs/heads/"
    return reference[len(prefix):] if reference.startswith(prefix) else reference


def at_revision(lab: Lab, clone: str, branch: str, head: str) -> bool:
    """True when the clone already sits on `branch`, or detached, at `head`."""
    head_now = exec_capture(lab, ["git", "rev-parse", "HEAD"], clone)
    if head_now != head:
        return False
    if not is_branch(branch):
        return True
    branch_now = exec_capture(lab, ["git", "branch", "--show-current"], clone)
    return branch_now == branch_name(branch)


def run_setup(lab: Lab, profile: Profile, workdir: str) -> bool:
    """Run the profile's `setup` argv once, from the clone directory.

    Skipped when a sentinel in the work volume already records a successful
    setup for this recipe hash and current start. A restart changes the
    sentinel because the volume outlives processes that setup launched.
    Raises LabError on a non-zero exit.
    """
    if not profile.setup:
        return False
    started_at = podman(["inspect", lab.container, "--format", "{{.State.StartedAt}}"])
    start_hash = hashlib.sha256(started_at.encode("utf-8")).hexdigest()
    sentinel = f"{SETUP_SENTINEL_PREFIX}{profile.recipe_sha256}-{start_hash}"
    if exec_status(lab, ["test", "-f", sentinel], MOUNT_WORK) == 0:
        return False
    exec_capture(lab, list(profile.setup), workdir)
    exec_capture(lab, ["touch", sentinel], MOUNT_WORK)
    return True


def wait_ready(lab: Lab, profile: Profile) -> bool:
    """Poll the profile's `ready` argv until it exits 0.

    Returns False when `ready` is absent. Raises LabError naming the lab and
    `ready_timeout_sec` when the deadline passes, because a lab that never
    became ready must fail here rather than at the agent's first real call.
    """
    if not profile.ready:
        return False
    deadline = time.monotonic() + profile.ready_timeout_sec
    while time.monotonic() < deadline:
        if exec_status(lab, list(profile.ready), MOUNT_WORK) == 0:
            return True
        time.sleep(READY_POLL_SEC)
    raise LabError(f"lab {lab.name} was not ready within "
                   f"{profile.ready_timeout_sec} seconds")


def exec_argv(lab: Lab, argv: list[str], workdir: str) -> int:
    """Run `argv` in the container at `workdir`, streaming to this process.

    Returns the command's exit code so the caller can exit with it. Does not
    wrap `argv` in a shell: a caller that wants pipes passes
    `["bash", "-lc", "..."]` and owns that string.
    """
    command = ["podman", "exec", "--interactive", "--workdir", workdir, lab.container]
    return subprocess.run(command + argv, check=False).returncode


def copy_out(lab: Lab, container_path: str, host_path: Path) -> None:
    """Copy one file out of the container to `host_path`."""
    podman(["cp", f"{lab.container}:{container_path}", str(host_path)])


def destroy(lab: Lab) -> None:
    """Remove the container and its volume. Does not fail on an absent lab."""
    podman(["rm", "--force", lab.container], check=False)
    podman(["volume", "rm", "--force", lab.volume], check=False)
