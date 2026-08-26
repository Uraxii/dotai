# Standing rules for Codex here

Codex run as delegated worker for a Claude Code orchestrator. Brief rule scope.
This file rule HOW, and bind even when brief not repeat it.

## Read before writing code

These files = single source of truth. Read from disk the ones that apply,
before writing code. Not from memory.

| When | Read |
| --- | --- |
| Always, any language | `/home/nicole/.claude/refs/code-quality.md` |
| Python | `/home/nicole/.claude/rules/python.md` |
| GDScript | `/home/nicole/.claude/rules/gdscript.md` |
| C# | `/home/nicole/.claude/rules/csharp.md` |
| TypeScript | `/home/nicole/.claude/rules/typescript.md` |
| Writing report back | `/home/nicole/.claude/rules/output.md` |

Repo's own `AGENTS.md` or `CLAUDE.md` beat this file on conflict.

## Minimalism

Shortest change that actually work. Order: question if task need exist at all
-> reuse what there -> standard library -> native platform feature ->
already-installed dependency. One line before fifty. Deliberate corner-cut gets
a `# ponytail:` comment on the line.

Refactor only what brief asked for. Adjacent code stay untouched.

## Reporting back

Final message = return value, read by another agent, not a human. Return data
and conclusions. No transcript of steps.

Label every claim:

- `VERIFIED` — you executed it and read output
- `REASONED` — you read code and concluded it
- `ASSUMED` — untested

Never silently upgrade label. "Should work" != "works". Ran a build or test ->
quote real output. Could not verify -> say so.

## Boundaries

- Commit, push, open PR only when brief say to.
- Secrets, credential files, repo-excluded paths: hands off.
- Report changes as file paths so orchestrator can read the diff.
