# dotai

Stow-managed repo for every AI-harness config on this machine: Claude Code,
Codex, Hermes, opencode, GitHub Copilot CLI. Split out of `dotfiles`, which
now keeps only system/shell/desktop config (it still owns
`~/.claude/{hooks,themes,statusline.sh}`, see below). LOCAL ONLY, no remote.

## Layout

The repo root mirrors `$HOME`, so the whole repo is one stow package.

| Dir                 | Deploys to             |
|---------------------|------------------------|
| `.claude/`          | `~/.claude` (skills source of truth) |
| `.agents/skills`    | `~/.agents/skills` -> `.claude/skills`; read natively by codex, copilot, opencode |
| `.codex/`           | `~/.codex` (allowlist) |
| `.hermes/`          | `~/.hermes`            |
| `.config/opencode/` | `~/.config/opencode`   |
| `.copilot/`         | `~/.copilot`           |

One `.stow-local-ignore` at the root covers every harness.

Hermes needs one config line to see the shared skills (`~/.hermes/config.yaml`):

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

## Usage

```
cd ~/dotai
stow -t ~ --no-folding .
```

Add `-R` to restow after a rename, `-n -v1` to preview, `-D` to remove.
After a restow, prune links whose source moved:
`find ~/.claude ~/.codex ~/.hermes ~/.config/opencode ~/.copilot -xtype l -delete`.
`--no-folding` links files, never dirs, so live runtime state (copilot's sqlite
store, codex sessions) sits beside the links untouched.

Adding another harness later is one more `$HOME`-shaped dir at the root.

## The `.codex` allowlist

`~/.codex` is ~155M of live runtime (sessions, caches, sqlite state,
`auth.json` OAuth credentials). `.gitignore` ignores `.codex/*` wholesale and
un-ignores only `AGENTS.md`, `rules/`, `schemas/`, `skills/`. Within
`skills/`, `skills/.system/` (imagegen, openai-docs, plugin-creator,
review-agent, skill-creator, skill-installer) is vendor-managed; the Codex
CLI regenerates it on upgrade, so tracking it would be permanent churn. It
stays live and untracked by design, same as `~/.claude/skills/krita`.

## Deliberately gitignored

- `~/.claude/settings.json` and `settings.local.json` are gitignored. A
  fresh machine must recreate `~/.claude/settings.json` by hand; it's not
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
under `~/.hermes/skills/`, of which only `caveman` and
`productivity/session-transfer` come from this repo. The dotai `hermes`
package deploys exactly 19 leaf symlinks into that directory; nothing
outside those 19 leaves is ever touched by stow or this repo.
