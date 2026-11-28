#!/bin/bash
# The skill-quality verification script passes a clean skill and fails each
# smell it owns.

PLUGIN_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

lint="$PLUGIN_ROOT_DIR/skills/skill-quality/scripts/lint-skills.sh"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# skill NAME DESCRIPTION BODY: writes a fresh skill and prints its directory.
skill() {
  local dir="$WORK/$1"
  rm -rf "$dir"
  mkdir -p "$dir/references"
  printf -- '---\nname: %s\ndescription: %s\n---\n\n%s\n' "$1" "$2" "$3" >"$dir/SKILL.md"
  printf '%s\n' "$dir"
}
good="Checks widgets. Use when a widget breaks."

dir=$(skill clean "$good" "Read [the guide](references/guide.md) when a widget breaks.")
printf '# Guide\n' >"$dir/references/guide.md"
run_hook "$lint" "$dir"
expect_equal "a clean skill exits 0" 0 "$STATUS"
expect_contains "a clean skill has no warnings" "0 failed, 0 warnings" "$STDOUT"

dir=$(skill orphan "$good" "Read [the index](references/README.md).")
printf '[guide](guide.md)\n' >"$dir/references/README.md"
printf '# Guide\n' >"$dir/references/guide.md"
run_hook "$lint" "$dir"
expect_equal "a reference linked only from a README fails" 1 "$STATUS"
expect_contains "the orphan is named" "FAIL  references/guide.md: no link" "$STDOUT"
run_hook "${lint%/*}/checks/orphan-references.sh" "$dir"
expect_equal "the orphan check fails on its own" 1 "$STATUS"
run_hook "${lint%/*}/checks/links.sh" "$dir"
expect_equal "the links check passes on its own" "0 " "$STATUS $STDOUT"

dir=$(skill licensed "$good" "Read [the guide](references/guide.md).")
printf '# Guide\n' >"$dir/references/guide.md"
mkdir -p "$dir/references/licenses"
printf 'MIT\n' >"$dir/references/licenses/NOTICE.md"
printf 'MIT\n' >"$dir/references/LICENSE.md"
printf 'MIT\n' >"$dir/references/notice-apache.md"
run_hook "${lint%/*}/checks/orphan-references.sh" "$dir"
expect_equal "unlinked license and notice files are not orphans" "0 " "$STATUS $STDOUT"
printf '# Stray\n' >"$dir/references/licensed-notes.md"
run_hook "${lint%/*}/checks/orphan-references.sh" "$dir"
expect_equal "a reference whose name only starts like license still fails" 1 "$STATUS"
rm "$dir/references/licensed-notes.md"
mkdir -p "$dir/references/LICENSE-notes"
printf '# Stray\n' >"$dir/references/LICENSE-notes/guide.md"
run_hook "${lint%/*}/checks/orphan-references.sh" "$dir"
expect_equal "a file inside a LICENSE-named folder still fails" 1 "$STATUS"

dir=$(skill folder "$good" "Read [examples](references/) when a widget breaks.")
printf '# Guide\n' >"$dir/references/guide.md"
run_hook "$lint" "$dir"
expect_equal "a link to the directory reaches its files" 0 "$STATUS"

dir=$(skill deep "$good" "Read [a](references/a.md).")
printf '[b](b.md)\n' >"$dir/references/a.md"
printf '# B\n' >"$dir/references/b.md"
run_hook "$lint" "$dir"
expect_contains "a reference two links deep warns" "WARN  references/b.md: this file is 2 links" "$STDOUT"

dir=$(skill broken "$good" 'Run `scripts/missing.sh`. See [x](references/nope.md). Read `references/<topic>.md`.')
run_hook "$lint" "$dir"
expect_contains "a missing backticked script fails" "link to scripts/missing.sh does not resolve" "$STDOUT"
expect_contains "a missing linked file fails" "link to references/nope.md does not resolve" "$STDOUT"
expect_equal "a placeholder path is not a link" "" "$(grep '<topic>' <<<"$STDOUT")"

dir=$(skill wrong-name "Has <b>tags</b>. Use when testing." 'Open references\guide.md.')
sed 's/^name: .*/name: Other_Name/' "$dir/SKILL.md" >"$WORK/tmp" && mv "$WORK/tmp" "$dir/SKILL.md"
run_hook "$lint" "$dir"
expect_contains "a name that is not the directory fails" "is not the directory name" "$STDOUT"
expect_contains "a name with capitals fails" "has characters other than" "$STDOUT"
expect_contains "XML in the description fails" "description has an XML tag" "$STDOUT"
expect_contains "a backslash path fails" "has a backslash path" "$STDOUT"

dir=$(skill long "Use this to check widgets." "$(printf 'word %.0s' $(seq 5001))")
run_hook "$lint" "$dir"
expect_contains "a body over 5,000 words fails" "body is 5001 words" "$STDOUT"
expect_contains "a description that starts with Use warns" "not third person" "$STDOUT"

dir=$(skill tall "$good" "$(printf 'Line.\n%.0s' $(seq 501))")
run_hook "$lint" "$dir"
expect_contains "a body over 500 lines warns" "WARN  SKILL.md: body is 502 lines, over 500" "$STDOUT"
expect_equal "a body over 500 lines still passes" 0 "$STATUS"
dir=$(skill short "$good" "$(printf 'Line.\n%.0s' $(seq 499))")
run_hook "${lint%/*}/checks/body-length.sh" "$dir"
expect_equal "a body of 500 lines adds nothing" "0 " "$STATUS $STDOUT"

dir=$(skill nowhen "Checks widgets." "Body.")
run_hook "$lint" "$dir"
expect_contains "a description with no trigger warns" "does not say when" "$STDOUT"

dir=$(skill forms "$good" 'Read [t](references/t.md "Title"), [s](references/my%20ref.md) and [a](<references/a b.md>). Write links like `[x](references/nope.md)`. See `forms/references/p.md`. Run from the plugin'"'"'s `scripts/` folder.')
for f in t "my ref" "a b" p; do printf '# Ref\n' >"$dir/references/$f.md"; done
run_hook "$lint" "$dir"
expect_contains "titled, encoded, angle and name-prefixed links resolve; inline code and bare folders are skipped" \
  "$dir: 0 failed, 0 warnings" "$STDOUT"

dir=$(skill crlf "$good" "Body.")
awk '{ printf "%s\r\n", $0 }' "$dir/SKILL.md" >"$WORK/tmp" && mv "$WORK/tmp" "$dir/SKILL.md"
run_hook "$lint" "$dir"
expect_equal "a SKILL.md with CRLF line endings passes" 0 "$STATUS"

shape="${lint%/*}/checks/playbook-shape.sh"
# shaped KIND BODY: a skill whose references/p.md has that shape and body.
shaped() {
  local dir
  dir=$(skill shaped "$good" "Read [p](references/p.md) when a widget breaks.")
  printf -- '---\nshape: %s\n---\n\n%s\n' "$1" "$2" >"$dir/references/p.md"
  printf '%s\n' "$dir"
}
playbook=$'1. Read the log. Expect the error line.\n2. Fix it. Expect the test to pass.\n\nDone when the test passes.\n\n**Reply:** cause, fix.'

dir=$(shaped playbook "$playbook")
run_hook "$lint" "$dir"
expect_contains "a playbook with a stop predicate and a Reply line passes" "$dir: 0 failed, 0 warnings" "$STDOUT"

dir=$(shaped playbook "${playbook/Done when/Finish}")
run_hook "$shape" "$dir"
expect_equal "a playbook with no stop predicate warns and passes" 0 "$STATUS"
expect_contains "the stop predicate is named" "WARN  references/p.md: playbook has no stop predicate" "$STDOUT"
for stop in Stop Stops Done Exit Exits Finish Finished Complete Completed End Ends '**Done**' $'The run is done\n'; do
  dir=$(shaped playbook "${playbook/Done when/$stop when}")
  run_hook "$shape" "$dir"
  expect_equal "'$stop when' is a stop predicate" "0 " "$STATUS $STDOUT"
done
for connector in if once after; do
  dir=$(shaped playbook "${playbook/Done when/Done $connector}")
  run_hook "$shape" "$dir"
  expect_equal "'Done $connector' is a stop predicate" "0 " "$STATUS $STDOUT"
done

dir=$(shaped playbook "${playbook/\*\*Reply:\*\*/Report}")
run_hook "$shape" "$dir"
expect_equal "a playbook with no Reply label fails" 1 "$STATUS"
expect_contains "the Reply label is named" "FAIL  references/p.md: playbook has no Reply label" "$STDOUT"
for reply in '**Reply**:' '- **Reply:**' '__Reply:__' 'Reply:' $'## Reply\n\n' '> **Reply:**'; do
  dir=$(shaped playbook "${playbook/\*\*Reply:\*\*/$reply}")
  run_hook "$shape" "$dir"
  expect_equal "'$reply' is a Reply label" "0 " "$STATUS $STDOUT"
done
dir=$(shaped playbook "${playbook/\*\*Reply:\*\* cause, fix./The reply names the cause.}")
run_hook "$shape" "$dir"
expect_equal "the word reply inside a sentence is not a label" 1 "$STATUS"
dir=$(shaped playbook "${playbook/\*\*Reply:\*\* cause, fix./Reply with the cause.}")
run_hook "$shape" "$dir"
expect_equal "Reply followed by more words is not a label" 1 "$STATUS"
dir=$(shaped Playbook "${playbook/\*\*Reply:\*\*/Report}")
run_hook "$shape" "$dir"
expect_contains "the shape value is read in any case" "FAIL  references/p.md: playbook has no Reply label" "$STDOUT"
awk '{ printf "%s\r\n", $0 }' "$dir/references/p.md" >"$WORK/tmp" && mv "$WORK/tmp" "$dir/references/p.md"
run_hook "$shape" "$dir"
expect_contains "a shaped file with CRLF line endings is checked" "FAIL  references/p.md: playbook has no Reply label" "$STDOUT"

dir=$(skill unclosed "$good" "Read [p](references/p.md) when a widget breaks.")
printf -- '---\n\n# Title under a rule\n\nshape: playbook\n\n1. Fix it.\n' >"$dir/references/p.md"
run_hook "$shape" "$dir"
expect_equal "a shape line in a frontmatter that never closes is skipped" "0 " "$STATUS $STDOUT"
printf -- 'Intro.\n\nshape: playbook\n\n1. Fix it.\n' >"$dir/references/p.md"
run_hook "$shape" "$dir"
expect_equal "a shape line with no frontmatter is skipped" "0 " "$STATUS $STDOUT"
printf -- '---\ndescription: >-\n  Draws each\n  shape: playbook of it.\n---\n\n1. Fix it.\n' >"$dir/references/p.md"
run_hook "$shape" "$dir"
expect_equal "a shape line inside another value is skipped" "0 " "$STATUS $STDOUT"
printf -- '---\nshape: playbook # the kind\n---\n\n1. Fix it.\n' >"$dir/references/p.md"
run_hook "$shape" "$dir"
expect_contains "a YAML comment after the shape is ignored" "FAIL  references/p.md: playbook has no Reply label" "$STDOUT"

dir=$(shaped playbook "$playbook"$'\n3. Retry the build until it passes.')
run_hook "$shape" "$dir"
expect_contains "a loop with no limit warns" "WARN  references/p.md: line 11 has a loop with no limit" "$STDOUT"
expect_equal "a loop with no limit still passes" 0 "$STATUS"
dir=$(shaped playbook "$playbook"$'\n3. Retry the build at most 3 times.')
run_hook "$shape" "$dir"
expect_equal "a loop with a limit adds nothing" "0 " "$STATUS $STDOUT"
dir=$(shaped playbook "$playbook"$'\nUse for "run until done". Not for one fix; see diagnose-loop.')
run_hook "$shape" "$dir"
expect_equal "loop words in quotes or in a hyphenated name add nothing" "0 " "$STATUS $STDOUT"
for loop in '3. Run the test again.' $'## Retry policy\n' $'3. Retry the build until it passes,\n   at most 3 times.' \
  '3. Repeat steps 1 and 2 at most <N> times, until the test passes.' '3. Retry the build at most ten times.' \
  '3. Retry the build, 3 rounds in all.' '3. Retry the build for 3 tries.' '3. Retry the build for 3 attempts.' \
  '3. Do not merge until the review passes.' '3. Keep the copy until step 6.' '3. Retry once.' '3. Retry twice.' \
  '3. Do not edit README.md until the review passes.' "3. Don't merge until the review passes." \
  '3. Don’t merge until the review passes.' '3. Never merge until the review passes.' \
  '3. You must not merge until the review passes.' '3. Retry once more.' \
  "3. Don't build and deploy until review passes." '3. Do not merge, even on a green build, until review passes.' \
  '3. Do not, under any circumstances, merge until review passes.' \
  '3. Never merge before CI passes, until the owner signs off.' '3. Keep the branch until step 6 passes.' \
  '3. Never skip a test, and run the suite until it passes.' '3. Poll until step 4 succeeds.'; do
  dir=$(shaped playbook "$loop"$'\n'"$playbook")
  run_hook "$shape" "$dir"
  expect_equal "'$loop' adds nothing" "0 " "$STATUS $STDOUT"
done
for loop in '3. Repeat steps 1 and 2 until the test passes.' '3. Retry until the cache is up to date.' \
  '3. Loop to maximize coverage.' '3. Go back to step one.' '3. Run the tests until they pass.' \
  '3. Retry the build, and stop once it passes.' '3. Never skip a test. Run the suite until it passes.' \
  '3. Do not stop; run the suite until it passes.' '3. Run the suite until it passes, at least once.' \
  '3. Run the suite until it passes all at once.' '3. Wait until CI is green.' \
  '3. Retry once it is green.' '3. Retry until green, once per file.'; do
  dir=$(shaped playbook "$loop"$'\n'"$playbook")
  run_hook "$shape" "$dir"
  expect_contains "'$loop' warns" "WARN  references/p.md: line 5 has a loop with no limit" "$STDOUT"
done

dir=$(shaped playbook "$playbook"$'\n'"$(printf '%s. Step.\n' $(seq 3 11))")
run_hook "$shape" "$dir"
expect_contains "a playbook over 10 steps warns" "playbook has 11 steps, over 10" "$STDOUT"
dir=$(shaped playbook "$playbook"$'\n'"$(printf '%s. Step.\n' $(seq 3 10))")
run_hook "$shape" "$dir"
expect_equal "a playbook of 10 steps adds nothing" "0 " "$STATUS $STDOUT"

router=$'- Use for "fix": read [fix](fix.md).\n- Use for "ship": read `references/ship.md`.\n\nDefault: ask which one.'
dir=$(shaped router "$router")
printf '# Fix\n' >"$dir/references/fix.md"
printf '# Ship\n' >"$dir/references/ship.md"
run_hook "$shape" "$dir"
expect_equal "a router whose routes exist and that has a default passes" "0 " "$STATUS $STDOUT"
rm "$dir/references/ship.md"
run_hook "$shape" "$dir"
expect_contains "a route to a missing file fails" "FAIL  references/p.md: line 6 routes to references/ship.md, which does not exist" "$STDOUT"
rm "$dir/references/fix.md"
printf '# Ship\n' >"$dir/references/ship.md"
run_hook "$shape" "$dir"
expect_contains "a Markdown-link route to a missing file fails" "FAIL  references/p.md: line 5 routes to fix.md, which does not exist" "$STDOUT"
printf '# Fix\n' >"$dir/references/fix.md"
printf '\nSee [the notes](gone.md) for background.\n\n- Run `scripts/gone.sh` first.\n' >>"$dir/references/p.md"
run_hook "$shape" "$dir"
expect_equal "a paragraph link and a non-.md list target are not routes" "0 " "$STATUS $STDOUT"

dir=$(shaped router "$router"$'\n\n- Update `CHANGELOG.md`. Write a route as `[name](name.md)`.\n- "two": read [two](my%20file.md).')
printf '# Ref\n' >"$dir/references/fix.md"
printf '# Ref\n' >"$dir/references/ship.md"
printf '# Ref\n' >"$dir/references/my file.md"
run_hook "$shape" "$dir"
expect_equal "inline code and an encoded space in a route are read as links.sh reads them" "0 " "$STATUS $STDOUT"

dir=$(shaped router "${router/Default: ask which one./Ask which one.}")
printf '# Fix\n' >"$dir/references/fix.md"
printf '# Ship\n' >"$dir/references/ship.md"
run_hook "$shape" "$dir"
expect_equal "a router with no Default label fails" 1 "$STATUS"
expect_contains "the Default label is named" "FAIL  references/p.md: router has no Default label" "$STDOUT"
for default in '**Default:** ask.' '- Default route: ask.' $'## Default\n\nAsk.'; do
  dir=$(shaped router "${router/Default: ask which one./$default}")
  printf '# Fix\n' >"$dir/references/fix.md"
  printf '# Ship\n' >"$dir/references/ship.md"
  run_hook "$shape" "$dir"
  expect_equal "'$default' is a Default label" "0 " "$STATUS $STDOUT"
done

dir=$(shaped flow "No steps.")
run_hook "$shape" "$dir"
expect_contains "an unknown shape warns" "shape 'flow' is not playbook or router" "$STDOUT"

dir=$(skill unshaped "$good" "Read [p](references/p.md) when a widget breaks.")
printf '1. Retry until done.\n' >"$dir/references/p.md"
run_hook "$shape" "$dir"
expect_equal "a file with no shape is skipped" "0 " "$STATUS $STDOUT"

dir=$(skill meta "$good" "1. Fix it.")
printf -- '---\nname: meta\ndescription: %s\nmetadata:\n  shape: playbook\n---\n\n1. Fix it.\n' "$good" >"$dir/SKILL.md"
run_hook "$shape" "$dir"
expect_contains "a shape under metadata in SKILL.md is checked" "FAIL  SKILL.md: playbook has no Reply label" "$STDOUT"

for template in "$PLUGIN_ROOT_DIR"/skills/skill-quality/examples/*.md; do
  expect_contains "${template##*/} declares a shape" "shape: " "$(head -n 5 "$template")"
  expect_equal "${template##*/} has 25 lines or fewer" "" "$(awk 'NR == 26 { print FILENAME }' "$template")"
  dir=$(skill template "$good" "Read [p](references/p.md) when a widget breaks.")
  cp "${template%/*}"/*.md "$dir/references/" # the router links its siblings
  cp "$template" "$dir/references/p.md"
  run_hook "$shape" "$dir"
  expect_equal "${template##*/} passes the shape check" "0 " "$STATUS $(grep -F 'references/p.md' <<<"$STDOUT")"
done
run_hook "$shape" "$PLUGIN_ROOT_DIR/skills/skill-quality"
expect_equal "the six templates pass the shape check" "0 6" "$STATUS $(ls "$PLUGIN_ROOT_DIR"/skills/skill-quality/examples/*.md | wc -l | tr -d ' ')"

# A playbook beside SKILL.md, as the router template places it, is checked:
# the waitcap reproduction from the phase 4 eval.
waitcap=$'---\nshape: playbook\n---\n\n# X\n\n1. Push the branch. Expect it on origin.\n2. Wait until the PR is merged.\n3. Retry the push until it works.\n\nDone when the PR is merged.\n\n**Reply:** result.'
dir=$(skill waitcap "$good" "Read [x](x.md) when needed.")
printf '%s\n' "$waitcap" >"$dir/x.md"
run_hook "$lint" "$dir"
expect_equal "a playbook beside SKILL.md warns on each loop" "WARN  x.md: line 8 has a loop with no limit
WARN  x.md: line 9 has a loop with no limit" "$(grep -E '^(FAIL|WARN)' <<<"$STDOUT")"
expect_contains "a playbook beside SKILL.md is counted" "0 failed, 2 warnings" "$STDOUT"

dir=$(skill waitcap "$good" "Read [x](references/x.md) when needed.")
printf '%s\n' "$waitcap" >"$dir/references/x.md"
run_hook "$lint" "$dir"
expect_contains "a playbook under references/ is checked once" "0 failed, 2 warnings" "$STDOUT"

dir=$(skill waitcap "$good" "Read [x](deep/er/x.md) and [y](deep/my play.md) when needed.")
mkdir -p "$dir/deep/er"
printf '%s\n' "$waitcap" >"$dir/deep/er/x.md"
printf '%s\n' "$waitcap" >"$dir/deep/my play.md"
printf '%s\n' "${waitcap/shape: playbook/title: x}" >"$dir/plain.md"
printf '%s\n' "$waitcap" >"$WORK/outside.md"
ln -s "$WORK/outside.md" "$dir/linked.md"
run_hook "$shape" "$dir"
expect_equal "an opted-in file at any depth or with a space is checked; others are not" "WARN  deep/er/x.md: line 8 has a loop with no limit
WARN  deep/er/x.md: line 9 has a loop with no limit
WARN  deep/my play.md: line 8 has a loop with no limit
WARN  deep/my play.md: line 9 has a loop with no limit" "$(grep -E '^(FAIL|WARN)' <<<"$STDOUT")"

run_hook "$lint" "$PLUGIN_ROOT_DIR/skills/skill-quality"
expect_equal "skill-quality passes its own verification" 0 "$STATUS"

finish
