# Models

You define models here. Edit by hand or through `setup-models`, which fills rows from what your harness can pin. One row per label, an ordered preference list; the spawner uses the first name its harness accepts. Absent row -> omit model, child inherits. Panel rows spawn one agent per entry. `fable`, `sol`, `luna` never written without explicit user permission.

feature, refactoring: claude-sonnet-5, gpt-5.5, gpt-5.4, claude-opus-5
judgment and prose: claude-opus-5, gpt-5.5, claude-sonnet-5, gpt-5.4
arena runners: claude-opus-5, claude-sonnet-5, gpt-5.5
arena cross-judge pool: claude-opus-5, gpt-5.5, claude-sonnet-5
interrogate reviewers: claude-opus-5, gpt-5.5, claude-sonnet-5
swarm workers: claude-sonnet-5, gpt-5.5, gpt-5.4-mini

One list per row serve every harness. A spawner walk the list and take the first name its harness can pin, skipping the rest. `claude-*` are Copilot CLI slugs, `gpt-*` are Codex and Copilot. A harness alias that name the same model count as pinnable (`claude-opus-5` -> `opus`, `claude-sonnet-5` -> `sonnet` on harnesses that only take aliases).

Panel rows spawn one agent per *pinnable* entry, so a panel mix Claude and GPT wherever the harness offer both.

`feature, refactoring` covers implementation, tests, lookups; `judgment and prose` covers orchestration, architecture, review, research, docs. Names a harness cannot pin are skipped, not errors.
