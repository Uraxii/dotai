# Check plugin loading

Use a copy of the candidate and a temporary profile for each target.
Keep the installed user profile and its rules unchanged.
Select flags from the installed CLI's help before a session starts.

## Check the package first

Run these checks from the repository root.

```bash
python3 scripts/generate-plugin-manifests.py --check
python3 -m unittest discover -s plugins/pstack/hooks/tests
python3 -m unittest discover -s plugins/pstack/skills/poteto-mode/scripts/tests
```

The generator must return 0. The tests must pass.
Run the generator again and require no changes.
These checks prove package contracts. A real session must also receive context.

## Load the candidate

Set a temporary `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, or `COPILOT_HOME` for its target.
For Copilot, also set a temporary `COPILOT_CACHE_HOME`.
Register the candidate marketplace with that CLI's marketplace command.
Install pstack from that marketplace. Check its name and version.
Do not install main and use its result as evidence for another branch.

For a local Codex candidate, use one local marketplace entry.
Its source has this shape.

```json
{
  "source": "local",
  "path": "./plugins/pstack"
}
```

The path is relative to the marketplace root.
Keep the entry's installation policy, authentication policy, and category.
See [OpenAI's plugin packaging documentation](https://developers.openai.com/plugins/build/plugins).

Keep the root `plugin.json` present without `$schema`.
To check metadata precedence, change only the copied root manifest's version.
Install into a new temporary profile and record the selected version.
Compare it with both copied manifests. Restore the copied version after the probe.
A cache from an earlier install cannot prove precedence.

Check a copied Git marketplace install as well as a local live install.
Record whether the CLI reports an installed copy or a live source.
Compare the installed component files with the candidate.

## Check session behavior

Record each target's installed version and the exact session command.
Use only model names accepted by that target.

- Resolve poteto-mode and the deslop skill from the installed candidate.
- Start each shared agent where named agents are supported.
- Verify actual context delivery from the candidate session hook.
- Check a configured unavailable model and the existing role fallback.
- Use a supplied project transcript or digest. Also check missing evidence.
- Generate a verification skill in a supported project directory.
- Prove its discovery and run Launch, Doctor, Drive, Evidence, and Cleanup.
- Confirm that evidence remains after Cleanup.

poteto-mode permits model invocation so the session reminder can load it.
Other skills keep their explicit invocation settings.
Use the mappings in [Platform adaptation](../skills/poteto-mode/references/platform-adaptation.md).

A unique marker in the copied reminder can prove its source.
Check that marker in the session's actual context or hook receipt.
Remove the marker from the copied plugin after the probe.
Do not substitute a model's unsupported claim for a tool receipt.

A skill count does not prove agent execution.
A hook subprocess result does not prove context delivery.
A digest cannot certify tool calls that it does not record.

## Record limits and hand off

Record authentication, runner, and permission failures with the exact command.
Leave the affected acceptance case open. Do not report target support for it.
Keep the record outside committed product files.

A fresh reviewer checks the full patch and each checklist row.
The writer supplies receipts and does not supply its own review pass.
After integration, run the manifest check on the integrated branch too.
