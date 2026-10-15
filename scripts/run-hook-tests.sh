#!/bin/bash
# Runs every plugin hook test and the shunt evals, and checks that the files
# each plugin carries its own copy of have not drifted apart.
#
# Usage: scripts/run-hook-tests.sh
# Needs bash and jq for the tests; the hooks themselves need only bash and awk.

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
failed=0

# A plugin cannot read another plugin's files, so each one ships these.
for shared in hook-json.awk run-hook.cmd; do
  copies=("$root"/plugins/*/hooks/"$shared")
  for copy in "${copies[@]}"; do
    if ! cmp -s "${copies[0]}" "$copy"; then
      echo "FAIL  ${copy#"$root"/} differs from ${copies[0]#"$root"/}"
      failed=1
    fi
  done
done

for test in "$root"/plugins/*/hooks/tests/*.test.sh; do
  bash "$test" || failed=1
done
bash "$root/plugins/shunt/evals/run.sh" 2>&1 | grep -E 'FAIL|^Total'
[ "${PIPESTATUS[0]}" = 0 ] || failed=1
exit "$failed"
