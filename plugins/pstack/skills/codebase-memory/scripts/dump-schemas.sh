#!/usr/bin/env bash
# Regenerate references/tools.json from the binary's own MCP tools/list.
# Rerun after upgrading codebase-memory-mcp.
set -euo pipefail
out="$(dirname "$0")/../references/tools.json"
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"dump-schemas","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | timeout 20 codebase-memory-mcp 2>/dev/null \
  | jq -c 'select(.id==2)' > "$out"
echo "wrote $out: $(jq '.result.tools|length' "$out") tools"
