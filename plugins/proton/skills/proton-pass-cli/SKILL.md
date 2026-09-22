---
name: proton-pass-cli
description: Retrieve a stored credential (an API key, a gateway token, a password, an SSH key) from Proton Pass with the pass-cli tool, authenticating with a Personal Access Token held in the OS keyring. Use whenever a task needs a secret that lives in Proton Pass, before starting any tool or service that reads such a secret, or to log in somewhere with a stored password. Covers session bootstrap, authenticated reads with a mandatory access reason, and auto-recovery from an expired session.
---

# proton-pass-cli

Auth is a Personal Access Token (PAT) stored in the OS keyring (secret-service / KWallet), never in a file, never in this repo. Requires `pass-cli` and `secret-tool` (libsecret) with an active provider (ksecretd/kwalletd or gnome-keyring).

The caller must have `PASS_VAULT_NAME` and `PASS_PAT_KEYRING_ACCOUNT` exported.

```bash
export PROTON_PASS_SESSION_DIR="/tmp/pass-agent-$USER"   # same value for every command in the task
PROTON_PASS_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service proton-pass-cli account "$PASS_PAT_KEYRING_ACCOUNT")"
```

An empty lookup means no PAT is stored yet: `printf '%s' 'PASTE_PAT_HERE' | secret-tool store --label="Proton Pass CLI PAT" service proton-pass-cli account "$PASS_PAT_KEYRING_ACCOUNT"`. Rotating the PAT is re-running that store command.

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
pass-cli info || { pass-cli logout --force 2>/dev/null; PROTON_PASS_PERSONAL_ACCESS_TOKEN="$(secret-tool lookup service proton-pass-cli account "$PASS_PAT_KEYRING_ACCOUNT")" pass-cli login; }
PROTON_PASS_AGENT_REASON="start the service that needs this credential" pass-cli item view --vault-name "$PASS_VAULT_NAME" --item-title "ITEM_TITLE" --field api-key
```

## Gotchas

- Check `pass-cli info` before real work every time; the session can expire mid-task.
- Any command failing with an auth error or non-zero exit: `pass-cli logout --force`, log in again, `pass-cli info` to confirm, retry.
- The current PAT is scoped to the vault named by `PASS_VAULT_NAME` (Owner).
- Never write the PAT or any retrieved secret to a file, tracked path, or log. Read into a shell variable, use it, let it fall out of scope.
- Prefer `--field` over whole-item reads, least exposure.
- Give a truthful, specific `PROTON_PASS_AGENT_REASON` every time.

Full docs: <https://protonpass.github.io/pass-cli/>
