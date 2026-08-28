---
name: proton-pass-cli
description: Retrieve credentials (API keys, passwords, tokens, SSH keys) from Proton Pass via the pass-cli tool, using a Personal Access Token held in the OS keyring. Use whenever a task needs a secret that lives in Proton Pass - e.g. "get the OpenAI key", "read the litellm master key", "fetch the DB password", "log in to <service> using my stored credentials", or before running any tool/gateway that reads secrets from the MachineSecrets vault. Covers session bootstrap, authenticated reads with a mandatory access reason, and auto-recovery from an expired session.
---

# proton-pass-cli

Auth is a Personal Access Token (PAT) stored in the OS keyring (secret-service / KWallet), never in a file, never in this repo. Requires `pass-cli` and `secret-tool` (libsecret) with an active provider (ksecretd/kwalletd or gnome-keyring).

```bash
export PROTON_PASS_SESSION_DIR="/tmp/pass-agent-$USER"   # same value for every command in the task
PROTON_PASS_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service proton-pass-cli account machinesecrets-pat)"
```

Empty lookup means no PAT stored yet: `printf '%s' 'PASTE_PAT_HERE' | secret-tool store --label="Proton Pass CLI PAT (MachineSecrets)" service proton-pass-cli account machinesecrets-pat`. Rotating the PAT is re-running that store command.

## Commands

| command | needs | returns |
|---|---|---|
| `pass-cli info` | session | account type, session details (exit 0 = authenticated) |
| `pass-cli login` | `PROTON_PASS_PERSONAL_ACCESS_TOKEN` env | new session |
| `pass-cli logout --force` | | clears session |
| `pass-cli vault list` | session | vaults granted to this PAT |
| `pass-cli share list` | session | vaults + directly-shared items |
| `pass-cli item list --vault-name NAME` | session | items in a vault |
| `pass-cli item view --vault-name NAME --item-title TITLE [--field F]` | session, `PROTON_PASS_AGENT_REASON` | one item or one field |
| `pass-cli item view "pass://SHARE_ID/ITEM_ID"` | session, `PROTON_PASS_AGENT_REASON` | item by URI |
| `pass-cli test` | | API connectivity check |

`item view`, `item create*`, `item update`, `item trash`, `item untrash`, and `vault update` all require `PROTON_PASS_AGENT_REASON` naming why access is needed (audited). Add `--output json` to any list/view command when parsing programmatically.

## Example

```bash
pass-cli info || { pass-cli logout --force 2>/dev/null; PROTON_PASS_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service proton-pass-cli account machinesecrets-pat)" pass-cli login; }
PROTON_PASS_AGENT_REASON="start litellm gateway" pass-cli item view --vault-name "MachineSecrets" --item-title "openai" --field api-key
```

## Gotchas

- Check `pass-cli info` before real work every time; the session can expire mid-task.
- Any command failing with an auth error or non-zero exit: `pass-cli logout --force`, log in again, `pass-cli info` to confirm, retry.
- The current PAT is scoped to the MachineSecrets vault (Owner).
- Never write the PAT or any retrieved secret to a file, tracked path, or log. Read into a shell variable, use it, let it fall out of scope.
- Prefer `--field` over whole-item reads, least exposure.
- Give a truthful, specific `PROTON_PASS_AGENT_REASON` every time.

Full docs: <https://protonpass.github.io/pass-cli/>
