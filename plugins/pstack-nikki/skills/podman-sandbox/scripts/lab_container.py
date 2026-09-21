"""Read a repository's container definition and converge its lab container.

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
The container is the state: if somebody removes it with `podman rm`, the
label goes with it, so the tool cannot believe in a lab that no longer
exists. A state file would drift from reality; a label cannot.

A podman label cannot be changed after a container is created, so the one
thing `up` must remember across runs is a sentinel file in the work volume.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

SPEC_LABEL = "lab.spec"
MOUNT_SOURCE_READONLY = "/src-ro"
MOUNT_GIT_COMMON_READONLY = "/git-common-ro"
MOUNT_WORK = "/work"
PERSISTENT_DISPLAY = ":99"

DEFINITION_SUBPATH = ".sandbox-container"
RECIPE_NAME = "Containerfile"
SETUP_NAME = "setup"
READY_NAME = "ready"
READY_TIMEOUT_SEC = 180
IMAGE_TAG_PREFIX = "podman-sandbox/"
IMAGE_TAG_SUFFIX = ":latest"
IMAGE_TAG_DIGEST_CHARS = 12
IMAGE_TAG_FALLBACK_STEM = "repo"
ILLEGAL_IN_IMAGE_TAG = re.compile("[^a-z0-9._-]")
IMAGE_TAG_EDGE_SEPARATORS = "._-"

SHOT_COMMAND_SOURCE = Path(__file__).resolve().parent / "lab-shot"
SHOT_COMMAND_PATH = "/usr/local/bin/lab-shot"
SHOT_COMMAND_MODE = 0o755

SPEC_QUERY = '{{index .Config.Labels "' + SPEC_LABEL + '"}}'
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
class ContainerDefinition:
    """What `<repo>/.sandbox-container` declares, as read from disk.

    `directory` is handed to podman as the build context, so every file in
    it reaches the image. `recipe_sha256` covers that whole directory, which
    is why editing a hook rebuilds the image.

    `setup_command` runs once after the private clone exists and must exit
    0. `ready_command` is polled until it exits 0 or READY_TIMEOUT_SEC
    elapses. Both are argument lists naming an executable on the read-only
    mount of the repository. An empty tuple means the hook is absent.
    """

    directory: Path
    image: str
    recipe_sha256: str
    setup_command: tuple[str, ...]
    ready_command: tuple[str, ...]


def load_definition(repo: Path) -> ContainerDefinition:
    """Read `<repo>/.sandbox-container`, or raise LabError naming the path."""
    directory = repo / DEFINITION_SUBPATH
    if not directory.is_dir():
        raise LabError(
            f"no container definition at {directory}\n"
            f"create that directory and write a {RECIPE_NAME} in it. "
            f"Executables named {SETUP_NAME} and {READY_NAME} beside it are "
            "optional"
        )
    if not (directory / RECIPE_NAME).is_file():
        raise LabError(
            f"no {RECIPE_NAME} in {directory}\n"
            f"write one there. Executables named {SETUP_NAME} and "
            f"{READY_NAME} beside it are optional"
        )
    recipe_sha256 = hash_directory(directory)
    return ContainerDefinition(
        directory=directory,
        image=image_tag(repo, recipe_sha256),
        recipe_sha256=recipe_sha256,
        setup_command=hook_command(directory, SETUP_NAME),
        ready_command=hook_command(directory, READY_NAME),
    )


def hook_command(directory: Path, name: str) -> tuple[str, ...]:
    """Return the container argv running `name`, or () when it is absent.

    The repository is mounted read-only at `/src-ro`, so a hook the project
    committed is already inside the container at a known path.
    """
    if not (directory / name).is_file():
        return ()
    return (f"{MOUNT_SOURCE_READONLY}/{DEFINITION_SUBPATH}/{name}",)


def image_tag(repo: Path, recipe_sha256: str) -> str:
    """Return the image tag for `repo`, naming it and its recipe hash.

    The hash is part of the tag, so two repositories whose directories share
    a name cannot build over each other's image, and a tag that exists is
    always an image built from that exact directory.
    """
    stem = ILLEGAL_IN_IMAGE_TAG.sub("-", repo.name.lower())
    stem = stem.strip(IMAGE_TAG_EDGE_SEPARATORS) or IMAGE_TAG_FALLBACK_STEM
    digest = recipe_sha256[:IMAGE_TAG_DIGEST_CHARS]
    return f"{IMAGE_TAG_PREFIX}{stem}-{digest}{IMAGE_TAG_SUFFIX}"


def hash_directory(directory: Path) -> str:
    """Hash every file under `directory` into one stable digest.

    Walks in sorted relative-path order and feeds the path, the owner
    execute bit, and the bytes of each file into one sha256. Sorting makes
    the digest independent of filesystem order, so the same directory hashes
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


def build_image(definition: ContainerDefinition) -> bool:
    """Build the image unless the tag already exists. True when a build ran.

    The tag carries the recipe hash, so existence is the whole check.
    """
    if podman_status(["image", "exists", definition.image]) == 0:
        return False
    podman(["build", "--tag", definition.image,
            "--file", str(definition.directory / RECIPE_NAME),
            str(definition.directory)])
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
    so the setup and ready hooks read the port instead of hardcoding it.

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


def install_shot_command(lab: Lab) -> None:
    """Copy `lab-shot` into the container, overwriting any older copy.

    `up` runs this every time, so editing the skill's own `lab-shot`
    reaches an existing lab. It is not part of LabSpec: a container holding
    an older copy is not worth destroying a clone over.

    Copied rather than bind-mounted: a bind mount would write a host path
    into the container's spec, and the spec is read back as lab state.
    """
    with tempfile.TemporaryDirectory() as staging:
        staged = Path(staging) / SHOT_COMMAND_SOURCE.name
        shutil.copyfile(SHOT_COMMAND_SOURCE, staged)
        staged.chmod(SHOT_COMMAND_MODE)
        podman(["cp", str(staged), f"{lab.container}:{SHOT_COMMAND_PATH}"])


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
        exec_capture(lab, [
            "git", "fetch", "--quiet", "--prune", MOUNT_GIT_COMMON_READONLY,
            "+refs/heads/*:refs/lab/host/heads/*",
            "+refs/tags/*:refs/lab/host/tags/*",
        ], clone)
        container_refs = has_container_only_commits(lab, clone, branch, head)
        if container_refs:
            bundle = f"/tmp/{lab.name}.bundle"
            lines = [f"lab {lab.name} has commits only in the container. "
                     "To save them, run:"]
            for ref, tip in container_refs:
                lines += [
                    f"scripts/lab exec {lab.name} git bundle create {bundle} {ref}",
                    f"podman cp lab-{lab.name}:{bundle} {bundle}",
                    f"git fetch {bundle} {ref}:refs/heads/lab-rescue/{lab.name}-{tip[:12]}",
                ]
            raise LabError("\n".join(lines))
    if not cloned:
        exec_capture(lab, ["git", "fetch", "--quiet", MOUNT_GIT_COMMON_READONLY, head], clone)
    if is_branch(branch):
        exec_capture(lab, ["git", "checkout", "--quiet", "-B",
                           branch_name(branch), head], clone)
    else:
        exec_capture(lab, ["git", "checkout", "--quiet", "--detach", head], clone)
    exec_capture(lab, ["git", "update-ref", f"refs/lab/synced/{head}", head], clone)
    return True


def has_container_only_commits(
    lab: Lab, clone: str, branch: str, head: str
) -> list[tuple[str, str]]:
    """Return (ref, tip) pairs a reset to `head` would lose; needs sync_clone's host-ref fetch."""
    refs: list[str] = []
    if is_branch(branch) and exec_status(
            lab, ["git", "show-ref", "--verify", "--quiet", branch], clone
    ) == 0:
        refs.append(branch)
    if not exec_capture(lab, ["git", "branch", "--show-current"], clone):
        refs.append("HEAD")
    container_refs = []
    for ref in refs:
        command = [
            "git", "rev-list", "--max-count=1", ref, "--not", head,
            "--glob=refs/lab/synced/*", "--glob=refs/lab/host/*", "--remotes",
        ]
        if ref == branch:
            command += ["--exclude=" + branch_name(branch), "--branches"]
        tip = exec_capture(lab, command, clone)
        if tip:
            container_refs.append((ref, tip))
    return container_refs


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


def run_setup(lab: Lab, definition: ContainerDefinition, workdir: str) -> bool:
    """Run the `setup` hook once, from the clone directory.

    Skipped when a sentinel in the work volume already records a successful
    setup for this recipe hash and current start. A restart changes the
    sentinel because the volume outlives processes that setup launched.
    Raises LabError on a non-zero exit.
    """
    if not definition.setup_command:
        return False
    started_at = podman(["inspect", lab.container, "--format", "{{.State.StartedAt}}"])
    start_hash = hashlib.sha256(started_at.encode("utf-8")).hexdigest()
    sentinel = f"{SETUP_SENTINEL_PREFIX}{definition.recipe_sha256}-{start_hash}"
    if exec_status(lab, ["test", "-f", sentinel], MOUNT_WORK) == 0:
        return False
    exec_capture(lab, list(definition.setup_command), workdir)
    exec_capture(lab, ["touch", sentinel], MOUNT_WORK)
    return True


def wait_ready(lab: Lab, definition: ContainerDefinition) -> bool:
    """Poll the `ready` hook until it exits 0.

    Returns False when the hook is absent. Raises LabError when the deadline
    passes, because a lab that never became ready must fail here rather than
    at the agent's first real call.
    """
    if not definition.ready_command:
        return False
    deadline = time.monotonic() + READY_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if exec_status(lab, list(definition.ready_command), MOUNT_WORK) == 0:
            return True
        time.sleep(READY_POLL_SEC)
    raise LabError(f"lab {lab.name} was not ready within "
                   f"{READY_TIMEOUT_SEC} seconds")


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
