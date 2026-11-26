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

The host must set `PLUGIN_ROOT`, `DEVIN_PLUGIN_ROOT`, or `CLAUDE_PLUGIN_ROOT`
to the plugin directory. Alternatively, make `bin/ox-vibesec-hook` available on `PATH`.

The adapter reads `OX_VIBESEC_API_KEY` and skips OX calls when the key is
absent. It verifies the installer checksum before it installs the OX runtime.
`OX_VIBESEC_INSTALLER` can specify a local installer file. If the file is missing, the adapter warns and downloads the installer.
It does not install Claude Code or change the user's Claude configuration.
The runtime is separate from the OX MCP.

The adapter requires Python 3 and Bash. It uses curl to download the installer.
On restricted networks, allow HTTPS access to these hosts:

- `ox-vibesec.s3.eu-west-1.amazonaws.com` for the installer and bootstrap
- `nodejs.org` for the Node.js runtime
- `api.cloud.ox.security` for the OX API

Devin forwards prompts, shell calls and results, and supported file changes
from `edit`, `write`, and `apply_patch`. Patches forward added file content
and update hunks, not standalone file deletions. The adapter does not forward
transcripts or apply OX's suggested tool rewrites. Only enable it where your
organization permits OX to receive this data. These hooks fail open and are not
an enforcement boundary.

## Other harnesses

`hooks/ox` is the common launcher for the OX hook. The Python runtime in
`bin/vibesec.py` manages an isolated installation and invokes that launcher.
To add a harness, register its lifecycle hooks and translate its event and
response formats in an adapter like `bin/hook.py`. Use a private runtime
home for that harness. Claude Code continues to use the vendor payload
directly and does not need Python.
