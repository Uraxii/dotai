#!/bin/bash
# check-mise-setup.sh passes a repository built from the templates and prints
# the FAIL line of each check on a repository that breaks it. Runs offline.

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../../../../../scripts/hook-test-assertions.sh
. "$SKILL_DIR/../../../../scripts/hook-test-assertions.sh"

check="$SKILL_DIR/scripts/check-mise-setup.sh"
# The real path: mise and the check print real paths, and a temp root can be a symlink.
WORK=$(cd -P "$(mktemp -d)" && pwd) || exit 1
: "${WORK:?}"
trap 'rm -rf "$WORK"' EXIT
# Before each command: stop if a test directory is empty or not under WORK, so
# that no test writes outside its temp directory.
trap 'case ${dir-$WORK/unset}:${root-$WORK/unset} in "$WORK"/*:"$WORK"/*) ;; *)
  echo "check-mise-setup.test.sh: a test directory is not under $WORK" >&2; exit 1 ;; esac' DEBUG
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

in_repo() { # DIR COMMAND...: runs a mise command in the repository, with no config from above WORK
  cd "$1" || exit 1
  shift
  capture env MISE_CEILING_PATHS="$WORK" "$@"
  cd "$WORK" || exit 1
}

dir=$(repo good)
run_hook "$check" -C "$dir"
expect_equal "a repository built from mise.toml and file-task passes and says so" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

cp -R "$dir" "$WORK/no-ci-source"
sed -i.bak '/^\[tasks.ci\]/,/^depends/d' "$WORK/no-ci-source/mise.toml"

mkdir -p "$WORK/global/tasks"
printf '[tools]\nyq = "4.44.3"\n\n[tasks.global-bare]\nrun = "true"\n' >"$WORK/global/config.toml"
printf '#!/bin/sh\n' >"$WORK/global/tasks/global-file"
chmod +x "$WORK/global/tasks/global-file"
printf '[tools]\nshellcheck = "0.10"\n' >"$WORK/system.toml"
capture env MISE_CONFIG_DIR="$WORK/global" MISE_SYSTEM_CONFIG_FILE="$WORK/system.toml" bash "$check" -C "$dir"
expect_equal "a global and a system config with tools and bare tasks do not fail a sound repository" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

capture env PATH=/nonexistent "$BASH" "$check" -C "$dir"
expect_equal "with no mise on PATH the check says so on stderr and exits 2" \
  "2 check-mise-setup.sh: mise is not on PATH" "$STATUS ${STDERR%$'\n'}"

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

in_repo "$dir" mise run ci
expect_equal "ci runs each lint and test task once" "1 1" \
  "$(grep -cE '(^|\] )lint-ran$' <<<"$STDOUT") $(grep -cE '(^|\] )unit-ran$' <<<"$STDOUT")"
printf '\n[tasks."test:smoke"]\ndescription = "Run the smoke tests"\nrun = "echo smoke-ran"\n' >>"$dir/mise.toml"
in_repo "$dir" mise run ci
expect_contains "a new test:<name> task runs under ci with no other edit" "smoke-ran" "$STDOUT"

dir="$WORK/test-tasks"
mkdir -p "$dir/src"
echo x >"$dir/src/a"
{ printf '[tasks."lint:code"]\ndescription = "Lint the code"\nrun = "echo lint-ran"\n\n'; instantiate test-tasks.toml; } >"$dir/mise.toml"
(cd "$dir" && mise trust -q)
run_hook "$check" -C "$dir"
expect_equal "a repository with test-tasks.toml, no tools and no lockfile passes" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"
in_repo "$dir" mise run ci
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

ln -s "$dir" "$WORK/link-to-untrusted"
run_hook "$check" -C "$WORK/link-to-untrusted"
expect_equal "an untrusted config behind a symlink fails as not trusted" "1 FAIL  .: config is not trusted
      fix: read the config, then run: mise trust .
check-mise-setup.sh: $dir: 1 failed" "$STATUS ${STDOUT%$'\n'}"

dir="$WORK/trusted-parent/project"
mkdir -p "$WORK/trusted-parent"
cp -R "$WORK/no-ci-source" "$dir"
printf '[tools]\njq = "1.8"\n\n[tasks.ci]\ndescription = "Run the parent ci"\nrun = "true"\n' >"$WORK/trusted-parent/mise.toml"
for trusted in "$WORK/trusted-parent" "$dir"; do (cd "$trusted" && mise trust -q); done
run_hook "$check" -C "$dir"
expect_equal "a trusted config above the repository adds no tool and no ci task to the result" "1 FAIL  mise.toml: no ci task
      fix: add a ci task that depends on lint:* and test:*
check-mise-setup.sh: $dir: 1 failed" "$STATUS ${STDOUT%$'\n'}"

mkdir "$WORK/trusted-parent/empty"
run_hook "$check" -C "$WORK/trusted-parent/empty"
expect_equal "a directory with no config below a trusted config fails as no config" \
  "1 FAIL  .: no mise config found" "$STATUS ${STDOUT%%$'\n'*}"

dir="$WORK/untrusted-parent/project"
mkdir -p "$WORK/untrusted-parent"
cp -R "$WORK/good" "$dir"
printf '[env]\nABOVE = "1"\n' >"$WORK/untrusted-parent/mise.toml"
(cd "$dir" && mise trust -q)
run_hook "$check" -C "$dir"
expect_equal "an untrusted config with [env] above the repository does not fail it" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

dir="$WORK/trusted-by-setting"
cp -R "$WORK/good" "$dir"
mkdir "$WORK/trust-setting"
printf '[settings]\ntrusted_config_paths = ["%s"]\n' "$dir" >"$WORK/trust-setting/config.toml"
capture env MISE_CONFIG_DIR="$WORK/trust-setting" bash "$check" -C "$dir"
expect_equal "a config trusted by the global trusted_config_paths setting passes" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

mkdir "$WORK/home"
echo 'jq 1.8.1' >"$WORK/home/.tool-versions"
cp -R "$WORK/good" "$WORK/home/proj"
(cd "$WORK/home/proj" && mise trust -q)
capture env HOME="$WORK/home" bash "$check" -C "$WORK/home/proj"
expect_equal "an untrusted ~/.tool-versions above the repository does not fail it" \
  "0 check-mise-setup.sh: $WORK/home/proj: 0 failed" "$STATUS ${STDOUT%$'\n'}"

dir=$(repo unparsed)
printf '[tasks.broken\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a config that does not parse fails" 1 "$STATUS"
expect_contains "the load error is named" "FAIL  mise.toml: mise cannot load the config" "$STDOUT"
expect_contains "the fix names mise config ls and the usual causes" \
  "fix: run mise config ls to see why: TOML syntax, a min_version above this mise, or a required [env] value that is not set" "$STDOUT"
for cause in min_version required; do
  dir=$(repo "unloaded-$cause")
  if [ "$cause" = min_version ]; then
    sed -i.bak 's/^min_version = .*/min_version = "2099.1.1"/' "$dir/mise.toml"
  else
    sed -i.bak '/^\[env\]$/d' "$dir/mise.toml"
    printf '\n[env]\nAPI_TOKEN = { required = "set it in mise.local.toml" }\n' >>"$dir/mise.toml"
  fi
  run_hook "$check" -C "$dir"
  expect_equal "a config with a $cause mise cannot meet fails as not loaded" \
    "1 FAIL  mise.toml: mise cannot load the config" "$STATUS ${STDOUT%%$'\n'*}"
done

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
dir=$(repo env-placeholders)
mkdir "$dir/.config"
for file in mise.local.toml mise.ci.toml .mise.ci.toml .config/mise.ci.toml; do
  printf '[env]\nDEPLOY_URL = "REPLACE_WITH_URL"\n' >"$dir/$file"
done
run_hook "$check" -C "$dir"
expect_equal "a placeholder in a local config and in each environment config is named" "1 FAIL  mise.ci.toml: a REPLACE_WITH_ placeholder is left
FAIL  mise.local.toml: a REPLACE_WITH_ placeholder is left
FAIL  .mise.ci.toml: a REPLACE_WITH_ placeholder is left
FAIL  .config/mise.ci.toml: a REPLACE_WITH_ placeholder is left
check-mise-setup.sh: $dir: 4 failed" "$STATUS $(grep -v '^      fix: ' <<<"$STDOUT")"

dir=$(repo invalid)
printf '\n[tasks.broken]\ndescription = "Broken"\ndepends = ["no-such-task"]\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a task that fails validation fails" 1 "$STATUS"
expect_contains "the validation failure is named" "FAIL  mise.toml: mise tasks validate fails" "$STDOUT"

dir=$(repo env-in-task)
mkdir "$dir/app"
printf '\n[tasks.build]\ndescription = "Build the app"\ndir = "{{env.APP_DIR}}"\nrun = "true"\n' >>"$dir/mise.toml"
sed -i.bak 's/^\[env\]$/[env]\nAPP_DIR = "app"/' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a task field that reads an [env] value passes validation" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

dir=$(repo missing)
sed -i.bak 's/^jq = "1.8.1"/jq = "1.7.1"/' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a tool that is not installed fails" 1 "$STATUS"
expect_contains "the missing tool is named" "FAIL  mise.toml: a requested tool is not installed" "$STDOUT"

for requested in 1.8 latest path:/tmp ref:jq-1.8.1 prefix:1.8.1 sub-0.1:1.8.2 '1.8.1 1.8'; do
  dir=$(repo "fuzzy-${requested//[:\/ ]/-}")
  value=\"$requested\"
  [ "$requested" = '1.8.1 1.8' ] && value='["1.8.1", "1.8"]'
  sed -i.bak "s#^jq = \"1.8.1\"#jq = $value#" "$dir/mise.toml"
  run_hook "$check" -C "$dir"
  expect_equal "a tool requested as $value fails" 1 "$STATUS"
  expect_contains "the $value request is named with a fix that holds for any request" \
    "FAIL  mise.toml: jq is requested as ${requested#1.8.1 }, not an exact version
      fix: request one exact release, such as: mise use --pin jq@<version>" "$STDOUT"
done

capture env MISE_JQ_VERSION=1.8.1 bash "$check" -C "$WORK/fuzzy-1.8"
expect_contains "a MISE_<TOOL>_VERSION variable does not hide a request that is not exact" \
  "FAIL  mise.toml: jq is requested as 1.8, not an exact version" "$STDOUT"

dir=$(repo local-override)
printf '[tools]\njq = "1.7.1"\n' >"$dir/mise.local.toml"
run_hook "$check" -C "$dir"
expect_equal "a tool request in mise.local.toml does not fail a pinned repository" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

dir="$WORK/local-pins-latest"
cp -R "$WORK/fuzzy-latest" "$dir"
printf '[tools]\njq = "1.8.1"\n' >"$dir/mise.local.toml"
(cd "$dir" && mise trust -q)
run_hook "$check" -C "$dir"
expect_contains "an exact version in mise.local.toml does not hide a committed latest" \
  "FAIL  mise.toml: jq is requested as latest, not an exact version" "$STDOUT"

dir=$(repo env-ci)
printf '[tools]\njq = "latest"\n' >"$dir/mise.ci.toml"
run_hook "$check" -C "$dir"
plain="$STATUS $STDOUT"
capture env MISE_ENV=ci bash "$check" -C "$dir"
expect_equal "MISE_ENV=ci gives the result of a run without it" "$plain" "$STATUS $STDOUT"
expect_equal "a mise.ci.toml is not checked without MISE_ENV" "0 check-mise-setup.sh: $dir: 0 failed" "${plain%$'\n'}"

dir="$WORK/dot-config"
mkdir -p "$dir/.config/mise"
printf '[settings]\nlockfile = true\n\n[tools]\njq = "1.8.1"\n\n[tasks.ci]\ndescription = "Run ci"\nrun = "true"\n' >"$dir/.config/mise/config.toml"
printf 'lockfile_version = 3\n\n[[tools.jq]]\nversion = "1.8.1"\nbackend = "aqua:jqlang/jq"\n' >"$dir/.config/mise/mise.lock"
(cd "$dir" && mise trust -q)
run_hook "$check" -C "$dir"
expect_equal "a .config/mise/config.toml repository with .config/mise/mise.lock passes" \
  "0 check-mise-setup.sh: $dir: 0 failed" "$STATUS ${STDOUT%$'\n'}"

dir=$(repo unlocked)
rm "$dir/mise.lock"
run_hook "$check" -C "$dir"
expect_equal "a repository with tools and no lockfile fails" "1 FAIL  mise.lock: the lockfile does not list every requested tool
      fix: run mise lock, and commit the lockfile it writes
check-mise-setup.sh: $dir: 1 failed" "$STATUS ${STDOUT%$'\n'}"

dir=$(repo lockfile-off)
rm "$dir/mise.lock"
sed -i.bak 's/^lockfile = true/lockfile = false/' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a repository with tools, no lockfile and lockfile = false fails" "1 FAIL  mise.lock: the lockfile does not list every requested tool
      fix: run mise lock, and commit the lockfile it writes
check-mise-setup.sh: $dir: 1 failed" "$STATUS ${STDOUT%$'\n'}"
dir=$(repo lockfile-unset)
rm "$dir/mise.lock"
sed -i.bak '/^lockfile = true/d' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_contains "a repository with tools, no lockfile and no lockfile setting fails" \
  "FAIL  mise.lock: the lockfile does not list every requested tool" "$STDOUT"

dir=$(repo stale-lock)
sed -i.bak 's/1.8.1/1.7.1/' "$dir/mise.lock"
run_hook "$check" -C "$dir"
expect_equal "a mise.lock without the requested version fails" 1 "$STATUS"
expect_contains "the stale lockfile is named" "FAIL  mise.lock: the lockfile does not list every requested tool" "$STDOUT"

dir=$(repo undescribed)
printf '\n[tasks.bare]\nrun = "echo bare"\n' >>"$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a task with no description fails" 1 "$STATUS"
expect_contains "the task is named with both ways to describe it" "FAIL  bare: task has no description
      fix: add description = \"...\" to a TOML task, or #MISE description=\"...\" to a file task" "$STDOUT"

dir=$(repo no-ci)
sed -i.bak '/^\[tasks.ci\]/,/^depends/d' "$dir/mise.toml"
run_hook "$check" -C "$dir"
expect_equal "a repository with no ci task fails" 1 "$STATUS"
expect_contains "the missing ci task is named" "FAIL  mise.toml: no ci task" "$STDOUT"

root="$WORK/monorepo"
mkdir -p "$root/apps/api" "$root/apps/web" "$root/apps/new" "$root/apps/lib"
printf 'monorepo_root = true\n\n[monorepo]\nconfig_roots = ["apps/api", "apps/web", "apps/new", "apps/lib"]\n\n[tasks.ci]\ndescription = "Run every ci task"\nrun = "true"\n' >"$root/mise.toml"
printf '[settings]\nlockfile = true\n\n[tools]\njq = "1.8.1"\n\n[tasks.ci]\ndescription = "Run web ci"\nrun = "true"\n' >"$root/apps/web/mise.toml"
printf 'lockfile_version = 3\n\n[[tools.jq]]\nversion = "1.8.1"\nbackend = "aqua:jqlang/jq"\n' >"$root/apps/web/mise.lock"
printf '[tools]\njq = "1.8"\n\n[tasks.ci]\ndescription = "Run REPLACE_WITH_API ci"\nrun = "true"\ndepends = ["no-such-task"]\n' >"$root/apps/api/mise.toml"
printf '[env]\nPWNED = "{{ exec(command=\x27touch %s/pwned\x27) }}"\n\n[tools]\njq = "1.7.1"\n\n[tasks.x]\ndescription = "{{ exec(command=\x27touch %s/pwned\x27) }}"\nrun = "true"\n' "$root" "$root" >"$root/apps/new/mise.toml"
printf '[tasks."test:unit"]\ndescription = "Run lib tests"\nrun = "true"\n\n[tasks.bare]\nrun = "true"\n' >"$root/apps/lib/mise.toml"
for project in . apps/web apps/api apps/lib; do (cd "$root/$project" && mise trust -q); done
run_hook "$check" -C "$root"
expect_equal "a monorepo root with no tools passes" "0 check-mise-setup.sh: $root: 0 failed" "$STATUS ${STDOUT%$'\n'}"
run_hook "$check" -C "$root/apps/web"
expect_equal "a sound monorepo project with its own apps/web/mise.lock passes" \
  "0 check-mise-setup.sh: $root/apps/web: 0 failed" "$STATUS ${STDOUT%$'\n'}"
run_hook "$check" -C "$root/apps/api"
expect_equal "a monorepo project reports its own defects" "1 FAIL  mise.toml: a REPLACE_WITH_ placeholder is left
      fix: replace each REPLACE_WITH_ value
FAIL  mise.toml: mise tasks validate fails
      fix: run mise tasks validate to see each error. In a monorepo, a task field that calls exec() or reads [env] fails too, because the check runs in safe mode there
FAIL  mise.toml: jq is requested as 1.8, not an exact version
      fix: request one exact release, such as: mise use --pin jq@<version>
FAIL  mise.lock: the lockfile does not list every requested tool
      fix: run mise lock, and commit the lockfile it writes
check-mise-setup.sh: $root/apps/api: 4 failed" "$STATUS ${STDOUT%$'\n'}"
run_hook "$check" -C "$root/apps/lib"
expect_equal "a monorepo project is checked for its own ci task and descriptions only" "1 FAIL  //apps/lib:bare: task has no description
      fix: add description = \"...\" to a TOML task, or #MISE description=\"...\" to a file task
FAIL  mise.toml: no ci task
      fix: add a ci task that depends on lint:* and test:*
check-mise-setup.sh: $root/apps/lib: 2 failed" "$STATUS ${STDOUT%$'\n'}"
ln -s "$root/apps/web" "$WORK/link-to-web"
run_hook "$check" -C "$WORK/link-to-web"
expect_equal "a monorepo project behind a symlink is checked for its own ci task" \
  "0 check-mise-setup.sh: $root/apps/web: 0 failed" "$STATUS ${STDOUT%$'\n'}"
cp -R "$root" "$WORK/untrusted-root"
(cd "$WORK/untrusted-root/apps/web" && mise trust -q)
run_hook "$check" -C "$WORK/untrusted-root/apps/web"
expect_contains "an untrusted monorepo root fails a project under it" \
  "FAIL  $WORK/untrusted-root: config is not trusted" "$STDOUT"
run_hook "$check" -C "$root/apps/new"
expect_contains "an untrusted monorepo project is named" "FAIL  .: config is not trusted" "$STDOUT"
in_repo "$root/apps/new" mise trust --show
expect_contains "no check trusts the untrusted project" "$root/apps/new: untrusted" "$STDOUT"
expect_equal "no check runs a template exec() or installs a tool" "no 1.8.1" \
  "$([ -e "$root/pwned" ] && echo yes || echo no) $(ls "$MISE_DATA_DIR/installs/jq")"

mkdir "$WORK/slow"
printf '#!/bin/sh\nsleep 1\nexec %s "$@"\n' "$(command -v mise)" >"$WORK/slow/mise"
chmod +x "$WORK/slow/mise"
for signal in HUP TERM; do
  mkdir "$WORK/tmp-$signal"
  env PATH="$WORK/slow:$PATH" TMPDIR="$WORK/tmp-$signal" bash "$check" -C "$WORK/good" >/dev/null 2>&1 &
  pid=$!
  until [ -d "$WORK/tmp-$signal"/*/state ] || ! kill -0 "$pid" 2>/dev/null; do sleep 0.1; done
  kill -"$signal" "$pid"
  wait "$pid"
  alive=$(pgrep -f "$WORK/slow" >/dev/null && echo alive)
  sleep 2
  expect_equal "SIG$signal leaves no copy of the mise state and no mise process" "" \
    "$alive$(ls -A "$WORK/tmp-$signal")"
done

finish
