# codebase-memory tools (generated from tools.json, codebase-memory-mcp 0.8.1)

Regenerate: `bash scripts/dump-schemas.sh` then rebuild this table. `project` is the name from `list_projects`.

| Tool | Purpose | Required | Optional | Example |
|---|---|---|---|---|
| `index_repository` | Index a repository into the knowledge graph | repo_path | mode, persistence, target_projects | `cbm index_repository '{"repo_path":"/path/repo","mode":"fast"}'` |
| `search_graph` | Search the code knowledge graph for functions, classes, routes, and variables | project | exclude_entry_points, file_pattern, include_connected, label, limit, max_degree, min_degree, name_pattern, offset, qn_pattern, query, relationship, semantic_query | `cbm search_graph '{"project":"P","query":"init db","label":"Function","limit":5}'` |
| `query_graph` | Execute a Cypher query against the knowledge graph for complex multi-hop patterns, aggrega | query, project | max_rows | `cbm query_graph '{"project":"P","query":"MATCH (f:Function) WHERE f.in_degree = 0 RETURN f.qualified_name LIMIT 20"}'` |
| `trace_path` | Trace paths through the code graph | function_name, project | depth, direction, edge_types, include_tests, mode, parameter_name, risk_labels | `cbm trace_path '{"project":"P","function_name":"init_db","direction":"inbound","depth":2}'` |
| `get_code_snippet` | Read source code for a function/class/symbol | qualified_name, project | include_neighbors | `cbm get_code_snippet '{"project":"P","qualified_name":"P.app.storage.init_db"}'` |
| `get_graph_schema` | Get the schema of the knowledge graph (node labels, edge types) | project |  | `cbm get_graph_schema '{"project":"P"}'` |
| `get_architecture` | Get high-level architecture overview — packages, services, dependencies, and project struc | project | aspects | `cbm get_architecture '{"project":"P"}'` |
| `search_code` | Graph-augmented code search | pattern, project | context, file_pattern, limit, mode, path_filter, regex | `cbm search_code '{"project":"P","pattern":"TODO","limit":5}'` |
| `list_projects` | List all indexed projects |  |  | `cbm list_projects '{}'` |
| `delete_project` | Delete a project from the index | project |  | `cbm delete_project '{"project":"P"}'` |
| `index_status` | Get the indexing status of a project | project |  | `cbm index_status '{"project":"P"}'` |
| `detect_changes` | Detect code changes and their impact | project | base_branch, depth, scope, since | `cbm detect_changes '{"project":"P","since":"HEAD~5"}'` |
| `manage_adr` | Create or update Architecture Decision Records | project | content, mode, sections | `cbm manage_adr '{"project":"P","mode":"get"}'` |
| `ingest_traces` | Ingest runtime traces to enhance the knowledge graph | traces, project |  | `cbm ingest_traces '{"project":"P","traces":[...]}'` |

Enums: `index_repository.mode` full/moderate/fast/cross-repo-intelligence. `trace_path.direction` inbound/outbound/both, `.mode` calls/data_flow/cross_service. `search_code.mode` compact/full/files. `manage_adr.mode` get/update/sections.

Cypher (query_graph) is a subset: `NOT f.is_test` fails with "unexpected operator". Use `f.is_test = false` or filter via `search_graph` flags instead.
