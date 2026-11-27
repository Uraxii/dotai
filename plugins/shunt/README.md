# shunt

Shunt saves main-agent context tokens by sending large reads to a small,
fast subagent. The reader returns a short answer with file and line citations.

Vendored from Spotify's [portal-ai-plugins](https://github.com/spotify/portal-ai-plugins/tree/e14bdb1dc894e0a2ef150fa811db5308ae2ddb37/plugins/shunt),
revision `e14bdb1dc894e0a2ef150fa811db5308ae2ddb37`, under Apache-2.0.
See [LICENSE.md](LICENSE.md) and [patch notes](upstream-source.md).

## Large reads

Hooks deny full reads of files over 350 lines and lead with "delegate via the
bulk-reader skill" for understanding or questions. The main agent gives the
reader paths and a specific question, without loading the file first.

Both read hooks allow full reads under an exact `.handoffs` or `handoffs`
directory so agents can read the handoff needed to resume work. The exception
runs before the size check, after resolving relative paths from the session
cwd, and requires a path without any `..` segment. `.handoffs/../big.md`,
`handoffs.txt`, and `myhandoffs/` still follow the size guard.

- Claude Code uses Agent with `subagent_type: Explore` and `model: haiku`.
- Copilot CLI uses task with `agent_type: explore` and `mode: sync`. Its built-in
  explore definition selects a fast model and read tools. Prefer
  `model: gpt-5.4-mini` when exposed by the task schema.
- Codex uses an available exploration subagent and small model. When no
  subagent mechanism is exposed, it falls back to targeted or chunked reads.
- Devin uses an available read-only subagent. If none is available, use
  targeted or chunked reads.

The reader uses the same hooks. Claude's `agent_id` switches the deny reason
straight to chunk instructions. Copilot 1.0.95's live `preToolUse` input has
`cwd`, `sessionId`, `timestamp`, `toolArgs`, and `toolName`, with no subagent
identity. Its reason tells an existing reader to use
chunks rather than delegate again. The skill includes that instruction in
all reader prompts.

For exact content, edits, or reader-subagent reads, use chunks of at most
`SHUNT_MIN_LINES` lines until the required content has been read. Claude uses
Read with `offset` and `limit`; Copilot uses view with inclusive
`view_range [start, end]`. All harnesses can use `sed -n 'START,ENDp' FILE`
or `grep` for targeted lookups. Before editing, the main agent re-reads only
the exact cited lines. See [bulk-reader](skills/bulk-reader/SKILL.md).

## Devin install

```bash
devin plugins install Uraxii/dotai#plugins/shunt
```

## Prerequisites

Reads need Bash and awk. On Windows, that is Git for Windows: Claude Code runs
the hooks with Git Bash, and Codex and Copilot reach it through
`hooks/run-hook.cmd`. Reads also need the harness's subagent tools when
available.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SHUNT_MIN_LINES` | `350` | Read threshold and suggested chunk size |

## Hooks and limitations

`hooks/check-file-size` covers Claude Read, Copilot view, and Devin read.
`hooks/check-bash-read` covers Claude and Codex Bash, Copilot bash, and Devin exec for
`cat`, `head`, `tail`, `less`, and `more`. Small files, missing files, targeted
reads, pipes, and redirections pass through without granting permissions.
These hooks guide cooperative agents; existing offset-only reads,
`view_range [1, -1]`, and the `head -n 5` parser gap remain unchanged.

Debugging, editing, and architectural judgment stay with the main agent.
The reader supplies evidence as needed.
Read delegation saves main-agent context; it still consumes reader tokens.

## Evals

```bash
bash plugins/shunt/evals/run.sh
python3 scripts/generate-plugin-manifests.py --check
```

`scripts/run-hook-tests.sh` runs these evals with every other plugin hook test.

The suite checks hook routing, deny reasons, and chunk continuation.
[evals/evals.json](evals/evals.json) describes live skill checks.

Bead dotai-4cy's close reason records the live Claude and Copilot checks,
including subagent hook continuation.
