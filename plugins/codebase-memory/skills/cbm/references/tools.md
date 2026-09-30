# codebase-memory tools (generated from tools.json, codebase-memory-mcp 0.11.0)

Regenerate: `python3 scripts/dump_schemas.py` then rebuild this table. `project` is the name from `list_projects`.

| Tool | Purpose | Required | Optional | Example |
|---|---|---|---|---|
| `index_repository` | Index a repository | repo_path | mode, name, persistence, target_projects | `cbm index_repository '{"repo_path":"/path/repo","mode":"fast"}'` |
| `search_graph` | Find symbols via BM25 query, regex name/qn filters, or semantic_query | project | detail, exclude_entry_points, fields, file_pattern, format, include_connected, label, limit, max_degree, max_output_tokens, min_degree, name_pattern, offset, qn_pattern, query, relationship, semantic_limit, semantic_offset, semantic_query | `cbm search_graph '{"project":"P","query":"init db","label":"Function","limit":5}'` |
| `query_graph` | Read-only Cypher for multi-hop, aggregation, complexity, or cross-service analysis | query, project | cursor, format, graph, max_output_tokens, max_rows, offset | `cbm query_graph '{"project":"P","query":"MATCH (f:Function) WHERE f.in_degree = 0 RETURN f.qualified_name LIMIT 20"}'` |
| `trace_path` | Trace callers/callees, data flow, or cross-service paths | function_name, project | cursor, depth, direction, edge_types, format, include_evidence, include_tests, limit, max_output_tokens, mode, parameter_name, risk_labels | `cbm trace_path '{"project":"P","function_name":"init_db","direction":"inbound","depth":2}'` |
| `get_code_snippet` | Read a search_graph symbol | qualified_name, project | format, include_neighbors, max_lines, max_output_tokens, member_limit, member_offset, source_mode, start_line | `cbm get_code_snippet '{"project":"P","qualified_name":"P.app.storage.init_db"}'` |
| `get_file_outline` | Declaration outline of one exact repository-relative file: optional exact label filter, source order, exact total/offset/limit paging; file/folder/container nodes excluded | project, file_path | format, labels, limit, offset | `cbm get_file_outline '{"project":"P","file_path":"app/storage.py"}'` |
| `get_graph_schema` | Get node-label and edge-type counts | project | diagnostics, format, limit, offset | `cbm get_graph_schema '{"project":"P"}'` |
| `compare_graphs` | Compare two indexed snapshots: deterministic target-only additions and base-only removals of stable node/edge identities; each set capped by limit and a 512 KiB budget with exact totals and truncation reasons | base_project, target_project | limit, scan_limit | `cbm compare_graphs '{"base_project":"P","target_project":"P2"}'` |
| `get_architecture` | Compact counts, languages, packages, entry points | project | aspects, format, path | `cbm get_architecture '{"project":"P","aspects":["overview"]}'` |
| `search_code` | Graph-ranked text search: compact symbols, full bounded source, or file paths | pattern, project | context, debug, directory_limit, directory_offset, file_pattern, format, limit, match_limit, max_output_tokens, mode, path_filter, raw_content_offset, raw_limit, raw_offset, regex, result_limit, result_offset, source_max_lines | `cbm search_code '{"project":"P","pattern":"TODO","limit":5}'` |
| `list_projects` | List projects with stable paging |  | detail, format, include_details, limit, metadata_only, offset | `cbm list_projects` |
| `delete_project` | Delete a project from the index | project |  | `cbm delete_project '{"project":"P"}'` |
| `index_status` | Project readiness, counts, root, and coverage gaps | project | diagnostics, format, verbose | `cbm index_status '{"project":"P"}'` |
| `check_index_coverage` | Best-effort exact-path/scope coverage and freshness, paged separately | project | diagnostics, format, path_limit, path_offset, paths, scope_limit, scope_offset, scopes | `cbm check_index_coverage '{"project":"P","paths":["app/storage.py"]}'` |
| `detect_changes` | Map a Git diff to files and impact | project | base_branch, changed_cursor, changed_limit, changed_offset, depth, direction, format, impact_cursor, impact_offset, limit, max_output_tokens, module_cursor, module_limit, module_offset, scope, since | `cbm detect_changes '{"project":"P","since":"HEAD~5"}'` |
| `manage_adr` | Outline an ADR by default; get reads it; update replaces it | project | content, format, mode, section_limit, section_offset, section_updates | `cbm manage_adr '{"project":"P","mode":"get"}'` |
| `ingest_traces` | Validate and count traces; graph edge creation is not implemented | traces, project |  | `cbm ingest_traces '{"project":"P","traces":[...]}'` |

`format` tree/json (default tree) on every tool except `compare_graphs`, `delete_project`, `index_repository`, `ingest_traces`.

Other enums: `index_repository.mode` full/moderate/fast/cross-repo-intelligence (default full); `search_graph.detail` ids/default (default default); `query_graph.graph` code/missed (default code); `trace_path.direction` inbound/outbound/both (default both); `trace_path.mode` calls/data_flow/cross_service (default calls); `get_code_snippet.source_mode` auto/full/outline (default auto); `get_graph_schema.diagnostics` none/full (default none); `search_code.mode` compact/full/files (default compact); `list_projects.detail` identity/stats (default identity); `index_status.diagnostics` none/summary/full (default none); `check_index_coverage.diagnostics` none/full (default none); `detect_changes.scope` files/impact (default impact); `detect_changes.direction` inbound/outbound/both (default inbound); `manage_adr.mode` outline/get/update/set_sections/sections (default outline).

`search_code.regex` defaults to false: `pattern` is a literal unless you pass `"regex":true`.

Cypher (query_graph) is a subset: `NOT f.is_test` fails with "unexpected operator". Use `f.is_test = false` or filter via `search_graph` flags instead.
