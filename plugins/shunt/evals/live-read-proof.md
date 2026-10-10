# Close reason for dotai-4cy

Completed shunt 0.3.0. Large-read questions delegate to a small reader
subagent; exact content and edits retain chunk instructions. Claude subagents
receive chunk-only reasons via `agent_id`. Copilot's observed hook input has
no role identifier, so its shared reason explicitly lets an existing reader
continue without another delegation. Deleted the Portal bulk-read script and
read benchmarks; Portal remains required only for code-writer.

Verification passed:

- `bash plugins/shunt/evals/run.sh`: 96 passed, 0 failed.
- `python3 scripts/generate-plugin-manifests.py --check`: all 45 generated
  files are current.
- `python3 plugins/shunt/evals/verify-live-reads.py`: four checks passed for
  delegation, continuation, concise correct answers, and hook identity.
- `git diff --check`: passed.

Live Claude Code 2.1.296 session `5884ab99-a8f1-49dc-b1dd-f4e1f88c5d64`
used Agent with Explore and model haiku, resolved to `claude-haiku-5-5`.
The reader's unrestricted Read was denied with "You are the reader subagent;
do not delegate again." It continued with `sed -n '1,350p'` and
`sed -n '351,480p'`. The main agent received the short answer and verified
only the three matching lines with grep. It never received the full file.
Evidence: [Claude events](transcripts/claude-reader.jsonl) and
[hook inputs](transcripts/claude-hook-inputs.jsonl).

Live Copilot CLI 1.0.95 session `306a3114-ba7b-4340-b26d-c8f36f15422b`
denied the main agent's unrestricted view, then loaded bulk-reader and
called task with explore, sync, and `model: gpt-5.4-mini`. The reader viewed
ranges `[1,350]` and `[351,480]` and returned a concise cited answer.
The main agent never received the full file.
Evidence: [Copilot small-model events](transcripts/copilot-reader.jsonl).

Copilot session `2ea61fde-f06c-4639-bc8b-38beb2020268` separately exercised a
full view inside the built-in Explore reader (`gpt-5.6-luna`). That subagent's
own shunt denial said "If you are already the reader subagent, do not delegate
again." It continued with the same two ranges and answered correctly.
Hook input contained only cwd, sessionId, timestamp, toolArgs, and toolName.
The sessionId belongs to the reader session, but provides no role marker by
itself. No recursive task call occurred.
Evidence: [subagent-denial events](transcripts/copilot-subagent-denial.jsonl)
and [Copilot hook inputs](transcripts/copilot-hook-inputs.jsonl).

All three runs answered billing=3 at line 23, search=7 at line 239,
checkout=11 at line 467, total=21. The fixture had exactly 480 lines; all other
lines were `route-NNN: enabled=false; retries=0`.

An initial Claude run treated citation requests as exact-content reads and
loaded both chunks into the parent. The final reason explicitly assigns
citations to the reader. A later Copilot trial stopped after the first chunk;
the final skill instructs readers to cover the whole file for all/every/total
questions. The final small-model check includes an absolute path and an
explicit small-model hint. These are cooperative instructions, not a hard
guarantee that every future agent follows the skill.

## Live commands and retained evidence

The runs used isolated configuration/state directories in this worktree and
network access to the authenticated model services. Temporary hook-input
logging captured the two input files above, then was removed. The final
Copilot small-model run used the production hooks without that logging.

The Claude command was:

```bash
CLAUDE_CONFIG_DIR="$PWD/.agent-proof/claude-home" \
SHUNT_PROBE_INPUT_LOG="$PWD/.agent-proof/claude-hook-inputs.jsonl" \
claude -p --plugin-dir plugins/shunt --no-session-persistence \
  --allowedTools Read,Agent,Skill,Bash --output-format stream-json --verbose \
  --forward-subagent-text --include-hook-events \
  'Read .agent-proof/routes.txt and tell me every enabled route and its retry count, plus the sum. Cite line numbers and do not modify files. This also tests the shunt hook: have the bulk-reader subagent first attempt an unrestricted Read of this file, then follow the hook direction to finish the answer.'
```

The final Copilot command was:

```bash
COPILOT_HOME="$PWD/.agent-proof/copilot-home" \
XDG_CACHE_HOME="$PWD/.agent-proof/cache" \
copilot --plugin-dir plugins/shunt \
  -p "Use the bulk-reader skill to answer this question about $PWD/.agent-proof/routes.txt: list every enabled route, its retry count, and the sum across the whole file. Return a concise answer with line citations. Do not return file contents or modify files. Exercise the reader's hook by first attempting an unrestricted view, then continue in chunks through all 480 lines. Use the small model selected by the skill (gpt-5.4-mini is available in the task schema)." \
  --disable-builtin-mcps --no-custom-instructions --allow-tool task \
  --allow-tool view --allow-tool bash --no-ask-user \
  --log-dir .agent-proof/copilot-verified-logs \
  --share .agent-proof/copilot-verified.md
```

Retained JSONL excerpts include every tool-call start, main-agent tool results,
subagent denials, reader answers, and final answers. They omit thinking,
encrypted reasoning, usage metadata, and successful child chunk contents.
[Provenance](transcripts/provenance.json) records original transcript hashes
and Copilot session ids. Temporary state and full working transcripts were
removed before committing. The bead store was not changed.
