# Installing or updating codebase-memory-mcp

Ask the user before installing or updating anything. State which command you
intend to run and wait for a yes. Do not install on silence.

## Check the installed and latest versions

```bash
codebase-memory-mcp --version
gh release view -R DeusData/codebase-memory-mcp --json tagName -q .tagName
```

Update when the installed version is older than the latest release, or when
the binary prints a deprecation warning for the way this skill calls it.

## Install or update to the latest release

The upstream install script installs a new binary and updates an existing
one. Always pass `--skip-config`:

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config
```

`--skip-config` installs the binary only. Without it, the script writes MCP
entries, hooks, and instructions into every detected agent's settings. The
script installs to `~/.local/bin` by default; add `--dir=<path>` for another
location.

`codebase-memory-mcp update` does not update anything. It prints the path of
an `install.sh` beside the binary, and that file may not exist. Use the
command above.

Installed through npm? Update with `npm install -g codebase-memory-mcp@latest`.

Do NOT run `codebase-memory-mcp install`, even though the upstream README
lists it: it rewrites every detected agent's settings and rebuilds every
index. The CLI works without it.

## After installing or updating

1. Confirm the new version: `codebase-memory-mcp --version`.
2. Read the release notes before the first query:
   `gh release view -R DeusData/codebase-memory-mcp`. A minor version
   (0.10 to 0.11) can change the index format, which forces one full reindex,
   and can change the CLI output format.
3. Run the wrapper tests. If they fail, the CLI contract changed and
   `scripts/cbm` needs an update before agents rely on it:

   ```bash
   python3 -m unittest discover -s <skilldir>/scripts -p 'test_*.py'
   ```

4. Index the repo per the "Project name" section of SKILL.md.
