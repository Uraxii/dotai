# ox-vibesec

This plugin connects the OX Security VibeSec hooks to Claude Code. It adds the
hooks for five events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
and PostToolUseFailure. It also adds three commands: `/ox-vibesec:status`,
`/ox-vibesec:login-oauth`, and `/ox-vibesec:login-api-key`.

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
