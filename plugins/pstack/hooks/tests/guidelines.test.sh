#!/bin/bash
# The code-quality guideline hook, run through its wrapper the way a harness
# runs it: payload on stdin, one JSON object or nothing on stdout. Guideline
# files are fixtures written here, and ruff and eslint are stubs, so the
# result does not depend on the real guidelines folder or on installed tools.

PLUGIN_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
HOOK="$PLUGIN_ROOT_DIR/hooks/guidelines.sh"
ENGINE="$PLUGIN_ROOT_DIR/skills/principle-code-quality/scripts/guideline_hook.py"
FIXTURES="$WORK/guidelines"
mkdir -p "$FIXTURES" "$WORK/bin" "$WORK/tools"
export WORK CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR" CLAUDE_PLUGIN_DATA="$WORK/data"
export PSTACK_GUIDELINES_DIR="$FIXTURES"

# guideline FILE BODY KEY-LINE...
guideline() {
  local file=$1 body=$2
  shift 2
  { echo ---; printf '%s\n' "$@"; echo ---; printf '%s\n' "$body"; } >"$FIXTURES/$file"
}
ONE_FOR='Use at most one `for` clause per comprehension. Write a flattening comprehension as an explicit `for` loop that names each intermediate value.'
NESTED_CALL='Inside a comprehension, do not pass a call'"'"'s result straight into another call. Bind the inner result to a name in an explicit `for` loop.'
DATACLASS='Model a record with a `@dataclass`, not a `dict` with fixed string keys.'
guideline py-comprehension-one-for.md "$ONE_FOR" 'id: py.comprehension.one-for' \
  'languages: python' 'scope: contextual' 'severity: block' 'enabled: true' \
  'detectors: code_quality:CQ001' 'keywords: list comprehension, flatten'
guideline py-comprehension-no-nested-call.md "$NESTED_CALL" 'id: py.comprehension.no-nested-call' \
  'languages: python' 'scope: contextual' 'severity: warn' 'enabled: true' 'detectors: code_quality:CQ002'
guideline py-error-no-assert-in-prod.md \
  'Do not use `assert` for runtime checks in production code; raise an exception instead.' \
  'id: py.error.no-assert-in-prod' 'languages: python' 'scope: contextual' 'severity: warn' \
  'enabled: true' 'detectors: ruff:S101' 'keywords: assert' \
  'exclude: tests/*, test_*.py, *_test.py, conftest.py'
guideline py-import-no-star.md 'Import names explicitly; do not use `from module import *`.' \
  'id: py.import.no-star' 'languages: python' 'scope: contextual' 'severity: block' \
  'enabled: true' 'detectors: ruff:F403'
guideline py-logging-no-print.md 'Use the logging module, not print.' 'id: py.logging.no-print' \
  'languages: python' 'scope: contextual' 'severity: warn' 'enabled: false' 'detectors: ruff:T201'
guideline py-data-dataclass-over-dict.md "$DATACLASS" 'id: py.data.dataclass-over-dict' \
  'languages: python' 'scope: global' 'severity: warn' 'enabled: true' 'detectors:'
guideline ts-binding-no-var.md 'Declare bindings with `const`, or `let` when reassigned; never `var`.' \
  'id: ts.binding.no-var' 'languages: typescript, javascript' 'scope: contextual' \
  'severity: block' 'enabled: true' 'detectors: eslint:no-var'

# The hook sees only these programs: no installed ruff or eslint.
for tool in bash sh cat mkdir date wc sleep; do
  ln -s "$(command -v "$tool")" "$WORK/tools/$tool"
done
ln -s "$(command -v python3)" "$WORK/bin/python3"
cat >"$WORK/bin/ruff" <<'STUB'
#!/bin/sh
if [ "$1" = --version ]; then
  echo "${RUFF_VERSION:-ruff 0.16.9}"
  exit 0
fi
echo "$*" >>"$WORK/ruff.args"
cat >/dev/null
[ -n "$RUFF_SLEEP" ] && sleep "$RUFF_SLEEP"
[ -n "$RUFF_STDERR" ] && printf '%s\n' "$RUFF_STDERR" >&2
printf '%s\n' "${RUFF_JSON:-[]}"
STUB
cat >"$WORK/bin/eslint" <<'STUB'
#!/bin/sh
if [ "$1" = --version ]; then
  echo v10.1.0
  exit 0
fi
echo "$*" >>"$WORK/eslint.args"
cat >/dev/null
[ -n "$ESLINT_JSON" ] || ESLINT_JSON='[{"messages":[]}]'
printf '%s\n' "$ESLINT_JSON"
STUB
chmod +x "$WORK/bin/ruff" "$WORK/bin/eslint"
HOOK_PATH="$WORK/bin:$WORK/tools"

PAGES='def pages(paths):
    return tuple(page for path in paths for page in parse_page(_read(path)))
'
EXPLICIT_LOOP='def pages(paths):
    found = []
    for path in paths:
        text = _read(path)
        found.extend(parse_page(text))
    print(len(found))
    return tuple(found)
'
OVERRIDE='Project standards, configs and lints override these defaults.'
BLOCKED="Blocked: this edit adds code that breaks a block guideline. Fix it, then retry the edit.
$OVERRIDE"
PAGES_REASON="$BLOCKED

[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2
$ONE_FOR

[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:2
$NESTED_CALL"
GLOBALS_CONTEXT="Code-quality guidelines (pstack):
$OVERRIDE

[py.data.dataclass-over-dict] warn
$DATACLASS"
F403_ROW='[{"code":"F403","location":{"row":1}}]'

# Each case gets its own project directory and session.
new_case() {
  SESSION=$1
  PROJECT="$WORK/projects/$1"
  mkdir -p "$PROJECT/src" "$PROJECT/tests"
  export CLAUDE_PROJECT_DIR="$PROJECT"
  rm -f "$WORK/ruff.args" "$WORK/eslint.args"
}

# hook [VAR=VALUE...]: runs the wrapper with the payload on stdin.
hook() {
  capture env PATH="$HOOK_PATH" "$@" bash "$HOOK" "${HARNESS:-claude}"
}

# tool_payload EVENT TOOL FILE JQ-TOOL-INPUT [JQ-ARG...]
tool_payload() {
  local event=$1 tool=$2 file=$3 filter=$4
  shift 4
  jq -cn --arg e "$event" --arg t "$tool" --arg s "$SESSION" --arg c "$PROJECT" \
    --arg f "$PROJECT/$file" "$@" \
    "{hook_event_name: \$e, session_id: \$s, cwd: \$c, tool_name: \$t, tool_input: ({file_path: \$f} + $filter)}"
}
write() { tool_payload "${3:-PreToolUse}" Write "$1" '{content: $text}' --arg text "$2"; }
prompt() {
  jq -cn --arg s "$SESSION" --arg c "$PROJECT" --arg p "$1" \
    '{hook_event_name: "UserPromptSubmit", session_id: $s, cwd: $c, prompt: $p}'
}
session_start() {
  jq -cn --arg s "$SESSION" --arg c "$PROJECT" --arg source "$1" \
    '{hook_event_name: "SessionStart", session_id: $s, cwd: $c, source: $source}'
}
decision() { jq -r '.hookSpecificOutput.permissionDecision // empty' <<<"$STDOUT" 2>/dev/null; }
reason() { jq -r '.hookSpecificOutput.permissionDecisionReason // empty' <<<"$STDOUT" 2>/dev/null; }
context() { jq -r '.hookSpecificOutput.additionalContext // empty' <<<"$STDOUT" 2>/dev/null; }

new_case flattening
hook <<<"$(write pages.py "$PAGES")"
expect_equal "a flattening comprehension is denied" deny "$(decision)"
expect_equal "the deny reason carries both findings and their guidance" "$PAGES_REASON" "$(reason)"
expect_equal "the deny exits 0" 0 "$STATUS"

new_case clean
hook <<<"$(write pages.py "$EXPLICIT_LOOP")"
expect_equal "the explicit loop is not denied" "" "$(decision)"
expect_equal "the first Python touch delivers the global guideline" "$GLOBALS_CONTEXT" "$(context)"
hook <<<"$(write pages.py "$EXPLICIT_LOOP")"
expect_equal "a second clean write says nothing" "0:" "$STATUS:$STDOUT"
hook <<<"$(tool_payload PostToolUse Read pages.py '{}' | jq -c '. + {agent_id: "a1"}')"
expect_contains "a subagent gets its own delivery" "[py.data.dataclass-over-dict] warn" "$(context)"
hook <<<"$(session_start compact)"
expect_equal "compaction sends the globals again" "$GLOBALS_CONTEXT" "$(context)"
hook <<<"$(tool_payload PostToolUse Read pages.py '{}')"
expect_equal "a read after compaction says nothing" "" "$STDOUT"
expect_equal "state files are private" "-rw-------" \
  "$(ls -l "$WORK/data/guideline-state/clean/main.json" | cut -c1-10)"

new_case preexisting
printf '%s' "$PAGES" >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse Edit pages.py '{old_string: "def pages(paths):", new_string: "def pages(paths):  # noqa-free"}')"
expect_equal "an edit that leaves an old violation is not denied" "" "$(decision)"
hook <<<"$(tool_payload PostToolUse Edit pages.py '{}')"
expect_contains "the old violation arrives as a warning after the write" \
  "[py.comprehension.one-for] warn: code_quality:CQ001 at pages.py:2" "$(context)"

new_case adds
printf '%s' "$EXPLICIT_LOOP" >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse Edit pages.py '{old_string: "    return tuple(found)", new_string: "    return tuple(p for q in found for p in q)"}')"
expect_equal "an edit that adds the violation is denied" deny "$(decision)"
expect_contains "the deny names the new line" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:7" "$(reason)"

new_case replace-all
printf 'x = 1\nx = 1\n' >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse Edit pages.py '{old_string: "x = 1", new_string: "x = [a for b in c for a in b]", replace_all: true}')"
expect_equal "replace_all blocks each added line" "$BLOCKED

[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:1
$ONE_FOR

[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2 (guidance sent earlier)" "$(reason)"

new_case refused
printf 'x = 1\n' >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse Edit pages.py '{old_string: "absent", new_string: "y = [a for b in c for a in b]"}')"
expect_contains "an edit whose text cannot be built is named" "Notice: did not check pages.py: could not build the text this edit leaves, so PostToolUse checks it" "$(context)"
expect_equal "and is not denied" "" "$(decision)"

new_case crlf
printf 'def pages(paths):\r\n    return tuple(found)\r\n' >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse Edit pages.py '{old_string: "def pages(paths):\n    return tuple(found)", new_string: "def pages(paths):\n    return tuple(p for q in found for p in q)"}')"
expect_contains "an LF edit to a CRLF file is applied and denied" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2" "$(reason)"

new_case unreadable
printf 'x = 1\n\xff\n' >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse Edit pages.py '{old_string: "x = 1", new_string: "y = 2"}')"
expect_contains "a file that is not UTF-8 is named" \
  "Notice: did not check pages.py: it is not UTF-8 text, so PostToolUse checks it" "$(context)"
hook <<<"$(tool_payload PostToolUse Edit pages.py '{}')"
expect_contains "and named again after the write" "Notice: did not check pages.py: it is not UTF-8 text" "$(context)"
hook <<<"$(write pages.py "$PAGES")"
expect_equal "a Write over a file that is not UTF-8 does not deny" "" "$(decision)"
expect_contains "but is still checked, and its findings are warnings" \
  "Notice: could not read the current pages.py: it is not UTF-8 text, so its findings are warnings." "$(context)"
printf '#!/usr/bin/env python3\nx = 0\n' >"$PROJECT/run"
hook <<<"$(tool_payload PreToolUse Edit run '{old_string: "not here", new_string: "y = 1"}')"
expect_contains "an unbuilt edit to an extensionless script is named" \
  "Notice: did not check run: could not build the text this edit leaves" "$(context)"

new_case non-code
hook <<<"$(write notes.md "$PAGES")"
expect_equal "a non-code file says nothing" "0:" "$STATUS:$STDOUT"
hook <<<"$(write main.go 'package main')"
expect_equal "a language with no guidelines says nothing" "0:" "$STATUS:$STDOUT"
hook <<<"$(write ../outside.py "$PAGES")"
expect_equal "a file outside the project says nothing" "0:" "$STATUS:$STDOUT"
hook <<<"$(write node_modules/pkg/pages.py "$PAGES")"
expect_equal "a vendored file says nothing" "0:" "$STATUS:$STDOUT"
hook <<<"$(write build/pages.py "$PAGES")"
expect_equal "a file in a root build directory says nothing" "0:" "$STATUS:$STDOUT"
hook <<<"$(write src/app/build/pages.py "$PAGES")"
expect_equal "a nested build directory is checked" deny "$(decision)"
hook <<<"$(write bin/pages "#!/usr/bin/env python3
$PAGES")"
expect_equal "an extensionless file with a python shebang is checked" deny "$(decision)"

new_case multi-edit
printf 'x = 1\n' >"$PROJECT/pages.py"
hook <<<"$(tool_payload PreToolUse MultiEdit pages.py '{edits: [{old_string: "x = 1", new_string: "y = 2"}, {old_string: "y = 2", new_string: "y = [a for b in c for a in b]"}]}')"
expect_contains "MultiEdit edits apply in order" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:1" "$(reason)"

new_case exclude
hook <<<"$(write tests/test_app.py 'assert x
')"
hook <<<"$(write src/app.py 'assert x
')"
expect_equal "an excluded guideline's detector is not selected" \
  "check --isolated --line-length 80 --select F403 --output-format json --stdin-filename $PROJECT/tests/test_app.py -
check --isolated --line-length 80 --select F403,S101 --output-format json --stdin-filename $PROJECT/src/app.py -" \
  "$(cat "$WORK/ruff.args")"

new_case disabled
hook RUFF_JSON='[{"code":"T201","location":{"row":1}}]' <<<"$(write src/app.py 'print("x")
')"
expect_equal "a disabled guideline's detector is not selected" \
  "check --isolated --line-length 80 --select F403,S101 --output-format json --stdin-filename $PROJECT/src/app.py -" \
  "$(cat "$WORK/ruff.args")"
expect_equal "a disabled guideline is never delivered" "" "$(grep -F py.logging.no-print <<<"$STDOUT")"

new_case project-default
hook RUFF_JSON="$F403_ROW" <<<"$(write src/app.py 'from os import *
')"
expect_equal "with no project config the default rule blocks" "$BLOCKED

[py.import.no-star] block: ruff:F403 at src/app.py:1
Import names explicitly; do not use \`from module import *\`." "$(reason)"

new_case project-ignores
printf '[lint]\nignore = ["F403"]\n' >"$PROJECT/ruff.toml"
hook RUFF_JSON="$F403_ROW" <<<"$(write src/app.py 'from os import *
')"
expect_equal "a rule the project ignores does not block" "" "$(decision)"
expect_equal "a rule the project ignores gives no finding" "" "$(grep -F py.import.no-star <<<"$STDOUT")"
expect_equal "ruff runs with the project config, without the ignored rule" \
  "check --verbose --force-exclude --extend-select S101 --output-format json --stdin-filename $PROJECT/src/app.py -" \
  "$(cat "$WORK/ruff.args")"
hook RUFF_JSON="$F403_ROW" RUFF_STDERR='DEBUG Ignored path via `exclude`: "src/dist"' \
  <<<"$(write src/dist/app.py 'assert x
')"
expect_equal "a file ruff's config excludes does not deny" "" "$(decision)"
expect_contains "and the user is told ruff skipped it" \
  "Notice: ruff skips this file under its exclude settings (the project's or ruff's defaults), so detectors ruff:S101 did not run." "$(context)"
printf '[lint]\nignore = ["F403"]\n' >"$PROJECT/ruff.toml"
hook RUFF_JSON="$F403_ROW" <<<"$(tool_payload PostToolUse Write src/app.py '{}')"
expect_equal "the ignored rule stays quiet after the write" "" "$(grep -F py.import.no-star <<<"$STDOUT")"
cp -r "$FIXTURES" "$WORK/two-detectors"
sed -i 's/^detectors: ruff:F403$/detectors: ruff:F403, code_quality:CQ001/' "$WORK/two-detectors/py-import-no-star.md"
rm "$WORK/two-detectors/py-comprehension-one-for.md"
hook PSTACK_GUIDELINES_DIR="$WORK/two-detectors" RUFF_JSON="$F403_ROW" <<<"$(write src/two.py 'x = [a for b in c for a in b]
')"
expect_contains "an ignored detector leaves the guideline's other detectors on" \
  "[py.import.no-star] block: code_quality:CQ001 at src/two.py:1" "$(reason)"
expect_equal "the ignored detector gives no finding" "" "$(grep -F 'ruff:F403 at' <<<"$(reason)")"

new_case project-pyproject
printf '[tool.ruff.lint.per-file-ignores]\n"src/*" = ["F403"]\n' >"$PROJECT/pyproject.toml"
hook RUFF_JSON="$F403_ROW" <<<"$(write src/app.py 'from os import *
')"
expect_equal "a per-file ignore in pyproject.toml does not block" "" "$(decision)"
hook RUFF_JSON="$F403_ROW" <<<"$(write lib.py 'from os import *
')"
expect_equal "the same rule still blocks outside the ignored path" deny "$(decision)"

new_case editorconfig
printf '[*]\nmax_line_length = 120\n' >"$PROJECT/.editorconfig"
hook <<<"$(write src/app.py 'x = 1
')"
expect_contains "the project's line length replaces the default" "--line-length 120 " "$(cat "$WORK/ruff.args")"

new_case missing-ruff
rm "$WORK/bin/ruff"
hook <<<"$(write src/app.py 'from os import *
')"
RUFF_NOTICE='Notice: ruff is not installed, so detectors ruff:F403, ruff:S101 did not run. Their guidelines apply as warnings.'
expect_contains "a missing tool is named in the context" "$RUFF_NOTICE" "$(context)"
expect_contains "its guideline follows as a warning" "[py.import.no-star] warn (detector unavailable)" "$(context)"
expect_equal "the user sees the same notice" "$RUFF_NOTICE" "$(jq -r .systemMessage <<<"$STDOUT")"
expect_equal "a missing tool never denies" "" "$(decision)"
hook <<<"$(write src/app.py 'from os import *
')"
expect_contains "the notice repeats on each call the tool is missing" "$RUFF_NOTICE" "$(context)"
expect_equal "the user is told only once" "null" "$(jq -r .systemMessage <<<"$STDOUT")"
cat >"$WORK/bin/ruff" <<'STUB'
#!/bin/sh
if [ "$1" = --version ]; then
  echo "${RUFF_VERSION:-ruff 0.16.9}"
  exit 0
fi
echo "$*" >>"$WORK/ruff.args"
cat >/dev/null
[ -n "$RUFF_SLEEP" ] && sleep "$RUFF_SLEEP"
[ -n "$RUFF_STDERR" ] && printf '%s\n' "$RUFF_STDERR" >&2
printf '%s\n' "${RUFF_JSON:-[]}"
STUB
chmod +x "$WORK/bin/ruff"

new_case wrong-program
hook RUFF_VERSION='Usage: sg group' <<<"$(write src/app.py 'x = 1
')"
expect_contains "another program under the tool's name is not run" \
  "Notice: ruff is not the expected program, so detectors" "$(context)"

new_case timeout
started=$SECONDS
hook RUFF_SLEEP=5 <<<"$(write src/app.py 'x = 1
')"
expect_contains "a slow tool is cut off and named" "Notice: ruff timed out after 1.5 s, so detectors" "$(context)"
expect_equal "the hook returns before the slow tool ends" yes "$([ $((SECONDS - started)) -lt 5 ] && echo yes)"

new_case eslint-missing
mv "$WORK/bin/eslint" "$WORK/eslint.stub"
hook <<<"$(write a.ts 'var x = 1
')"
expect_contains "missing eslint is named" "Notice: eslint is not installed" "$(context)"
expect_contains "the TypeScript guideline follows as a warning" "[ts.binding.no-var] warn (detector unavailable)" "$(context)"
expect_equal "missing eslint never denies" "" "$(decision)"
mv "$WORK/eslint.stub" "$WORK/bin/eslint"

new_case eslint-no-config
NO_VAR='[{"messages":[{"ruleId":"no-var","line":1}]}]'
hook ESLINT_JSON="$NO_VAR" <<<"$(write a.ts 'var x = 1
')"
expect_contains "eslint does not run without a project config" \
  "Notice: eslint has no project config, so detectors eslint:no-var did not run." "$(context)"
expect_equal "eslint was not started" "" "$(cat "$WORK/eslint.args" 2>/dev/null)"

new_case eslint-config
echo 'export default [];' >"$PROJECT/eslint.config.js"
hook ESLINT_JSON="$NO_VAR" <<<"$(write a.ts 'var x = 1
')"
expect_equal "eslint runs with the project's config and its hit blocks" "$BLOCKED

[ts.binding.no-var] block: eslint:no-var at a.ts:1
Declare bindings with \`const\`, or \`let\` when reassigned; never \`var\`." "$(reason)"
expect_equal "eslint gets no rule overrides" "--stdin --stdin-filename $PROJECT/a.ts -f json" "$(cat "$WORK/eslint.args")"

new_case dedupe
NESTED='x = [f(g(a)) for a in b]
'
printf '%s' "$NESTED" >"$PROJECT/pages.py"
hook <<<"$(tool_payload PostToolUse Write pages.py '{}')"
expect_contains "the first finding carries the guidance" "at pages.py:1
$NESTED_CALL" "$(context)"
for _ in $(seq 19); do hook <<<"$(prompt hello)"; done
expect_equal "an unrelated prompt says nothing" "" "$STDOUT"
hook <<<"$(tool_payload PostToolUse Write pages.py '{}')"
expect_contains "inside the window the guidance is not repeated" \
  "[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:1 (guidance sent earlier)" "$(context)"
hook <<<"$(prompt 'hello SECRET-PROMPT-WORD')"
hook <<<"$(tool_payload PostToolUse Write pages.py '{}')"
expect_contains "after 20 prompts the guidance is sent again" "at pages.py:1
$NESTED_CALL" "$(context)"
expect_equal "state never stores prompt text" "" "$(grep -rl SECRET-PROMPT-WORD "$WORK/data")"

new_case keyword
hook <<<"$(prompt 'flatten the lists in parser.py')"
expect_contains "a keyword with a language context fires" "[py.comprehension.one-for] warn
$ONE_FOR" "$(context)"
expect_contains "the file path in the prompt detects the language" "[py.data.dataclass-over-dict] warn" "$(context)"
new_case keyword-alone
hook <<<"$(prompt 'flatten the pancake')"
expect_equal "a keyword with no language context says nothing" "0:" "$STATUS:$STDOUT"

for case in "x.cs.pp csharp" "foo.rs.in rust" "X.PY python"; do
  read -r name language <<<"$case"
  expect_equal "$name is $language" "$language" "$(python3 -I "$ENGINE" --language "$name")"
done

new_case invalid
cp -r "$FIXTURES" "$WORK/with-bad"
printf -- '---\nid: bad\nlanguages: python\nscope: global\nenabled: true\ndetectors:\n---\nBody.\n' >"$WORK/with-bad/bad.md"
hook PSTACK_GUIDELINES_DIR="$WORK/with-bad" <<<"$(write pages.py "$EXPLICIT_LOOP")"
expect_contains "an invalid guideline file is skipped and named" \
  "Notice: skipped invalid guideline file bad.md: missing key severity" "$(context)"
expect_contains "the other guidelines still arrive" "[py.data.dataclass-over-dict] warn" "$(context)"

new_case crash
touch "$WORK/not-a-directory"
hook PSTACK_GUIDELINES_DIR="$WORK/not-a-directory" <<<"$(write pages.py "$PAGES")"
expect_equal "an engine failure exits 0" 0 "$STATUS"
expect_json "an engine failure tells the user and does not deny" \
  "{\"systemMessage\": \"pstack guideline hook failed; code-quality guidelines were not checked for this call. Details: $WORK/data/guideline-state/errors.log\"}" "$STDOUT"
expect_contains "the failure is logged" "NotADirectoryError" "$(cat "$WORK/data/guideline-state/errors.log")"
HARNESS=bogus hook <<<'{}'
expect_json "a wrapper-caught failure names the log it wrote" \
  "{\"systemMessage\": \"pstack guideline hook failed; code-quality guidelines were not checked for this call. Details: $WORK/data/guideline-state/errors.log\"}" "$STDOUT"
ln -s "$WORK/data" "$WORK/data-link"
HARNESS=bogus hook CLAUDE_PLUGIN_DATA="$WORK/data-link" <<<'{}'
expect_json "a wrapper that refuses a symlinked data directory names no log" \
  '{"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call."}' "$STDOUT"
rm "$WORK/data/guideline-state/errors.log"
: >"$WORK/victim"
ln -s "$WORK/victim" "$WORK/data/guideline-state/errors.log"
hook PSTACK_GUIDELINES_DIR="$WORK/not-a-directory" <<<"$(write pages.py "$PAGES")"
expect_json "a planted log symlink is refused and the user still hears of the failure" \
  '{"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call."}' "$STDOUT"
expect_equal "and the symlink target is untouched" "" "$(cat "$WORK/victim")"
HARNESS=bogus hook <<<'{}'
expect_json "a wrapper that refuses a log symlink names no log" \
  '{"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call."}' "$STDOUT"
expect_equal "and the wrapper leaves the symlink target untouched" "" "$(cat "$WORK/victim")"
rm "$WORK/data/guideline-state/errors.log"
mkfifo "$WORK/data/guideline-state/errors.log"
capture timeout 5 env PATH="$HOOK_PATH" bash "$HOOK" bogus <<<'{}'
expect_json "a wrapper does not stall on a log that is a FIFO" \
  '{"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call."}' "$STDOUT"
capture timeout 5 env PATH="$HOOK_PATH" PSTACK_GUIDELINES_DIR="$WORK/not-a-directory" \
  bash "$HOOK" claude <<<"$(write pages.py "$PAGES")"
expect_json "the engine does not stall on a log that is a FIFO" \
  '{"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call."}' "$STDOUT"
rm "$WORK/data/guideline-state/errors.log"
hook <<<'not json'
expect_equal "a malformed payload says nothing" "0:" "$STATUS:$STDOUT"
hook <<<'{"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": 7, "tool_input": {"file_path": ["a.py"], "content": 3}}'
expect_equal "a payload with wrong types says nothing" "0:" "$STATUS:$STDOUT"

new_case no-python
PYTHON_NOTICE='Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session.'
capture env PATH="$WORK/tools" bash "$HOOK" claude <<<"$(session_start startup)"
expect_equal "without Python the session start tells the user" "$PYTHON_NOTICE" "$(jq -r .systemMessage <<<"$STDOUT")"
expect_equal "and tells the agent" "$PYTHON_NOTICE" "$(context)"
capture env PATH="$WORK/tools" bash "$HOOK" claude <<<"$(write pages.py "$PAGES")"
expect_equal "without Python other hooks stay quiet" "0:" "$STATUS:$STDOUT"

claude_config="$PLUGIN_ROOT_DIR/hooks/hooks.json"
wired() { jq -c "[.hooks.$2[] | {matcher, hooks: [.hooks[] | select(.command | contains(\"guidelines.sh\")) | [.command, .timeout]]}]" "$1"; }
claude_command='bash \"${CLAUDE_PLUGIN_ROOT}/hooks/guidelines.sh\" claude'
expect_equal "Claude Code SessionStart wiring" \
  "[{\"matcher\":\"startup|resume|clear|compact\",\"hooks\":[[\"$claude_command\",5]]}]" "$(wired "$claude_config" SessionStart)"
expect_equal "Claude Code UserPromptSubmit wiring" \
  "[{\"matcher\":null,\"hooks\":[[\"$claude_command\",5]]}]" "$(wired "$claude_config" UserPromptSubmit)"
expect_equal "Claude Code PreToolUse wiring" \
  "[{\"matcher\":\"Write|Edit|MultiEdit\",\"hooks\":[[\"$claude_command\",10]]}]" "$(wired "$claude_config" PreToolUse)"
expect_equal "Claude Code PostToolUse wiring" \
  "[{\"matcher\":\"Read|Write|Edit|MultiEdit\",\"hooks\":[[\"$claude_command\",15]]}]" "$(wired "$claude_config" PostToolUse)"
new_case wired
while IFS= read -r command; do
  run_wiring claude "$command" <<<"$(write pages.py "$PAGES")"
done < <(wiring_commands claude "$claude_config" PreToolUse)
expect_equal "the wired Claude Code command denies the flattening comprehension" deny "$(decision)"

HARNESS=codex
codex_config="$PLUGIN_ROOT_DIR/hooks/codex-hooks.json"
codex_command='\"${CLAUDE_PLUGIN_ROOT}/hooks/guidelines.sh\" codex'
expect_equal "Codex PreToolUse wiring" \
  "[{\"matcher\":\"apply_patch\",\"hooks\":[[\"$codex_command\",10]]}]" "$(wired "$codex_config" PreToolUse)"
expect_equal "Codex PostToolUse wiring" \
  "[{\"matcher\":\"apply_patch\",\"hooks\":[[\"$codex_command\",15]]}]" "$(wired "$codex_config" PostToolUse)"
expect_equal "Codex UserPromptSubmit wiring" \
  "[{\"matcher\":null,\"hooks\":[[\"$codex_command\",5]]}]" "$(wired "$codex_config" UserPromptSubmit)"

# patch_payload EVENT PATCH
patch_payload() {
  jq -cn --arg e "$1" --arg s "$SESSION" --arg c "$PROJECT" --arg p "$2" \
    '{hook_event_name: $e, session_id: $s, cwd: $c, tool_name: "apply_patch", tool_input: {command: $p}}'
}
new_case codex-add
hook <<<"$(patch_payload PreToolUse '*** Begin Patch
*** Add File: pages.py
+def pages(paths):
+    return tuple(page for path in paths for page in parse_page(_read(path)))
*** End Patch')"
expect_equal "a Codex patch that adds the violation is denied" "$PAGES_REASON" "$(reason)"
printf '%s\xff\n' "$PAGES" >"$PROJECT/pages.py"
hook <<<"$(patch_payload PreToolUse '*** Begin Patch
*** Add File: pages.py
+def pages(paths):
+    return tuple(page for path in paths for page in parse_page(_read(path)))
*** End Patch')"
expect_equal "a Codex Add File over a file that is not UTF-8 does not deny" "" "$(decision)"
expect_contains "and its findings are warnings" \
  "Notice: could not read the current pages.py: it is not UTF-8 text, so its findings are warnings." "$(context)"

new_case codex-update
printf '%s' "$EXPLICIT_LOOP" >"$PROJECT/pages.py"
UPDATE='*** Begin Patch
*** Update File: pages.py
@@ def pages(paths):
     print(len(found))
-    return tuple(found)
+    return tuple(p for q in found for p in q)
*** End Patch'
hook <<<"$(patch_payload PreToolUse "$UPDATE")"
expect_contains "a Codex update hunk is applied in memory and denied" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:7" "$(reason)"
printf '%s' "$PAGES" >"$PROJECT/pages.py"
hook <<<"$(patch_payload PostToolUse "$UPDATE")"
expect_contains "after a Codex patch the file's findings arrive as warnings" \
  "[py.comprehension.one-for] warn: code_quality:CQ001 at pages.py:2" "$(context)"

new_case codex-no-apply
printf 'x = 1\n' >"$PROJECT/pages.py"
hook <<<"$(patch_payload PreToolUse "$UPDATE")"
expect_contains "a Codex patch that does not apply is named" "Notice: did not check pages.py: could not build the text this edit leaves, so PostToolUse checks it" "$(context)"
expect_equal "and is not denied" "" "$(decision)"

new_case codex-whitespace
printf 'def pages(paths):  \r\n    return tuple(found)\r\n' >"$PROJECT/pages.py"
hook <<<"$(patch_payload PreToolUse '*** Begin Patch
*** Update File: pages.py
@@
 def pages(paths):
-    return tuple(found)
+    return tuple(p for q in found for p in q)
*** End Patch')"
expect_contains "a Codex hunk matches past trailing whitespace and CRLF" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2" "$(reason)"
HARNESS=claude

new_case neutral
neutral=$(jq -cn --arg c "$PROJECT" --arg text "$PAGES" \
  '{kind: "pre_write", session: "n1", agent: "main", cwd: $c, root: $c, files: [{path: "pages.py", before: null, after: $text}]}')
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" --harness neutral <<<"$neutral"
expect_json "the neutral core returns the deny text" \
  "$(jq -cn --arg d "$PAGES_REASON" '{deny: $d, context: null, notice: null}')" "$STDOUT"
neutral=$(jq -c '.channel = false | .files[0].after = "x = 1\n" | .session = "n2"' <<<"$neutral")
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" --harness neutral <<<"$neutral"
expect_json "with no context channel the globals wait" '{"deny": null, "context": null, "notice": null}' "$STDOUT"
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" --harness neutral \
  <<<"$(jq -c '.channel = true | .kind = "post_write"' <<<"$neutral")"
expect_equal "and arrive on the next call that has one" "$GLOBALS_CONTEXT" "$(jq -r .context <<<"$STDOUT")"

new_case check
printf '%s' "$PAGES" >"$PROJECT/pages.py"
cd "$PROJECT" || exit 1
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" check pages.py
expect_equal "check exits 1 on a block finding" 1 "$STATUS"
expect_equal "check prints findings, guidelines, and the override line" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2
$ONE_FOR

[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:2
$NESTED_CALL

[py.data.dataclass-over-dict] warn
$DATACLASS

$OVERRIDE
" "$STDOUT"
printf '%s' "$EXPLICIT_LOOP" >"$PROJECT/pages.py"
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" check pages.py
expect_equal "check exits 0 on a clean file" 0 "$STATUS"
mkdir -p build && printf '%s' "$PAGES" >build/b.py
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" check gone.py build/b.py pages.py
expect_equal "check exits 3 on a missing path" 3 "$STATUS"
expect_contains "check names the missing path" "Notice: did not check gone.py: no such file" "$STDOUT"
expect_contains "check names an excluded path" \
  "Notice: did not check build/b.py: it is in a dependency or build directory" "$STDOUT"
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" check build nope.txt
expect_equal "check exits 3 on a directory" 3 "$STATUS"
expect_contains "check names a directory" "Notice: did not check build: it is a directory" "$STDOUT"
expect_contains "check names a missing file of any type" "Notice: did not check nope.txt: no such file" "$STDOUT"
mkfifo queue.py
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" check queue.py
expect_equal "check exits 3 on a special file" 3 "$STATUS"
expect_contains "check names a special file" "Notice: did not check queue.py: it is not a regular file" "$STDOUT"
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" --harness unknown </dev/null
expect_equal "a usage error never exits 2, which Codex reads as a block" 64 "$STATUS"

new_case truncated
guideline py-types-mypy.md 'Type every function.' 'id: py.types.mypy' 'languages: python' \
  'scope: contextual' 'severity: warn' 'enabled: true' 'detectors: mypy:X'
many="$(for i in $(seq 400); do echo "x$i = [a for b in c for a in b]"; done)"
hook <<<"$(write many.py "$many")"
expect_contains "findings past the size cap are counted" \
  "more findings did not fit in this message. Run the check command on many.py to see all of them." "$(reason)"
expect_contains "a denial full of findings still names the detector that did not run" \
  "Notice: mypy has no runner yet, so detectors mypy:X did not run." "$(reason)"
expect_equal "the denial stays inside the size cap" yes "$([ "$(reason | wc -c)" -le 9000 ] && echo yes)"
printf '%s\n' "$many" >"$PROJECT/many.py"
cd "$PROJECT"
capture env PATH="$HOOK_PATH" python3 -I "$ENGINE" check many.py
expect_equal "check shows every finding" 400 "$(grep -c '^\[py.comprehension.one-for\] block' <<<"$STDOUT")"
long="$(printf 'n%.0s' $(seq 160))"
patch=$'*** Begin Patch\n*** Update File: many.py\n@@\n-x1 = [a for b in c for a in b]\n+x1 = [a for b in c for a in b]'
for i in $(seq 49); do
  printf 'x = 1\xff\n' >"$PROJECT/${long}_$i.py"
  patch+=$'\n'"*** Update File: ${long}_$i.py"$'\n@@\n-x = 1\n+x = 2'
done
HARNESS=codex hook <<<"$(patch_payload PostToolUse "$patch")"
expect_contains "a context full of notices still counts the findings" "more findings did not fit" "$(context)"
expect_equal "and stays inside the size cap" yes "$([ "$(context | wc -c)" -le 9000 ] && echo yes)"

new_case huge-guideline
cp "$FIXTURES/py-comprehension-one-for.md" "$WORK/one-for.md"
guideline py-comprehension-one-for.md "$(printf 'x%.0s' $(seq 8400))" 'id: py.comprehension.one-for' \
  'languages: python' 'scope: contextual' 'severity: block' 'enabled: true' 'detectors: code_quality:CQ001'
hook <<<"$(write pages.py "$PAGES")"
expect_contains "a denial whose guideline does not fit still names the rule and line" \
  "[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2" "$(reason)"
expect_contains "a denial keeps the detector-unavailable notice" \
  "Notice: mypy has no runner yet, so detectors mypy:X did not run." "$(reason)"
expect_equal "and stays inside the size cap" yes "$([ "$(reason | wc -c)" -le 9000 ] && echo yes)"
mv "$WORK/one-for.md" "$FIXTURES/py-comprehension-one-for.md"
rm "$FIXTURES/py-types-mypy.md"

finish
