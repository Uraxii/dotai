"""Runs the code-quality guideline engine for one hook call.

The harness name (claude or codex) is the first argument and the hook payload
is on stdin. Every path exits 0: a failure here must never block the user's
work. A failure is never silent either: the user gets a systemMessage, and
the engine's stderr goes to guideline-state/errors.log in the data directory.
The engine needs Python 3.11 or later; without it SessionStart says so once.
This file must run on any Python 3.6 or later, so it uses no newer syntax.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(
    HOOKS, "..", "skills", "principle-code-quality", "scripts",
    "guideline_hook.py",
)
INTERPRETERS = (
    ["python3.14"], ["python3.13"], ["python3.12"], ["python3.11"],
    ["python3"], ["python"], ["py", "-3"],
)
VERSION_CHECK = "import sys; sys.exit(sys.version_info < (3, 11))"
MAX_LOG_BYTES = 200000
PYTHON_NOTICE = (
    "Notice: code-quality guideline hooks need Python 3.11 or later; none "
    "was found, so no guideline checks run in this session."
)
FAILURE_MESSAGE = (
    "pstack guideline hook failed; code-quality guidelines were not checked "
    "for this call."
)


def find_python():
    """The command of a Python 3.11 or later, or None."""
    if sys.version_info >= (3, 11):  # noqa: UP036  this file runs on any Python 3
        return [sys.executable]
    for command in INTERPRETERS:
        program = shutil.which(command[0])
        if program is None:
            continue
        try:
            found = subprocess.run(
                [program] + command[1:] + ["-I", "-c", VERSION_CHECK],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=5, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if found.returncode == 0:
            return [program] + command[1:]
    return None


def no_python():
    """Tell the agent and the user once, at session start."""
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw)
    except ValueError:
        return
    if isinstance(payload, dict) and (
        payload.get("hook_event_name") == "SessionStart"
    ):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": PYTHON_NOTICE,
            },
            "systemMessage": PYTHON_NOTICE,
        }))


def data_dir():
    data = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get(
        "PLUGIN_DATA"
    )
    if data:
        os.environ["PSTACK_GUIDELINE_DATA"] = data
        return data
    user = os.getuid() if hasattr(os, "getuid") else "user"
    return os.path.join(
        tempfile.gettempdir(), f"pstack-guideline-state-{user}"
    )


def log_failure(data, harness, status, errors):
    """Append the engine's stderr to errors.log and return its path.

    Write only in directories this user owns, and never through a symlink
    or into a file that is not a regular file.
    """
    state = os.path.join(data, "guideline-state")
    os.makedirs(state, mode=0o700, exist_ok=True)
    user = os.getuid() if hasattr(os, "getuid") else None
    for directory in (data, state):
        info = os.lstat(directory)
        if os.path.islink(directory) or user not in (None, info.st_uid):
            raise PermissionError(directory + " is not owned by this user")
    log = os.path.join(state, "errors.log")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    for extra in ("O_NOFOLLOW", "O_NONBLOCK"):
        flags |= getattr(os, extra, 0)
    descriptor = os.open(log, flags, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PermissionError(log + " is not a regular file")
        if handle.tell() > MAX_LOG_BYTES:
            handle.truncate(0)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        details = errors.decode("utf-8", "replace")
        handle.write(f"{stamp} {harness} exit {status}\n{details}\n")
    return log


def main(arguments):
    harness = arguments[0] if arguments else ""
    python = find_python()
    if python is None:
        no_python()
        return 0
    data = data_dir()
    try:
        engine = subprocess.run(
            python + ["-I", ENGINE, "--harness", harness],
            stderr=subprocess.PIPE, check=False,
        )
        status, errors = engine.returncode, engine.stderr
    except OSError as error:
        status, errors = "not started", str(error).encode()
    if status == 0:
        return 0
    try:
        details = " Details: " + log_failure(data, harness, status, errors)
    except Exception:  # noqa: BLE001  the log is best effort
        details = ""
    sys.stdout.flush()
    print(json.dumps({"systemMessage": FAILURE_MESSAGE + details}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
