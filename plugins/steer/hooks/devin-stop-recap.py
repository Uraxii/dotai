import json
import os
from pathlib import Path
import re
import subprocess
import sys


MODEL_ID = re.compile(r"(?:claude-)?(?:opus|sonnet|haiku|fable)-[0-9]+(?:[.-][0-9]+)*(?:-latest)?", re.I)
SECRET_KEY = re.compile(r"token|secret|password|credential|authorization|cookie|api.?key", re.I)


def redact(value, key=""):
    if SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if key == "stop_hook_active" and isinstance(value, bool):
        return value
    if key == "hook_event_name" and value == "Stop":
        return value
    if "model" in key.lower() and isinstance(value, str) and MODEL_ID.fullmatch(value):
        return value
    return "[REDACTED]"


def record_diagnostics(payload):
    path = Path.home() / "steer-devin-stop.jsonl"
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags, 0o600), "a") as stream:
        os.fchmod(stream.fileno(), 0o600)
        print(json.dumps({"stdin": redact(payload), "env": redact(dict(os.environ))}), file=stream)


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if os.getenv("STEER_DEVIN_STOP_DIAGNOSTICS") == "1":
        try:
            record_diagnostics(payload)
        except OSError:
            print("steer: cannot write Devin Stop diagnostics", file=sys.stderr)
    hook = Path(__file__).with_name("opus_5_reduce_output.sh")
    if not isinstance(payload, dict):
        return
    subprocess.run(["bash", str(hook), "--harness", "devin"], input=raw, text=True, check=True)


if __name__ == "__main__":
    main()
