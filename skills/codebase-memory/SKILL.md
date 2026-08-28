---
name: codebase-memory
description: Query the codebase-memory code-intelligence graph from a shell via `codebase-memory-mcp cli`, no MCP server needed. Use for structural code questions on an indexed repo - who calls what, dependency and data-flow tracing, impact of a change, architecture overview and module clusters, dead code (zero-caller functions), reading a symbol's source by qualified name, ADR read/write, Cypher over the code graph. Also use when an agent or shell script lacks the MCP tools but the binary is on PATH.
---

# codebase-memory CLI

One tool per process. JSON in, JSON out on stdout, one `level=info msg=mem.init` line on stderr.

```bash
codebase-memory-mcp cli <tool> '<json>' 2>/dev/null
scripts/cbm <tool> ['<json>']   # same, init line dropped, jq-pretty, json defaults to {}
alias cbm=<skilldir>/scripts/cbm   # skilldir = directory holding this SKILL.md; examples below assume this
```

## Project name

Every tool but `list_projects` and `index_repository` requires `project`. The name is the repo root path with `/` turned into `-` and the leading slash dropped:
`/var/home/nicole/Projects/lodestar` -> `var-home-nicole-Projects-lodestar`. Confirm with:

```bash
cbm list_projects | jq -r '.projects[] | "\(.name)\t\(.root_path)"'
```

Not listed -> index first: `cbm index_repository '{"repo_path":"/abs/path","mode":"fast"}'` (`full` adds similarity edges, slower). Re-index only when `detect_changes` shows changed files.

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

# 5. Graph-ranked grep. Arg is `pattern`, NOT `query`
cbm search_code '{"project":"P","pattern":"TODO","limit":3}'

# 6. Dead code: functions nobody calls, entry points excluded
cbm search_graph '{"project":"P","label":"Function","max_degree":0,"exclude_entry_points":true,"limit":20}'

# 7. Impact of uncommitted / recent changes (since: git ref or date)
cbm detect_changes '{"project":"P"}'

# 8. ADR: mode get|update|sections. update takes markdown `content` with ## PURPOSE/STACK/ARCHITECTURE/PATTERNS/TRADEOFFS/PHILOSOPHY
cbm manage_adr '{"project":"P","mode":"get"}'
```

Cypher for anything else: `cbm query_graph '{"project":"P","query":"MATCH (f:Function) WHERE f.in_degree = 0 RETURN f.qualified_name LIMIT 20"}'`. Labels and properties: `cbm get_graph_schema '{"project":"P"}'`.

## Gotchas

- `search_code` wants `pattern` (else "pattern is required"); `search_graph` wants `query` or `name_pattern` and silently returns every node if given `pattern`.
- README examples omit `project` and name `trace_call_path`. Real tool is `trace_path`, and `project` is required.
- `manage_adr` modes are `get|update|sections`; unknown modes fall through to `get`.
- Cypher subset: `NOT f.is_test` fails ("unexpected operator"). Write `f.is_test = false`.
- Cold start ~0.1s per call; on a 60k-node DB the heavy tools (get_architecture, search_code, get_graph_schema) take 0.7-1.3s.
- `get_architecture.languages` omits GDScript (fps-mp-test reports Bash/YAML). The .gd symbols are indexed; trust `node_labels`.
- Repos containing nested git worktrees get those indexed too (qualified names under `worktrees.*`). Filter with `file_pattern`, a glob anchored at the repo root: `"file_pattern":"src/**"` excludes them, `"*.gd"` does not.
- Never run `codebase-memory-mcp install` to "fix" things: it rebuilds every index and writes hooks into user settings.
- Snippet line numbers not matching the file = stale index. `detect_changes` can still say 0 changed (seen on lodestar). Re-run `index_repository` on that repo.
- `delete_project`, `index_repository`, `manage_adr update`, `ingest_traces` write. Everything else is read-only.

Full arg table for all 14 tools: `references/tools.md`. Regenerate `references/tools.json` after a binary upgrade with `bash scripts/dump-schemas.sh`.
