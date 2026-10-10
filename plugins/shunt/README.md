# shunt

Shunt saves main-agent context tokens by sending large reads to a small,
fast subagent. The reader returns a short answer with file and line citations.
Boilerplate generation still uses Portal AiKA through code-writer.

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

## Prerequisites

Reads need Bash and [jq](https://jqlang.org), plus the harness's subagent tools
when available. No Portal CLI, Portal authentication, or AiKA reader mode is
needed.

### Portal setup for code-writer only

Install Spotify's Portal plugin, then authenticate in a new session:

```bash
claude plugin marketplace add spotify/portal-ai-plugins
claude plugin install portal@portal
```

```text
/portal:setup
```

Check whether the `code-writer` AiKA mode exists:

```bash
portal-cli actions aika:list-modes --json --input '{"search": "code-writer"}'
```

If needed, create it:

```bash
portal-cli actions aika:create-mode --input '{
  "name": "code-writer",
  "description": "Boilerplate code generator",
  "instructions": "Generate code from the spec and reference. Match existing patterns, conventions, naming, and style. Output only code, without explanations or markdown fences.",
  "tags": ["coding", "delegation"],
  "resource_limits": { "temperature": 0.2 }
}'
```

Mode names resolve server-side, preferring your own mode, then your groups',
then public modes. Pin `SHUNT_CODE_WRITER_MODE_ID` when a name is ambiguous.

## Code generation

[code-writer](skills/code-writer/SKILL.md) calls `scripts/code-write`.
`--reference` is required so generated code matches the project's patterns.
The script strips markdown fences and optionally writes to `--target`.
Each Portal invocation is one shot; follow up by referencing its output.

```bash
plugins/shunt/scripts/code-write --spec "Write UserService tests" \
  --reference tests/OrderTest.java --target tests/UserTest.java
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SHUNT_MIN_LINES` | `350` | Read threshold and suggested chunk size |
| `SHUNT_PORTAL_INSTANCE` | CLI default | Code-writer Portal instance |
| `PORTAL_CLI_BIN` | `portal-cli`, else `npx` | Code-writer CLI override |
| `SHUNT_MAX_PAYLOAD_BYTES` | `120000` on Linux, `400000` elsewhere | Code-writer request ceiling |
| `SHUNT_TIMEOUT_SECONDS` | `180` | Code-writer invocation timeout |
| `SHUNT_CODE_WRITER_MODE_ID` | Unset | Code-writer mode pin |

## Hooks and limitations

`hooks/check-file-size` covers Claude Read and Copilot view.
`hooks/check-bash-read` covers Claude and Codex Bash and Copilot bash for
`cat`, `head`, `tail`, `less`, and `more`. Small files, missing files, targeted
reads, pipes, and redirections pass through without granting permissions.
These hooks guide cooperative agents; existing offset-only reads,
`view_range [1, -1]`, and the `head -n 5` parser gap remain unchanged.

Code-writer has no hook enforcement. Debugging, editing, and architectural
judgment stay with the main agent; the reader supplies evidence as needed.
Portal payload and invocation timeout limits apply only to code-writer.
Read delegation saves main-agent context; it still consumes reader tokens.
The upstream 82–94% AiKA read benchmarks do not measure this subagent path.

## Evals

```bash
bash plugins/shunt/evals/run.sh
python3 scripts/generate-plugin-manifests.py --check
```

The default suite checks hook routing, six deny-reason scenarios, chunk
continuation, and code-writer transport against a stub. No Portal access is
needed. `--benchmark` also runs the retained code-writer estimate and requires
Portal auth. [evals/evals.json](evals/evals.json) describes live skill checks.

Bead dotai-4cy's close reason records the live Claude and Copilot checks,
including subagent hook continuation.
