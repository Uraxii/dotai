---
name: setup
description: "User invokes by name to install this repo's skills, agents, and harness config into the harness dirs under $HOME. Deploys by copy, tracks a manifest, prunes stale files. Use when user say install, deploy, sync, set up dotai, push skills to harnesses, or after moving/renaming/deleting skill in repo."
---

# Setup

Deploy repo -> `$HOME`. Copies, never symlinks. Script is lever; you drive it.

Script: `<repo>/skills/setup/scripts/install.sh`
Repo root = script's own repo unless `--repo` given.

## Steps

### 1. Detect

Which harness dirs exist:

```sh
for d in ~/.claude ~/.agents ~/.codex ~/.copilot ~/.config/opencode ~/.hermes; do
  [ -d "$d" ] && echo "present: $d"
done
```

Map dir -> mode: `~/.claude`=claude, `~/.agents`+`~/.codex`=codex,
`~/.copilot`=copilot, `~/.config/opencode`=opencode, `~/.hermes`=hermes.

### 2. Ask mode

Ask user which mode. Default = all detected. Use harness's structured
question prompt if it have one, else plain question. Options: each detected
mode, plus `all`.

### 3. Dry run first

```sh
bash <repo>/skills/setup/scripts/install.sh --harness <mode> --dry-run --prune
```

Show user summary lines (one per harness: written / pruned / skipped). Also
surface any `unlink-dir` line: that is old symlink deploy getting replaced by
real dir. Big prune count or surprise unlink -> stop, ask.

### 4. Run real

```sh
bash <repo>/skills/setup/scripts/install.sh --harness <mode> --prune
```

`--prune` deletes only files listed in previous manifest and absent now.
Manifest lives at `<target-root>/.dotai-manifest`. Files script never wrote
are never touched.

### 5. Verify

Count + frontmatter parse:

```sh
for d in ~/.claude/skills ~/.agents/skills ~/.copilot/skills \
         ~/.config/opencode/skills ~/.hermes/skills; do
  [ -d "$d" ] && echo "$d $(find "$d" -name SKILL.md | wc -l) skills"
done
find ~/.claude/skills -name SKILL.md | while read -r f; do
  { head -1 "$f" | grep -qx -- '---'; } && grep -qm1 '^name:' "$f" \
    && grep -qm1 '^description:' "$f" || echo "BAD $f"
done
```

Repo count must match target count. Any `BAD` line -> broken frontmatter,
fix in repo, rerun.

### 6. Post steps per harness

- claude: nothing. Reads `~/.claude/skills` and `~/.claude/agents` live.
- codex: nothing. Reads `~/.agents/skills` natively.
- copilot: nothing.
- opencode: nothing.
- hermes: no `external_dirs` config needed. Skills copied straight into
  `~/.hermes/skills`.

### 7. Offer setup-models

Ask if user want to run `setup-models` to repin per-role models. Only offer,
never auto-run.

## Bootstrap

Fresh machine, no agent, no skills installed yet:

```sh
bash <repo>/skills/setup/scripts/install.sh --harness all
```

Script standalone. Needs bash, find, cmp, comm, sort. Nothing else.

## What lands where

| mode | source | destination |
|---|---|---|
| claude | `skills/*` | `~/.claude/skills/` |
| claude | `agents/*` | `~/.claude/agents/` |
| codex | `skills/*` | `~/.agents/skills/` |
| codex | `harness/codex/*` | `~/.codex/` |
| copilot | `skills/*` | `~/.copilot/skills/` |
| copilot | `harness/copilot/*` | `~/.copilot/` |
| opencode | `skills/*` | `~/.config/opencode/skills/` |
| opencode | `harness/opencode/*` | `~/.config/opencode/` |
| hermes | `skills/*` | `~/.hermes/skills/` |
| hermes | `harness/hermes/*` | `~/.hermes/` |

Excluded always: `__pycache__`, `.pytest_cache`, `.ruff_cache`, `*.pyc`,
`.git`.

Existing symlink at destination (old stow deploy, maybe dangling) -> removed,
real copy written. Symlinked parent dir -> removed, real dir made.

Idempotent. Second run writes nothing, reports everything skipped.
