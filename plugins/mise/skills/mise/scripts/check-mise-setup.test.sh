#!/bin/bash
# check-mise-setup.sh passes a repository built from the templates and prints
# the FAIL line of each check on a repository that breaks it. Runs offline.

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../../../../../scripts/hook-test-assertions.sh
. "$SKILL_DIR/../../../../scripts/hook-test-assertions.sh"

check="$SKILL_DIR/scripts/check-mise-setup.sh"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export MISE_DATA_DIR="$WORK/mise/data" MISE_STATE_DIR="$WORK/mise/state" \
  MISE_CACHE_DIR="$WORK/mise/cache" MISE_CONFIG_DIR="$WORK/mise/config" MISE_OFFLINE=1 \
  HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9

# A fake install, so no test downloads a tool.
mkdir -p "$MISE_DATA_DIR/installs/jq/1.8.1/bin"
printf '#!/bin/sh\necho jq-1.8.1\n' >"$MISE_DATA_DIR/installs/jq/1.8.1/bin/jq"
chmod +x "$MISE_DATA_DIR/installs/jq/1.8.1/bin/jq"

instantiate() { # TEMPLATE: prints it with each placeholder filled in
  sed -e 's/REPLACE_WITH_TOOL/jq/; s/REPLACE_WITH_EXACT_VERSION/1.8.1/' \
    -e 's/REPLACE_WITH_LINT_COMMAND/echo lint-ran/; s/REPLACE_WITH_UNIT_TEST_COMMAND/echo unit-ran/' \
    -e 's/REPLACE_WITH_INTEGRATION_TEST_COMMAND/echo integration-ran/; s#REPLACE_WITH_SOURCE_GLOB#src/**#' \
    -e 's/REPLACE_WITH_DESCRIPTION/Deploy/; s/REPLACE_WITH_COMMAND/echo deploy-ran/' "$SKILL_DIR/templates/$1"
}

repo() { # NAME: writes a passing repository from the templates and prints its directory
  local dir="$WORK/$1"
  mkdir -p "$dir/mise-tasks" "$dir/src"
  instantiate mise.toml >"$dir/mise.toml"
  instantiate file-task >"$dir/mise-tasks/deploy"
  chmod +x "$dir/mise-tasks/deploy"
  # mise lock needs the network, so the lockfile is written by hand.
  printf 'lockfile_version = 3\n\n[[tools.jq]]\nversion = "1.8.1"\nbackend = "aqua:jqlang/jq"\n' >"$dir/mise.lock"
  (cd "$dir" && mise trust -q)
  printf '%s\n' "$dir"
}

in_repo() { # DIR COMMAND...: runs a mise command in the repository
  cd "$1" || exit 1
  shift
  capture "$@"
  cd "$WORK" || exit 1
}

dir=$(repo good)
run_hook "$check" -C "$dir"
expect_equal "a repository built from mise.toml and file-task passes" "0 " "$STATUS $STDOUT"
in_repo "$dir" mise tasks validate
expect_equal "mise tasks validate passes on the mise.toml template" 0 "$STATUS"
in_repo "$dir" mise fmt --check
expect_equal "mise fmt --check passes on the mise.toml template" 0 "$STATUS"
in_repo "$dir" mise run test -- -k 'a b'
expect_contains "mise run test passes arguments to the runner" "unit-ran -k a b" "$STDOUT"
in_repo "$dir" mise run deploy prod --dry-run
expect_contains "the file task reads its typed arguments" "deploy-ran prod true" "$STDOUT"
in_repo "$dir" mise run deploy staging
expect_equal "the file task rejects a value that is not a choice" 1 "$STATUS"

run_hook "$check" -C "$dir" --run ci
expect_equal "--run ci passes" 0 "$STATUS"
expect_equal "ci runs each lint and test task once" "1 1" \
  "$(grep -cE '(^|\] )lint-ran$' <<<"$STDOUT") $(grep -cE '(^|\] )unit-ran$' <<<"$STDOUT")"
printf '\n[tasks."test:smoke"]\ndescription = "Run the smoke tests"\nrun = "echo smoke-ran"\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir" --run ci
expect_contains "a new test:<name> task runs under ci with no other edit" "smoke-ran" "$STDOUT"

run_hook "$check" -C "$dir" --run 'ci; touch pwned'
expect_contains "--run refuses a name that mise tasks ls does not print" \
  "FAIL  ci; touch pwned: task is not in mise tasks ls" "$STDOUT"
expect_equal "--run does not pass the name to a shell" "1 no" "$STATUS $([ -e "$dir/pwned" ] && echo yes || echo no)"

dir="$WORK/test-tasks"
mkdir -p "$dir/src"
echo x >"$dir/src/a"
{ printf '[tasks."lint:code"]\ndescription = "Lint the code"\nrun = "echo lint-ran"\n\n'; instantiate test-tasks.toml; } >"$dir/mise.toml"
printf 'lockfile_version = 3\n' >"$dir/mise.lock"
(cd "$dir" && mise trust -q)
run_hook "$check" -C "$dir" --run ci
expect_equal "a repository with test-tasks.toml passes" 0 "$STATUS"
expect_contains "ci runs the integration suite" "integration-ran" "$STDOUT"
in_repo "$dir" mise fmt --check
expect_equal "mise fmt --check passes on the test-tasks.toml template" 0 "$STATUS"
in_repo "$dir" mise run ci
expect_equal "a second ci run skips test:unit, whose sources did not change" "1 0" \
  "$(grep -c 'test:unit\] sources up-to-date, skipping' <<<"$STDERR") $(grep -cE '(^|\] )unit-ran$' <<<"$STDOUT")"
expect_contains "a second ci run still runs test:integration, which has no sources" "integration-ran" "$STDOUT"
sleep 1
echo y >>"$dir/src/a"
in_repo "$dir" mise run ci
expect_contains "a changed source runs test:unit again" "unit-ran" "$STDOUT"

mkdir "$WORK/empty"
run_hook "$check" -C "$WORK/empty"
expect_equal "a directory with no config fails" "1" "$STATUS"
expect_contains "the missing config is named" "FAIL  .: no mise config found" "$STDOUT"

dir="$WORK/untrusted"
cp -R "$WORK/good" "$dir"
run_hook "$check" -C "$dir"
expect_equal "an untrusted config fails" 1 "$STATUS"
expect_contains "the untrusted config is named" "FAIL  .: config is not trusted" "$STDOUT"
in_repo "$dir" mise trust --show
expect_contains "the check does not trust the config" "$dir: untrusted" "$STDOUT"

dir=$(repo unparsed)
printf '[tasks.broken\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a config that does not parse fails" 1 "$STATUS"
expect_contains "the parse error is named" "FAIL  mise.toml: config does not parse" "$STDOUT"

dir="$WORK/placeholders"
mkdir -p "$dir/mise-tasks"
cp "$SKILL_DIR/templates/mise.toml" "$dir/mise.toml"
cp -p "$SKILL_DIR/templates/file-task" "$dir/mise-tasks/deploy"
(cd "$dir" && mise trust -q)
run_hook "$check" -C "$dir"
expect_equal "the templates fail with their placeholders left in" 1 "$STATUS"
expect_contains "a placeholder in mise.toml is named" "FAIL  mise.toml: a REPLACE_WITH_ placeholder is left" "$STDOUT"
expect_contains "a placeholder in a file task is named" "FAIL  mise-tasks/deploy: a REPLACE_WITH_ placeholder is left" "$STDOUT"
in_repo "$dir" mise run ci
expect_equal "ci fails while a run placeholder is left" 127 "$STATUS"

dir=$(repo invalid)
printf '\n[tasks.broken]\ndescription = "Broken"\ndepends = ["no-such-task"]\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a task that fails validation fails" 1 "$STATUS"
expect_contains "the validation failure is named" "FAIL  mise.toml: mise tasks validate fails" "$STDOUT"

dir=$(repo missing)
sed -i.bak 's/^jq = "1.8.1"/jq = "1.7.1"/' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a tool that is not installed fails" 1 "$STATUS"
expect_contains "the missing tool is named" "FAIL  mise.toml: a requested tool is not installed" "$STDOUT"

for requested in 1.8 latest; do
  dir=$(repo "fuzzy-$requested")
  sed -i.bak "s/^jq = \"1.8.1\"/jq = \"$requested\"/" "$dir/mise.toml"
  run_hook "$check" -C "$dir"
  expect_equal "a tool requested as $requested fails" 1 "$STATUS"
  expect_contains "the $requested request is named" \
    "FAIL  mise.toml: jq is requested as $requested, not an exact version" "$STDOUT"
done

dir=$(repo unlocked)
rm "$dir/mise.lock"
run_hook "$check" -C "$dir"
expect_equal "a repository with no mise.lock fails" 1 "$STATUS"
expect_contains "the missing lockfile is named" "FAIL  mise.lock: mise.lock does not exist" "$STDOUT"

dir=$(repo stale-lock)
sed -i.bak 's/1.8.1/1.7.1/' "$dir/mise.lock"
run_hook "$check" -C "$dir"
expect_equal "a mise.lock without the requested version fails" 1 "$STATUS"
expect_contains "the stale lockfile is named" "FAIL  mise.lock: mise.lock does not list every requested tool" "$STDOUT"

dir=$(repo undescribed)
printf '\n[tasks.bare]\nrun = "echo bare"\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a task with no description fails" 1 "$STATUS"
expect_contains "the task is named" "FAIL  bare: task has no description" "$STDOUT"

dir=$(repo no-ci)
sed -i.bak '/^\[tasks.ci\]/,/^depends/d' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a repository with no ci task fails" 1 "$STATUS"
expect_contains "the missing ci task is named" "FAIL  mise.toml: no ci task" "$STDOUT"
run_hook "$check" -C "$dir" --run lint
expect_contains "--run does not run a task after a failed check" \
  "FAIL  lint: task was not run, because a check failed" "$STDOUT"

finish
