# Installing codebase-memory-mcp

Ask the user before installing anything. State which command you intend to
run and wait for a yes. Do not install on silence.

Install instructions live in the upstream README:
https://github.com/DeusData/codebase-memory-mcp#installation

Options:

- `npm install -g codebase-memory-mcp` (needs Node 18+; the postinstall
  downloads a static binary for the host platform from GitHub Releases)
- Download the release binary for the platform from
  https://github.com/DeusData/codebase-memory-mcp/releases/latest and put it
  on `PATH` as `codebase-memory-mcp`. No Node needed.

`scripts/cbm` also needs `jq` on `PATH`.

Stop after the install. Do NOT run `codebase-memory-mcp install`, even
though the upstream README lists it as the next step: it rewrites every
detected agent's settings and rebuilds every index. The CLI works without it.

After installing, confirm the binary is on `PATH`:

```bash
codebase-memory-mcp --version
```

Then index the repo per the "Project name" section of SKILL.md.
