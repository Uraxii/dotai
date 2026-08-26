# dotai

Stow-managed repo for every AI-harness config on this machine: Claude Code,
Codex, Hermes, opencode, GitHub Copilot CLI. Split out of `dotfiles`, which
now keeps only system/shell/desktop config (it still owns
`~/.claude/{hooks,themes,statusline.sh}` — see below). LOCAL ONLY, no remote.

## Packages

| Package    | Deploy target         | Mechanism                      |
|------------|------------------------|---------------------------------|
| `.claude`  | `~/.claude`             | `stow --no-folding`            |
| `.codex`   | `~/.codex`               | `stow --no-folding` (allowlist)|
| `.hermes`  | `~/.hermes`              | `stow --no-folding`            |
| `opencode` | `~/.config/opencode`     | `stow --no-folding`            |
| `copilot`  | `~/.copilot`             | `copilot/install.sh` (own linker)|

## Usage

```
./setup.sh
```

Forwards extra args to stow (`-R` to restow, `-n` to preview) for every
package except `copilot`, which owns its own idempotent installer.

Adding another harness later (e.g. `pi` — already has a `[pi]` entry under
`deps.toml`'s `groups.ai`, but no local config yet) is one `deploy` line in
`setup.sh` plus a package directory here.

## The `.codex` allowlist

`~/.codex` is ~155M of live runtime (sessions, caches, sqlite state,
`auth.json` OAuth credentials). `.gitignore` ignores `.codex/*` wholesale and
un-ignores only `AGENTS.md`, `rules/`, `schemas/`, `skills/`. Within
`skills/`, `skills/.system/` (imagegen, openai-docs, plugin-creator,
review-agent, skill-creator, skill-installer) is vendor-managed — the Codex
CLI regenerates it on upgrade, so tracking it would be permanent churn. It
stays live and untracked by design, same as `~/.claude/skills/krita`.

## Deliberately gitignored

- `~/.claude/settings.json` and `settings.local.json` are gitignored. A
  fresh machine must recreate `~/.claude/settings.json` by hand — it's not
  in this repo.
- `~/.claude/skills/krita` stays live/untracked by design (341 files, 14M).

## agent-workbench: two sources of truth

`~/.claude/skills/agent-workbench` is tracked here AND has its own upstream
repo + installer at `/var/home/nicole/Projects/agent-workbench`. Keep them
in sync by hand; this repo does not automate that.

## `~/.hermes` is mostly not this repo

`~/.hermes` is 1.9G, almost all of it live upstream runtime:
`hermes-agent/` (1.9G), `bin/` (63M), `config.yaml`, a 74K
`config.yaml.bak.*`, `.env` (secrets), and ~20 upstream-bundled skill trees
under `~/.hermes/skills/` — of which only `caveman` and
`productivity/session-transfer` come from this repo. The dotai `.hermes`
package deploys exactly 20 leaf symlinks into that directory; nothing
outside those 20 leaves is ever touched by `setup.sh` or this repo.
