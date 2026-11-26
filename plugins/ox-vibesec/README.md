# ox-vibesec

## Claude Code

This plugin connects the OX Security VibeSec hooks to Claude Code. It adds the
hooks for five events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
and PostToolUseFailure. It also adds three commands: `/ox-vibesec:status`,
`/ox-vibesec:login-oauth`, and `/ox-vibesec:login-api-key`.
The `update` skill tells an agent how to update the plugin and the VibeSec hook code.

The plugin does not contain VibeSec. Run the OX installer once before you
install the plugin. The installer downloads a Node.js runtime to `~/.ox/node/`
and the hook script to `~/.claude/hooks/ox_mind.js`. The plugin finds both of
them each time a hook runs. If they are missing, the hook writes one line to
stderr and lets Claude Code continue. For the installer, see
https://docs.ox.security/vibesec/installing-vibesec.

The OX installer also writes five hook entries in `~/.claude/settings.json`.
These entries run `ox_mind.js` directly. When you install this plugin, delete
those five entries. If you do not, each hook runs two times.

When VibeSec runs as a plugin, its hourly self-updater is off. To update
VibeSec, run the OX installer again. The installer adds the five entries to
`~/.claude/settings.json` again, so delete them again.

## Devin

Install this same plugin from the `plugins/ox-vibesec` directory. Make the
personal VibeSec secret available to the hook process as `OX_VIBESEC_API_KEY`.
The adapter needs Python 3, Bash, curl, and standard Linux utilities.
It skips OX calls when the secret is absent.

At session start, the adapter installs the OX runtime into a private home
under `~/.local/state/ox-vibesec-devin/`. It sends the token on stdin.
It does not install Claude Code or touch the user's Claude configuration.
The runtime uses `ox-vibesec.s3.eu-west-1.amazonaws.com`, `nodejs.org`,
and `api.cloud.ox.security`. It is separate from the OX MCP.

No blueprint change is required. To stage the installer in a snapshot,
append this to the existing `initialize` shell block:

```bash
(
  set -euo pipefail
  ox_dir="$HOME/.local/lib/ox-vibesec-devin"
  ox_installer=$(mktemp)
  trap 'rm -f "$ox_installer"' EXIT
  curl -fsSL https://ox-vibesec.s3.eu-west-1.amazonaws.com/vibesec-installation/install.sh -o "$ox_installer"
  printf '%s  %s\n' 51f97f30518e7ff3b48a8d90b404b243896bc5d24f9d8b074d68d9846d3e1a25 "$ox_installer" | sha256sum -c -
  install -d -m 755 "$ox_dir"
  install -m 644 "$ox_installer" "$ox_dir/install.sh"
)
```

The adapter verifies the checksum with or without this step. It rejects a
staged file that fails verification. The blueprint does not use the token.

The hook commands use the runtime's plugin-root variable when set. Devin's
public documentation does not specify a root variable for native command
hooks. When none is set, the commands look for one dotai VibeSec install
in the Devin Cloud plugin cache and refuse to guess if ambiguous.

Devin forwards prompts, shell calls and results, and file edits with a
path and replacement text or content. It does not forward patch-only
edits or transcripts, or apply OX's suggested tool rewrites. Only enable
it where your organization permits OX to receive this data. Startup
can run in the background, so early events may be skipped. These hooks
fail open and are not an enforcement boundary.

## Other harnesses

`hooks/ox` is the common launcher for the OX hook. The Python runtime in
`bin/vibesec.py` manages an isolated installation and invokes that launcher.
To add a harness, register its lifecycle hooks and translate its event and
response formats in an adapter like `bin/hook.py`. Use a private runtime
home for that harness. Claude Code continues to use the vendor payload
directly and does not need Python.
