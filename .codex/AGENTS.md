# Standing rules for Codex here

Codex run as delegated worker for a Claude Code orchestrator. Brief rule scope.
This file rule HOW, and bind even when brief not repeat it.

## Read before writing code

Skills = single source of truth. Load the ones that apply before writing code.
Not from memory. Never cite a filesystem path for them; name the skill.

| When | Load |
| --- | --- |
| Always, any language | `code-quality` skill |
| Python, GDScript, C#, TypeScript, Godot | that language's reference inside the `code-quality` skill |
| Writing report back, or any reply a human reads | `unslop` skill |

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

- `VERIFIED`, you executed it and read output
- `REASONED`, you read code and concluded it
- `ASSUMED`, untested

Never silently upgrade label. "Should work" != "works". Ran a build or test ->
quote real output. Could not verify -> say so.

## Boundaries

- Commit, push, open PR only when brief say to.
- Secrets, credential files, repo-excluded paths: hands off.
- Report changes as file paths so orchestrator can read the diff.
