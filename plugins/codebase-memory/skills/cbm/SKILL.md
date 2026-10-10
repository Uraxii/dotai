---
name: cbm
description: "Answer code questions from the codebase-memory graph instead of grepping and reading files one by one. Use before grep, rg, find, or opening several files to understand code: \"where is X\", \"who calls X\", \"what breaks if I change X\", how modules fit together, data flow, dead code, or a symbol's source. Indexes the repo first when it isn't indexed yet."
---

# codebase-memory CLI

One tool per process. JSON arguments in on stdin. Read tools answer on stdout in a compact text tree; add `"format":"json"` to the arguments to get JSON. `index_repository` and `delete_project` answer in JSON. Errors go to stderr with exit 1.

```bash
echo '<json>' | codebase-memory-mcp cli --quiet <tool>
scripts/cbm <tool> ['<json>']   # same, JSON pretty-printed, text passed through, json defaults to {}
alias cbm=<skilldir>/scripts/cbm   # skilldir = directory holding this SKILL.md; examples below assume this
```

## Project name

Every tool but `list_projects`, `index_repository`, and `compare_graphs` requires `project`. The name is the repo root path with `/` turned into `-` and the leading slash dropped:
`/workspace/Projects/myapp` -> `workspace-Projects-myapp`. Confirm with:

```bash
cbm list_projects   # each row pairs a name with its root_path
```

Not listed -> index first: `cbm index_repository '{"repo_path":"/abs/path","mode":"fast"}'` (`full` adds similarity edges, slower). Nothing indexes a linked worktree for you, so index the one you work in on first use.

Listed -> check freshness before trusting it. Run `cbm detect_changes '{"project":"P"}'`. If it reports changed files, or snippet line numbers disagree with the file, re-run `index_repository` for that repo, then query.

## Workflows (P = project name)

```bash
# 1. Architecture overview: node/edge counts, packages, Leiden clusters (de-facto modules)
cbm get_architecture '{"project":"P"}'

# 2. Find a symbol (BM25 query, or name_pattern regex). Returns qualified_name for later calls
cbm search_graph '{"project":"P","name_pattern":".*init.*","label":"Function","limit":3}'

# 3. Who calls X / what does X call (direction inbound|outbound|both; mode calls|data_flow|cross_service)
cbm trace_path '{"project":"P","function_name":"init_db","direction":"inbound","depth":2}'

# 4. Read source by qualified_name (from step 2)
cbm get_code_snippet '{"project":"P","qualified_name":"P.app.storage.init_db"}'

# 4b. Declarations in one file, in source order (file_path relative to the repo root)
cbm get_file_outline '{"project":"P","file_path":"app/storage.py"}'

# 5. Graph-ranked grep. Arg is `pattern`, NOT `query`. Literal match unless you add "regex":true
cbm search_code '{"project":"P","pattern":"TODO","limit":3}'

# 6. Dead code: functions nobody calls, entry points excluded
cbm search_graph '{"project":"P","label":"Function","max_degree":0,"exclude_entry_points":true,"limit":20}'

# 7. Impact of uncommitted / recent changes (since: git ref or date)
cbm detect_changes '{"project":"P"}'

# 8. ADR: mode outline (default)|get|sections|update|set_sections. update replaces the whole doc from markdown `content`
#    (## PURPOSE/STACK/ARCHITECTURE/PATTERNS/TRADEOFFS/PHILOSOPHY); set_sections takes `section_updates` {heading: body}
cbm manage_adr '{"project":"P","mode":"get"}'
```

Cypher for anything else: `cbm query_graph '{"project":"P","query":"MATCH (f:Function) WHERE f.in_degree = 0 RETURN f.qualified_name LIMIT 20"}'`. Labels and properties: `cbm get_graph_schema '{"project":"P"}'`.

## Gotchas

- Read tools answer in a text tree by default, not JSON. Add `"format":"json"` to the arguments when a script needs to parse the answer.
- `search_code` wants `pattern` (else "pattern is required"); `search_graph` wants `query` or `name_pattern` and silently returns every node if given `pattern`.
- `manage_adr` rejects an unknown mode ("invalid mode", exit 1). With no mode it outlines headings; pass `"mode":"get"` for the text.
- Cypher subset: `NOT f.is_test` fails ("unexpected operator"). Write `f.is_test = false`.
- Each call takes ~7s, even `list_projects`: the CLI starts a temporary daemon every time. `codebase-memory-mcp daemon start` keeps one warm and cuts that to ~2.5s, but it is a permanent background process that also serves a web UI on a local port. Ask the user before starting it; `codebase-memory-mcp daemon stop` retires it.
- `get_architecture.languages` omits GDScript (a Godot repo reports Bash/YAML). The .gd symbols are indexed; trust `node_labels`.
- Repos containing nested git worktrees get those indexed too (qualified names under `worktrees.*`). Filter with `file_pattern`, a glob anchored at the repo root: `"file_pattern":"src/**"` excludes them, `"*.gd"` does not.
- Never run `codebase-memory-mcp install` to "fix" things: it rebuilds every index and writes hooks into user settings.
- If a call fails with `command not found`, or the wrapper tests fail, follow `references/SETUP.md` to install or update to the latest release, then rerun `codebase-memory-mcp --version` before retrying.
- Snippet line numbers not matching the file = stale index. `detect_changes` can still say 0 changed (observed on an indexed repo). Re-run `index_repository` on that repo.
- Under `codex -s workspace-write` every call fails with `socket_bind failed with EPERM` or `could not accept this client`: the sandbox blocks the unix socket the CLI uses to reach its daemon, whatever the socket directory (`CBM_RUNTIME_DIR` does not help). Start Codex with `-c sandbox_workspace_write.network_access=true`, or set it under `[sandbox_workspace_write]` in `~/.codex/config.toml`.
- `delete_project`, `index_repository`, and `manage_adr` `update`/`set_sections` write. Everything else is read-only; `ingest_traces` only validates and counts.

Full arg table for all 17 tools: `references/tools.md`. Regenerate `references/tools.json` after a binary upgrade with `python3 scripts/dump_schemas.py`.
