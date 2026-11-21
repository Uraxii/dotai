---
name: update
description: Updates the ox-vibesec plugin and the OX VibeSec hook code that it runs, then removes the duplicate hooks that the OX installer adds and verifies the result. Use when the user asks to update OX, update VibeSec, upgrade the ox plugin, re-run the OX installer, or says that OX is out of date.
metadata:
  author: Uraxii
  homepage: https://github.com/Uraxii/dotai
---

# Update OX VibeSec

There are two parts to update. They update in different ways.

- **A. The plugin.** This is the launcher, `hooks/hooks.json`, the commands, and this skill. The marketplace updates it.
- **B. The OX hook code.** This is `~/.claude/hooks/ox_mind.js`, `~/.claude/hooks/ox_updater.js`, and the node runtime under `~/.ox/node/`. The plugin does not contain this code. The OX installer writes it.

In plugin mode, OX turns off its hourly self-updater. The hook skips the updater when `CLAUDE_PLUGIN_ROOT` is set. Thus part B changes only when the installer runs again.

The security guidelines do not need an update. The hook gets them from the OX API on each prompt.

## 1. Choose the parts

If the user names one part, update only that part. If not, update both parts. Do part A first.

To see the installed OX version, run `/ox-vibesec:status`. Read the `OX VibeSec version` and `Node runtime` lines.

## 2. Update the plugin (part A)

Run these two commands.

```bash
claude plugin marketplace update Uraxii
```

```bash
claude plugin update ox-vibesec@Uraxii
```

Inside Claude Code, `/plugin` does the same. The change applies in a new session.

## 3. Run the OX installer again (part B)

Each Bash tool call starts a new shell. Variables do not persist between calls. Thus run each code block below as one Bash call.

This command downloads the script into a new empty directory and runs it for Claude Code. The installer uses the saved credentials again, so it does not need a token.

```bash
d=$(mktemp -d) && wget -qO "$d/install.sh" https://ox-vibesec.s3.eu-west-1.amazonaws.com/vibesec-installation/install.sh && bash "$d/install.sh" --ide claude
```

On macOS, download with `curl -fsSL -o "$d/install.sh" <url>`.

Set the Bash tool timeout to 600000 ms. If the OAuth tokens are expired, the installer waits up to 10 minutes for a browser sign-in. The default timeout is 2 minutes. You can also give the command to the user to run.

### Change the token

Do this only if the user wants a new token, or if no saved credentials exist. Do not ask for the token in the chat. Do not keep the token in a variable. Do not print the token. Do not write the token to a file. Send the token on stdin, directly from the place where the user keeps secrets.

```bash
d=$(mktemp -d) && wget -qO "$d/install.sh" https://ox-vibesec.s3.eu-west-1.amazonaws.com/vibesec-installation/install.sh && <command that prints the token> | bash "$d/install.sh" --token-stdin --ide claude
```

Replace the placeholder with the command that prints the user's token from their secret store. If you do not have such a command, give the command to the user to run. `--token-stdin` does not work with `curl ... | bash`, because the script must be on disk.

Options:

- `--ide claude` sets up Claude Code only. To also update the hooks for Cursor, Kiro, Codex, and Copilot, remove `--ide claude`. Step 4 cleans only Claude Code.
- `--proxy http://host:port` sends the downloads and the bootstrap run through a proxy. Only `http://` URLs work.

For more, see the OX docs at https://docs.ox.security/vibesec/installing-vibesec and https://docs.ox.security/vibesec/installing-vibesec/installing-vibesec-on-a-single-device-using-token.md.

## 4. Remove the duplicate wiring (after part B)

The installer adds its own wiring again. Each hook then runs two times. Do this step each time the installer runs.

**Do not run the OX uninstaller.** Do not delete `~/.claude/hooks/ox_mind.js`, `~/.ox/`, `~/.claude/.ox.json`, or `~/.claude/.ox/`. The plugin needs them.

The installer adds five hooks to `~/.claude/settings.json`: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, and PostToolUseFailure. Each hook command contains `ox_mind.js`. This command makes a backup, removes only those hooks, and removes matcher groups and events that become empty. It keeps all other keys. It writes the file only if the new JSON is valid. It writes into the file in place, so a symlink and the file mode stay the same. It also removes matcher groups that have no `hooks` key.

```bash
f="$HOME/.claude/settings.json"; cp "$f" "$f.bak.$(date +%Y%m%d%H%M%S)" && (trap 'rm -f "$f.new"' EXIT; jq 'if .hooks then .hooks |= (map_values(map((.hooks = ((.hooks // []) | map(select((.command // "") | contains("ox_mind.js") | not)))) | select(.hooks != []))) | with_entries(select(.value != []))) else . end' "$f" > "$f.new" && jq -e . "$f.new" > /dev/null && cat "$f.new" > "$f")
```

Delete the two commands that the installer adds. The plugin gives `/ox-vibesec:status`, `/ox-vibesec:login-oauth`, and `/ox-vibesec:login-api-key` in their place.

```bash
rm -f "$HOME/.claude/commands/ox-vibesec-status.md" "$HOME/.claude/commands/ox-vibesec-login.md"
```

## 5. Verify

1. Run this command. It must print `clean`.

   ```bash
   ! grep -q ox_mind "$HOME/.claude/settings.json" && echo clean
   ```

2. Tell the user to start a new session, so that Claude Code loads the hooks again.
3. In the new session, run `/ox-vibesec:status`. Make sure that it shows `ACTIVE`, valid authentication, `Hooks registered` set to yes, and the new `OX VibeSec version`.
