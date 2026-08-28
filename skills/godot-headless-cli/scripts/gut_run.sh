#!/usr/bin/env bash
# gut_run.sh - run GUT unit tests headless and surface pass/fail + exit code.
#
# Requires the GUT addon installed in the project at res://addons/gut/.
# GUT's CLI entry is a SceneTree script: addons/gut/gut_cmdln.gd.
#
# Usage:
#   gut_run.sh --project <dir> [-gdir=res://test] [-gtest=res://test/x.gd] [gut args...]
#
# Common GUT args (pass through verbatim):
#   -gdir=res://test        directory to scan for tests
#   -gtest=res://test/x.gd  a single test script
#   -gprefix=test_          test file prefix (default test_)
#   -gexit                  exit after run (this wrapper adds it if absent)
#   -gexit_on_success       exit 0 only if all pass
#
# Exit code: GUT's exit code. Non-zero means failures/errors.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT=""
GODOT_OPT=()
GUT_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?--project needs a dir}"; shift 2;;
    --godot)   GODOT_OPT=(--godot "$2"); shift 2;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) GUT_ARGS+=("$1"); shift;;
  esac
done

[[ -z "$PROJECT" ]] && { echo "gut_run.sh: --project required" >&2; exit 2; }

# Ensure GUT actually exits the process when done.
printf '%s\n' "${GUT_ARGS[@]}" | grep -q -- '-gexit' || GUT_ARGS+=(-gexit)

# Delegate binary discovery + noise filtering to run_headless.sh.
"$HERE/run_headless.sh" --project "$PROJECT" "${GODOT_OPT[@]}" -- \
  -s res://addons/gut/gut_cmdln.gd "${GUT_ARGS[@]}"
rc=$?

if [[ $rc -eq 0 ]]; then
  echo "gut_run.sh: PASS (exit 0)" >&2
else
  echo "gut_run.sh: FAIL/ERROR (exit $rc)" >&2
fi
exit "$rc"
