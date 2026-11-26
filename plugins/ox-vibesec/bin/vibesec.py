import fcntl
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


INSTALLER_URL = "https://ox-vibesec.s3.eu-west-1.amazonaws.com/vibesec-installation/install.sh"
INSTALLER_SHA256 = "51f97f30518e7ff3b48a8d90b404b243896bc5d24f9d8b074d68d9846d3e1a25"
LAUNCHER = Path(__file__).resolve().parents[1] / "hooks/ox"


def verified_installer(staged, destination, env):
    if staged.exists():
        destination.write_bytes(staged.read_bytes())
    else:
        subprocess.run(
            ["curl", "-fsSL", "--max-time", "15", "-o", str(destination), INSTALLER_URL],
            env=env, check=True, capture_output=True, timeout=17,
        )
    if hashlib.sha256(destination.read_bytes()).hexdigest() != INSTALLER_SHA256:
        raise RuntimeError("OX installer checksum mismatch")
    return destination


def redact(value, key):
    if isinstance(value, str):
        return value.replace(key, "[redacted]")
    if isinstance(value, dict):
        return {k: redact(v, key) for k, v in value.items()}
    return value


class Runtime:
    def __init__(self, home, staged):
        self.home = home
        self.staged = staged
        self.env = {k: os.environ[k] for k in (
            "PATH", "LANG", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY",
            "no_proxy", "SSL_CERT_FILE", "NODE_EXTRA_CA_CERTS",
        ) if k in os.environ}
        self.env.update(HOME=str(home), TMPDIR=str(home / "tmp"))

    def installed(self, key):
        try:
            auth = json.loads((self.home / ".claude/.ox.json").read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(auth, dict) or auth.get("access_token") != key:
            return None
        if not (self.home / ".claude/hooks/ox_mind.js").is_file():
            return None
        if not any(os.access(p, os.X_OK) for p in self.home.glob(".ox/node/v*/bin/node")):
            return None
        return ["sh", LAUNCHER]

    def start(self, key):
        self.home.mkdir(parents=True, exist_ok=True)
        tmp = self.home / "tmp"
        tmp.mkdir(exist_ok=True)
        with (self.home / ".install.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return None
            command = self.installed(key)
            if command:
                return command
            with tempfile.TemporaryDirectory(dir=tmp) as directory:
                installer = verified_installer(self.staged, Path(directory) / "install.sh", self.env)
                args = ["bash", str(installer), "--token-stdin", "--ide", "claude"]
                proxy = self.env.get("HTTPS_PROXY") or self.env.get("https_proxy") or ""
                if proxy.startswith("http://") and urlsplit(proxy).username is None:
                    args += ["--proxy", proxy]
                result = subprocess.run(
                    args, input=key + "\n", text=True, capture_output=True,
                    env=self.env, cwd=self.home, timeout=78,
                )
            command = self.installed(key) if result.returncode == 0 else None
            if not command:
                raise RuntimeError("OX installer failed")
            return command

    def run(self, payload, cwd, key, *, initialize=False):
        os.umask(0o077)
        command = self.start(key) if initialize else self.installed(key)
        if not command:
            return None
        return subprocess.run(
            command, input=json.dumps(redact(payload, key)), text=True, capture_output=True,
            env=self.env, cwd=cwd, timeout=20,
        )
