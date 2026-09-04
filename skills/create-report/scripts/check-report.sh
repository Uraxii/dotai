#!/usr/bin/env bash
# Diffs a report's deviations block and format-elements note against its
# sibling scoreboard, <report-name>.checks.md. Design:
# .nikki-agents/deviations-mechanism-design.md.
# Run: bash <this-skill-directory>/scripts/check-report.sh <report.md> <materials-dir>
set -euo pipefail

fail() {
	echo "FAIL: $1" >&2
	exit 1
}

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COLLISIONS="$SKILL_DIR/references/collisions.md"
CHECK_COUNT=23
# ponytail: difflib run-grouping over case- and whitespace-normalized tokens.
# Ceiling: it joins matched runs separated by insertions of up to
# RUN_GAP_WORDS, so padding a paste with "[sic]" no longer hides it, but a
# rewrite that changes more than that between runs still passes. Real
# paraphrase detection needs semantic matching, which this is not.
VERBATIM_SPAN_WORDS=40
MIN_RUN_WORDS=12
RUN_GAP_WORDS=20
QUESTION_EXEMPT_MAX_WORDS=80

# ---- selftest fixtures -----------------------------------------------------
# Fixtures live here, not under skills/ or .nikki-agents/: the former trips
# the orphan check in scripts/verify-plugin.sh, the latter is gitignored and
# proves nothing to a downstream reviewer. This --selftest run is the
# rerunnable artifact.

scoreboard_rows() {
	# Prints 23 scoreboard rows, all "met" by default.
	# Args, any order: "SKIP=N" drops row N. "DUP=N" prints row N twice.
	# "N=<full row line>" replaces row N's line.
	local skip="" dup="" arg n line
	declare -A custom=()
	for arg in "$@"; do
		case "$arg" in
		SKIP=*) skip="${arg#SKIP=}" ;;
		DUP=*) dup="${arg#DUP=}" ;;
		*=*) custom["${arg%%=*}"]="${arg#*=}" ;;
		esac
	done
	for n in $(seq 1 "$CHECK_COUNT"); do
		[ "$n" = "$skip" ] && continue
		line="${custom[$n]:-}"
		[ -n "$line" ] || line=$(printf '| %d | met | | | |' "$n")
		printf '%s\n' "$line"
		[ "$n" = "$dup" ] && printf '%s\n' "$line"
	done
}

board() {
	# $1 = Format: value, rest = scoreboard_rows args.
	local fmt="$1"
	shift
	printf 'Format: %s\n\n' "$fmt"
	printf '| check | verdict | authoriser | quoted rule | reader loses |\n'
	printf '|---|---|---|---|---|\n'
	scoreboard_rows "$@"
}

clean_report() {
	cat <<'EOF'
The proposal saves money and time, so it is approved.

## Body

Detail.

## Sources

- Example Source, 2026.
EOF
}

span_words() {
	# Prints $1 distinct tokens ("span01 span02 ..."), for verbatim-span
	# fixtures. Distinct from clean_report's own words so a match can only
	# come from the fixture's own planted span.
	local n="$1" i out=""
	for i in $(seq 1 "$n"); do
		out="$out span$(printf '%02d' "$i")"
	done
	printf '%s' "${out# }"
}

report_with_span() {
	# $1 = text to place inside the body (not a heading), so check 2's
	# end-matter scan never sees it.
	cat <<EOF
The proposal saves money and time, so it is approved.

## Body

$1

## Sources

- Example Source, 2026.
EOF
}

report_with_attachment_span() {
	# $1 = text placed under an admissible ## Attachment: heading, the shape
	# round 5's case 5 used: a verbatim clause the operator asked for.
	cat <<EOF
The proposal saves money and time, so it is approved.

## Body

Detail.

## Sources

- Example Source, 2026.

## Attachment: source clause

$1
EOF
}

run_fixture_tree() {
	# Builds a materials tree in a temp dir, runs the checker over it with
	# that dir as the materials root, and asserts exit status and output.
	# $1 name, $2 want_exit, $3 want_grep, $4 report path relative to the
	# materials root, then relpath/content pairs for every other file.
	# Content "BINARY" writes random bytes instead of text.
	local name="$1" want="$2" want_grep="$3" rel="$4" dir out status
	shift 4
	dir=$(mktemp -d)
	while [ $# -gt 0 ]; do
		mkdir -p "$dir/$(dirname "$1")"
		if [ "$2" = "BINARY" ]; then
			head -c 64 /dev/urandom >"$dir/$1"
		else
			printf '%s\n' "$2" >"$dir/$1"
		fi
		shift 2
	done
	set +e
	out=$(bash "$0" "$dir/$rel" "$dir" 2>&1)
	status=$?
	set -e
	rm -rf "$dir"
	if [ "$status" != "$want" ] || ! printf '%s' "$out" | grep -qF -- "$want_grep"; then
		echo "SELFTEST FAIL: $name (exit=$status want=$want): $out" >&2
		exit 1
	fi
	echo "PASS: $name (exit=$status)"
}

run_fixture() {
	# $1 name, $2 want_exit, $3 want_grep, $4 report content, $5 scoreboard
	# content ("" to omit the scoreboard file entirely, for the msg-1 case).
	local args=("$1" "$2" "$3" "report.md" "report.md" "$4")
	[ -z "$5" ] || args+=("report.checks.md" "$5")
	run_fixture_tree "${args[@]}"
}

run_fixture_with_file() {
	# Same as run_fixture, plus one extra sibling file beside the report.
	# $6 sibling relpath (skip write if empty), $7 sibling content.
	local args=("$1" "$2" "$3" "report.md" "report.md" "$4")
	[ -z "$5" ] || args+=("report.checks.md" "$5")
	[ -z "$6" ] || args+=("$6" "$7")
	run_fixture_tree "${args[@]}"
}

fixture_clean() {
	run_fixture "clean report, nothing to flag" 0 \
		"no undeclared verbatim span found" \
		"$(clean_report)" "$(board "point paper")"
}

fixture_no_scoreboard() {
	run_fixture "no scoreboard beside the report" 1 \
		"no scoreboard beside the report:" \
		"$(clean_report)" ""
}

fixture_missing_row() {
	run_fixture "scoreboard missing a row" 1 \
		"scoreboard has no row for check 23" \
		"$(clean_report)" "$(board "point paper" "SKIP=23")"
}

fixture_duplicate_row() {
	run_fixture "scoreboard row repeats" 1 \
		"scoreboard row for check 1 repeats" \
		"$(clean_report)" "$(board "point paper" "DUP=1")"
}

fixture_bad_verdict() {
	run_fixture "scoreboard verdict not a valid token" 1 \
		"check 10 verdict is 'maybe', want met|not-met|n-a" \
		"$(clean_report)" \
		"$(board "point paper" "10=| 10 | maybe | | | |")"
}

fixture_zero_parseable_rows() {
	# All 23 rows present but missing the leading/trailing pipe (the shape a
	# literal reading of the checklist's old prose gave). None of them parse;
	# the message must say the table didn't parse, not blame check 1.
	local n rows=""
	for n in $(seq 1 "$CHECK_COUNT"); do
		rows="${rows}${n} | met |  |  | "$'\n'
	done
	run_fixture "scoreboard rows without leading/trailing pipe parse to nothing" 1 \
		"scoreboard has no parseable rows" \
		"$(clean_report)" "Format: point paper

$rows"
}

fixture_doc_example_row() {
	# Copies the header/separator/example row straight out of
	# references/checklist.md (not hand-typed) to prove the doc's own
	# example parses. Checks 2-23 are still absent, so the run must reach
	# the genuine per-check message, not the zero-rows one.
	local table
	table=$(grep -A2 -F '| check | verdict | authoriser | quoted rule | reader loses |' \
		"$SKILL_DIR/references/checklist.md")
	run_fixture "scoreboard built from the checklist's own example row" 1 \
		"scoreboard has no row for check 2" \
		"$(clean_report)" "Format: point paper

$table"
}

fixture_case5_count() {
	# Case 5: seven not-met rows, zero deviation entries, block skipped
	# entirely. Message 4 must fire on this EMPTY-block shape, not only on
	# a merged entry (the defect that killed check 23's count test twice).
	local n rows=()
	for n in 1 3 5 7 9 11 13; do
		rows+=("$n=| $n | not-met | Op. | \"waived\" | reader loses it |")
	done
	run_fixture "case 5: seven not-met rows, no Deviations block" 1 \
		"7 checks not met, 0 deviation entries" \
		"$(clean_report)" "$(board "point paper" "${rows[@]}")"
}

fixture_missing_field() {
	local report
	report=$(clean_report)$'\n\n'"## Deviations"$'\n\n'
	report="${report}- Check 5. Operator instruction: \"skip it.\" Reader loses nothing."
	run_fixture "scoreboard not-met row missing a field" 1 \
		"check 5 is not-met with no authoriser field" \
		"$report" "$(board "point paper" "5=| 5 | not-met | | | |")"
}

fixture_missing_quoted_rule() {
	local report
	report=$(clean_report)$'\n\n'"## Deviations"$'\n\n'
	report="${report}- Check 5. Operator instruction: \"skip it.\" Reader loses nothing."
	run_fixture "scoreboard not-met row missing the quoted rule" 1 \
		"check 5 is not-met with no quoted rule field" \
		"$report" "$(board "point paper" "5=| 5 | not-met | Op. | | reader loses it |")"
}

fixture_missing_reader_loses() {
	local report
	report=$(clean_report)$'\n\n'"## Deviations"$'\n\n'
	report="${report}- Check 5. Operator instruction: \"skip it.\" Reader loses nothing."
	run_fixture "scoreboard not-met row missing reader-loses" 1 \
		"check 5 is not-met with no reader loses field" \
		"$report" "$(board "point paper" "5=| 5 | not-met | Op. | \"waived\" | |")"
}

fixture_stale_entry() {
	local report rows
	report=$(clean_report)$'\n\n'"## Deviations"$'\n\n'
	report="${report}- Check 5. Operator instruction: \"test.\" Reader loses nothing."
	rows="7=| 7 | not-met | Op. | \"waived\" | reader loses the estimate |"
	run_fixture "entry cites a check the scoreboard scores met" 1 \
		"deviations entry cites check 5, scoreboard scores it met" \
		"$report" "$(board "point paper" "$rows")"
}

fixture_bad_heading() {
	local report
	report=$(clean_report)$'\n\n'"## Notes"$'\n\n'"Should not be here."
	run_fixture "end-matter heading not one of the five types" 1 \
		"end-matter item 'Notes' is not an admissible type (check 2)" \
		"$report" "$(board "point paper")"
}

fixture_case8_format() {
	# Case 8: staff study claims four excluded elements, the note names one
	# and denies the rest.
	local report
	report=$(clean_report)$'\n\n'"## Format elements"$'\n\n'"Restate the problem."
	run_fixture "case 8: staff study names 1 of 4 claimed elements" 1 \
		"format 'staff study' claims 4 excluded elements, format-elements note names 1: missing define terms, summarize background, explain calculations" \
		"$report" "$(board "staff study")"
}

fixture_verbatim_span_met() {
	local span
	span="$(span_words "$VERBATIM_SPAN_WORDS")"
	run_fixture_with_file "verbatim span shared with sibling, check 22 scored met" 1 \
		"sibling.md shares ${VERBATIM_SPAN_WORDS}+ words verbatim with the report, opening: \"span01 span02" \
		"$(report_with_span "$span")" \
		"$(board "point paper")" \
		"sibling.md" "Source material.

$span

End of source."
}

fixture_verbatim_span_recorded() {
	local span report
	span="$(span_words "$VERBATIM_SPAN_WORDS")"
	report=$(report_with_span "$span")$'\n\n'"## Deviations"$'\n\n'
	report="${report}- Check 22. Operator instruction: \"reproduce clause 4.2 word for word.\" Reader loses the paraphrase."
	run_fixture_with_file "verbatim span shared, check 22 scored not-met and recorded" 0 \
		"no undeclared verbatim span found" \
		"$report" \
		"$(board "point paper" "22=| 22 | not-met | Operator | \"reproduce clause 4.2 word for word.\" | reader loses the paraphrase |")" \
		"sibling.md" "$span"
}

fixture_verbatim_span_under_threshold() {
	local span
	span="$(span_words $((VERBATIM_SPAN_WORDS - 1)))"
	run_fixture_with_file "verbatim span one word short of the threshold" 0 \
		"no undeclared verbatim span found" \
		"$(report_with_span "$span")" \
		"$(board "point paper")" \
		"sibling.md" "$span"
}

fixture_verbatim_span_case_whitespace() {
	local span sibling_span
	span="$(span_words "$VERBATIM_SPAN_WORDS")"
	sibling_span="$(printf '%s' "$span" | tr ' ' '\n' | tr '[:lower:]' '[:upper:]' | tr '\n' ' ')"
	run_fixture_with_file "verbatim span differs only in case and whitespace" 1 \
		"sibling.md shares ${VERBATIM_SPAN_WORDS}+ words verbatim" \
		"$(report_with_span "$span")" \
		"$(board "point paper")" \
		"sibling.md" "  $sibling_span

"
}

fixture_no_sibling_files() {
	run_fixture "no other files beside the report" 0 \
		"no undeclared verbatim span found" \
		"$(clean_report)" "$(board "point paper")"
}

fixture_unreadable_sibling() {
	run_fixture_with_file "unreadable sibling file is named, not skipped" 1 \
		"could not read 1 file under the materials root" \
		"$(clean_report)" "$(board "point paper")" \
		"sibling.bin" "BINARY"
}

clause_text() {
	# Real legal clause prose, not distinct tokens: the fixtures below have
	# to survive the ordinary English a difflib scan sees in every file.
	cat <<'EOF'
Subject to the limitations set forth in this Section, each party shall
indemnify, defend and hold harmless the other party and its affiliates,
officers, directors, employees and agents from and against any and all
claims, demands, losses, liabilities, damages, costs and expenses, including
reasonable attorneys fees, arising out of or resulting from any breach of the
representations and warranties made by the indemnifying party under this
Agreement, provided that the indemnified party gives prompt written notice of
such claim and permits the indemnifying party to control the defense and
settlement thereof, and further provided that no settlement imposing any
obligation upon the indemnified party shall be entered into without its prior
written consent, which consent shall not be unreasonably withheld, delayed or
conditioned by the indemnified party in any circumstance whatsoever.
EOF
}

operator_question() {
	printf '%s' "Should Halden renew the master services agreement with Vantage on the current terms, or renegotiate the indemnity and liability provisions before the automatic renewal date of 31 March 2027, given the outage record of the past eighteen months and the pricing offered by the two alternative suppliers we approached in January?"
}

case5_report() {
	# Round 5 case 5's recorded shape: a cover letter as front matter, the
	# body, then the clause under an admissible ## Attachment: heading.
	cat <<EOF
## Cover letter

For the general counsel, ahead of the 31 March renewal date.

Halden should renegotiate before renewal, for reasons of cost and risk.

## Body

The indemnity provisions carry the exposure counsel asked about.

## Sources

- Vantage MSA, 2024.

## Attachment: MSA clause 4.2 and referenced provisions

$(clause_text)
EOF
}

fixture_case5_verbatim() {
	# Round 5 case 5: report at the materials root beside its notes and
	# scoreboard, sources in correspondence/ and analysis/, every check
	# scored met, zero deviations, and the clause reproduced word for word
	# under an ## Attachment: heading. The Attachment heading buys no
	# exemption: recording the deviation is the point.
	run_fixture_tree "case 5: all checks met, 0 deviations, attached clause copied from analysis/" 1 \
		"shares ${VERBATIM_SPAN_WORDS}+ words verbatim with the report, opening: \"Subject to the limitations" \
		"halden-position-paper.md" \
		"halden-position-paper.md" "$(case5_report)" \
		"halden-position-paper.checks.md" "$(board "position paper")" \
		"halden-position-paper.notes.md" "# Notes

- Renewal date 31 March 2027. Source: correspondence/notice_bundle.md
- Indemnity exposure. Source: analysis/position_note.md" \
		"correspondence/notice_bundle.md" "# Notice bundle

Vantage gave notice on 2 February 2026." \
		"analysis/position_note.md" "# Position note

$(clause_text)"
}

fixture_paste_only_in_notes() {
	# The paste never reaches the report: it sits in the notes file, copied
	# out of the operator's own material. The notes file used to be
	# exempted from this scan, which made it the safest place to hide one.
	run_fixture_tree "clause pasted into the notes file only" 1 \
		"msa.md shares ${VERBATIM_SPAN_WORDS}+ words verbatim with the report's notes file" \
		"report.md" \
		"report.md" "$(clean_report)" \
		"report.checks.md" "$(board "point paper")" \
		"report.notes.md" "# Notes

$(clause_text)" \
		"msa.md" "# Master agreement

$(clause_text)"
}

fixture_paste_from_own_notes() {
	# The route the old skip set left open in both directions: the clause
	# reaches the report through the notes file, and the material it came
	# from is no longer under the materials root to compare against.
	run_fixture_tree "clause reaches the report through its own notes file" 1 \
		"report.notes.md shares ${VERBATIM_SPAN_WORDS}+ words verbatim with the report" \
		"report.md" \
		"report.md" "$(report_with_span "$(clause_text)")" \
		"report.checks.md" "$(board "point paper")" \
		"report.notes.md" "# Notes

$(clause_text)"
}

fixture_report_below_materials_root() {
	# The writer's output directory is one level below the operator's
	# folder, so scanning the report's own directory sees no source at all.
	run_fixture_tree "report in out/, source one level up under the materials root" 1 \
		"shares ${VERBATIM_SPAN_WORDS}+ words verbatim with the report" \
		"out/report.md" \
		"out/report.md" "$(report_with_span "$(clause_text)")" \
		"out/report.checks.md" "$(board "point paper")" \
		"msa.md" "# Master agreement

$(clause_text)"
}

fixture_unreadable_source_of_a_paste() {
	run_fixture_tree "source of the report's own text is unreadable" 1 \
		"could not read 1 file under the materials root, so check 22's verbatim scan is incomplete: msa.pdf" \
		"report.md" \
		"report.md" "$(report_with_span "$(clause_text)")" \
		"report.checks.md" "$(board "point paper")" \
		"msa.pdf" "BINARY"
}

fixture_sic_padded_paste() {
	# "[sic]" every 30 words breaks every contiguous window longer than 30
	# and leaves the reproduction word for word.
	local padded
	padded=$(clause_text | tr -s '[:space:]' ' ' |
		awk '{for(i=1;i<=NF;i++){printf "%s ",$i; if(i%30==0) printf "[sic] "}}')
	run_fixture_tree "paste padded with [sic] every 30 words" 1 \
		"msa.md shares ${VERBATIM_SPAN_WORDS}+ words verbatim with the report" \
		"report.md" \
		"report.md" "$(report_with_span "$padded")" \
		"report.checks.md" "$(board "point paper")" \
		"msa.md" "# Master agreement

$(clause_text)"
}

fixture_operator_question_restated() {
	# The report contract makes the written-out question govern the report,
	# so restating it verbatim is required, not a paste. Check 22 bars
	# session context, chat logs and raw source text; a question is none.
	run_fixture_tree "report restates the operator's written-out question" 0 \
		"no undeclared verbatim span found" \
		"report.md" \
		"report.md" "Halden should renegotiate before renewal. The written-out question this report answers is: $(operator_question) The reasons group into cost, risk and supplier readiness.

## Body

Uptime fell short of the promised level in six of the eighteen months reviewed.

## Sources

- Vantage MSA, 2024." \
		"report.checks.md" "$(board "point paper")" \
		"README.md" "# $(operator_question)

Operator brief. Materials are in this folder."
}

fixture_clean_materials_tree() {
	run_fixture_tree "paraphrased report over a realistic materials tree" 0 \
		"no undeclared verbatim span found" \
		"report.md" \
		"report.md" "Halden should renegotiate before renewal.

## Body

Uptime fell short in six of eighteen months. Both alternative bids undercut
the incumbent on unit price.

## Sources

- Vantage MSA, 2024." \
		"report.checks.md" "$(board "point paper")" \
		"report.notes.md" "# Notes

- Uptime shortfall, 6 of 18 months. Source: analysis/position_note.md
- Two bids undercut incumbent. Source: correspondence/notice_bundle.md" \
		"correspondence/notice_bundle.md" "# Notice bundle

$(clause_text)" \
		"analysis/position_note.md" "# Position note

$(clause_text)"
}

fixture_no_materials_dir_given() {
	# The one-argument call the whole repo used to make. It must name the
	# missing argument and must not print the clean line.
	local dir out status
	dir=$(mktemp -d)
	printf '%s\n' "$(clean_report)" >"$dir/report.md"
	printf '%s\n' "$(board "point paper")" >"$dir/report.checks.md"
	set +e
	out=$(bash "$0" "$dir/report.md" 2>&1)
	status=$?
	set -e
	rm -rf "$dir"
	if [ "$status" != 1 ] ||
		! printf '%s' "$out" | grep -qF "materials directory not given" ||
		printf '%s' "$out" | grep -qF "no undeclared verbatim span found"; then
		echo "SELFTEST FAIL: no materials directory given (exit=$status): $out" >&2
		exit 1
	fi
	echo "PASS: no materials directory given (exit=$status)"
}

fixture_materials_dir_beside_the_report() {
	local dir out status
	dir=$(mktemp -d)
	mkdir -p "$dir/out" "$dir/elsewhere"
	printf '%s\n' "$(clean_report)" >"$dir/out/report.md"
	printf '%s\n' "$(board "point paper")" >"$dir/out/report.checks.md"
	set +e
	out=$(bash "$0" "$dir/out/report.md" "$dir/elsewhere" 2>&1)
	status=$?
	set -e
	rm -rf "$dir"
	if [ "$status" != 1 ] ||
		! printf '%s' "$out" | grep -qF "does not contain the report's own directory"; then
		echo "SELFTEST FAIL: materials directory beside the report (exit=$status): $out" >&2
		exit 1
	fi
	echo "PASS: materials directory does not contain the report (exit=$status)"
}

selftest() {
	fixture_clean
	fixture_no_scoreboard
	fixture_missing_row
	fixture_duplicate_row
	fixture_bad_verdict
	fixture_zero_parseable_rows
	fixture_doc_example_row
	fixture_case5_count
	fixture_missing_field
	fixture_missing_quoted_rule
	fixture_missing_reader_loses
	fixture_stale_entry
	fixture_bad_heading
	fixture_case8_format
	fixture_verbatim_span_met
	fixture_verbatim_span_recorded
	fixture_verbatim_span_under_threshold
	fixture_verbatim_span_case_whitespace
	fixture_no_sibling_files
	fixture_unreadable_sibling
	fixture_case5_verbatim
	fixture_paste_only_in_notes
	fixture_paste_from_own_notes
	fixture_report_below_materials_root
	fixture_unreadable_source_of_a_paste
	fixture_sic_padded_paste
	fixture_operator_question_restated
	fixture_clean_materials_tree
	fixture_no_materials_dir_given
	fixture_materials_dir_beside_the_report
	echo "OK: 30/30 selftest fixtures passed"
}

if [ "${1:-}" = "--selftest" ]; then
	selftest
	exit 0
fi

# ---- argument parse ---------------------------------------------------------

case $# in
2) : ;;
1) fail "materials directory not given, so check 22's verbatim scan cannot run: check-report.sh <report.md> <materials-dir>, the folder the operator named" ;;
*) fail "usage: check-report.sh <report.md> <materials-dir> | --selftest" ;;
esac
report="$1"
[ -f "$report" ] || fail "no report: $report"
[ -d "$2" ] || fail "no materials directory: $2"
materials=$(cd "$2" && pwd)
report_dir=$(cd "$(dirname "$report")" && pwd)
case "$report_dir" in
"$materials" | "$materials"/*) : ;;
*) fail "materials directory $materials does not contain the report's own directory $report_dir, so the scan would miss the operator's files" ;;
esac

# ---- scoreboard guard --------------------------------------------------------

scoreboard="${report%.md}.checks.md"
[ -f "$scoreboard" ] || fail "no scoreboard beside the report: $scoreboard"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

python3 - "$scoreboard" >"$work/rows" <<'PYEOF'
import re, sys
fmt = ""
print_lines = []
for line in open(sys.argv[1], encoding="utf-8"):
	m = re.match(r'^Format:\s*(.+?)\s*$', line)
	if m:
		fmt = m.group(1)
		continue
	line = line.strip()
	if not line.startswith("|"):
		continue
	cells = [c.strip() for c in line.strip("|").split("|")]
	if len(cells) != 5 or not cells[0].isdigit():
		continue
	print_lines.append(cells)
# \x1f (unit separator): bash `read` treats tab as IFS whitespace and
# collapses an empty field between two tabs, silently shifting every field
# after it. \x1f is not IFS whitespace, so an empty cell stays its own field.
print("FORMAT\x1f" + fmt)
for c in print_lines:
	print("\x1f".join(c))
PYEOF

# ---- row-coverage loop: every check 1..N has exactly one valid-verdict row --

declare -A verdict=() authoriser=() quoted=() loses=()
fmt=""
row_count=0
while IFS=$'\x1f' read -r a b c d e; do
	if [ "$a" = "FORMAT" ]; then
		fmt="$b"
		continue
	fi
	row_count=$((row_count + 1))
	case "$b" in
	met | not-met | n-a) : ;;
	*) fail "check $a verdict is '$b', want met|not-met|n-a" ;;
	esac
	[ -z "${verdict[$a]:-}" ] || fail "scoreboard row for check $a repeats"
	verdict[$a]="$b"
	authoriser[$a]="$c"
	quoted[$a]="$d"
	loses[$a]="$e"
done <"$work/rows"

# Zero rows parsed means the table itself didn't parse (e.g. rows missing
# their leading/trailing pipe) — say that, not "no row for check 1", or the
# writer goes hunting for a missing row instead of a malformed table.
[ "$row_count" -gt 0 ] || fail "scoreboard has no parseable rows: $scoreboard
Expected a markdown table, one row per check, leading and trailing pipe on
every row:
| check | verdict | authoriser | quoted rule | reader loses |
|---|---|---|---|---|
| 1 | met |  |  |  |"

for n in $(seq 1 "$CHECK_COUNT"); do
	[ -n "${verdict[$n]:-}" ] || fail "scoreboard has no row for check $n"
done

# ---- count test: not-met rows vs deviation entries, zero counts included ----

python3 - "$report" >"$work/entries" <<'PYEOF'
import re, sys
in_block = False
for line in open(sys.argv[1], encoding="utf-8"):
	line = line.rstrip("\n")
	if re.match(r'^##\s+Deviations\s*$', line):
		in_block = True
		continue
	if in_block and re.match(r'^##\s', line):
		break
	if not in_block:
		continue
	m = re.match(r'^-\s+(?:Check\s+(\d+)|Rule\s+.+?)\.\s*(.*)$', line)
	if m:
		print((m.group(1) or "") + "\x1f" + m.group(2))
PYEOF

not_met_count=0
for n in $(seq 1 "$CHECK_COUNT"); do
	[ "${verdict[$n]}" = "not-met" ] && not_met_count=$((not_met_count + 1))
done
entry_count=$(wc -l <"$work/entries")
[ "$not_met_count" -eq "$entry_count" ] ||
	fail "$not_met_count checks not met, $entry_count deviation entries in $report"

# ---- field test: every not-met row carries its three deviation fields ------

for n in $(seq 1 "$CHECK_COUNT"); do
	[ "${verdict[$n]}" = "not-met" ] || continue
	[ -n "${authoriser[$n]}" ] || fail "check $n is not-met with no authoriser field"
	[ -n "${quoted[$n]}" ] || fail "check $n is not-met with no quoted rule field"
	[ -n "${loses[$n]}" ] || fail "check $n is not-met with no reader loses field"
done

# ---- transcription test: each entry cites a check the scoreboard scores ----
# not-met. (A row that is not not-met has no quoted rule to transcribe, so
# check 23's "quoted rule does not appear in its entry" is this same test.)

while IFS=$'\x1f' read -r n _rest; do
	[ -n "$n" ] || continue
	[ "${verdict[$n]:-}" = "not-met" ] ||
		fail "deviations entry cites check $n, scoreboard scores it ${verdict[$n]:-missing}"
done <"$work/entries"

# ---- end-matter type test: every heading from the first end-of-body -------
# heading to EOF is one of the five admissible types. A cover letter sits
# before the body, so it never starts this scan (check 2).

python3 - "$report" >"$work/heading" <<'PYEOF'
import re, sys
ADMISSIBLE = {"Sources", "Deviations", "Format elements", "Cover letter"}
SCAN_START = {"Sources", "Deviations", "Format elements"}


def is_attachment(h):
	return h.startswith("Attachment: ") and len(h) > len("Attachment: ")


headings = []
for line in open(sys.argv[1], encoding="utf-8"):
	m = re.match(r'^##\s+(.+?)\s*$', line)
	if m:
		headings.append(m.group(1))

start = None
for i, h in enumerate(headings):
	if h in SCAN_START or is_attachment(h):
		start = i
		break

if start is not None:
	for h in headings[start:]:
		if h not in ADMISSIBLE and not is_attachment(h):
			print(h)
			break
PYEOF

if [ -s "$work/heading" ]; then
	bad=$(head -n1 "$work/heading")
	fail "end-matter item '$bad' is not an admissible type (check 2)"
fi

# ---- format-elements test: the note names every element the format claims -

python3 - "$COLLISIONS" "$fmt" >"$work/claims" <<'PYEOF'
import sys
in_table = False
rows = []
for line in open(sys.argv[1], encoding="utf-8"):
	if line.strip() == "## Excluded elements each format claims":
		in_table = True
		continue
	if in_table and line.startswith("## "):
		break
	if not in_table or not line.strip().startswith("|"):
		continue
	cells = [c.strip() for c in line.strip("\n").strip("|").split("|")]
	if len(cells) == 2 and cells[0] not in ("format", "") and not cells[0].startswith("-"):
		rows.append(cells)

wanted = sys.argv[2].strip().lower()
for formats_cell, elements_cell in rows:
	for token in formats_cell.split(","):
		token = token.strip().lower()
		if wanted == token or wanted.startswith(token):
			if elements_cell.strip().lower() != "none":
				for e in elements_cell.split(";"):
					print(e.strip().lower())
			sys.exit(0)
PYEOF

if [ -s "$work/claims" ]; then
	python3 - "$report" >"$work/note" <<'PYEOF'
import re, sys
in_block = False
for line in open(sys.argv[1], encoding="utf-8"):
	line = line.rstrip("\n")
	if re.match(r'^##\s+Format elements\s*$', line):
		in_block = True
		continue
	if in_block and re.match(r'^##\s', line):
		break
	if not in_block or not line.strip():
		continue
	for part in line.split(","):
		part = part.strip().rstrip(".").lower()
		if part:
			print(part)
PYEOF
	claimed_n=$(wc -l <"$work/claims")
	named_n=$(wc -l <"$work/note")
	missing=""
	while IFS= read -r elem; do
		grep -qxF -- "$elem" "$work/note" || missing="$missing, $elem"
	done <"$work/claims"
	missing="${missing#, }"
	[ -z "$missing" ] ||
		fail "format '$fmt' claims $claimed_n excluded elements, format-elements note names $named_n: missing $missing"
fi

# ---- verbatim-span test: no undeclared paste from the operator's materials -
# Round 5's case 5: a writer scored check 22 "met" on a report carrying 637
# words of pasted source text, and the count test above passed because the
# scoreboard and the (empty) deviations block agreed with each other. Neither
# reads the report. This test does. It walks the materials directory the
# operator named, not the output directory the writer chose, and compares the
# report and its notes file against every file under it for a 40-plus-word
# span (VERBATIM_SPAN_WORDS), whitespace and case normalized. A match is not
# itself a fail — a verbatim clause the operator asked for is a legal report —
# but it must be check 22 not-met with a recorded deviation, the same as any
# other barred fix. An ## Attachment: section gets no exemption: recording the
# deviation is the point even when the paste is the right call.

python3 - "$report" "$materials" "$VERBATIM_SPAN_WORDS" "$MIN_RUN_WORDS" \
	"$RUN_GAP_WORDS" "$QUESTION_EXEMPT_MAX_WORDS" >"$work/span" <<'PYEOF'
import difflib, os, re, sys

report_path, materials_dir = sys.argv[1], sys.argv[2]
SPAN_WORDS, MIN_RUN_WORDS, RUN_GAP_WORDS, QUESTION_MAX_WORDS = (
	int(a) for a in sys.argv[3:7])
UNREADABLE_NAMES_SHOWN = 5
SENTENCE_ENDS = (".", "!", "?")


def read_tokens(path):
	# None means the scan could not read this file at all. The caller
	# reports those; it never treats them as carrying no source text.
	try:
		with open(path, encoding="utf-8") as f:
			text = f.read()
	except (UnicodeDecodeError, OSError):
		return None
	return re.findall(r"\S+", text)


def ngrams(tokens, size):
	return {tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def matched_groups(source, target):
	# autojunk=False: SequenceMatcher's default drops any token appearing in
	# more than 1% of a long sequence, which throws away exactly the common
	# words a pasted clause is made of.
	blocks = [b for b in difflib.SequenceMatcher(
		None, source, target, autojunk=False).get_matching_blocks()
		if b.size >= MIN_RUN_WORDS]
	groups = []
	for b in blocks:
		if groups:
			src_start, src_end, tgt_start, tgt_end, total = groups[-1]
			if b.a - src_end <= RUN_GAP_WORDS and b.b - tgt_end <= RUN_GAP_WORDS:
				groups[-1] = (src_start, b.a + b.size, tgt_start,
					b.b + b.size, total + b.size)
				continue
		groups.append((b.a, b.a + b.size, b.b, b.b + b.size, b.size))
	return groups


def is_one_question(tokens, start, end):
	# Check 22 bars session context, chat logs and raw source text. The
	# operator's written-out question is none of the three, and the report
	# contract requires the report to restate it, so a group that sits
	# inside a single interrogative sentence on the source side is not a
	# paste. Any sentence end strictly inside the group disqualifies it.
	for i in range(start, len(tokens)):
		if tokens[i].endswith(SENTENCE_ENDS):
			return i >= end - 1 and tokens[i].endswith("?")
	return False


unreadable = []
compared_sides = []
for label, path in (("the report", report_path),
		("the report's notes file", report_path[:-len(".md")] + ".notes.md"
			if report_path.endswith(".md") else "")):
	path = os.path.abspath(path) if path else ""
	if not path or not os.path.isfile(path):
		continue
	tokens = read_tokens(path)
	if tokens is None:
		unreadable.append(os.path.relpath(path, materials_dir))
		continue
	lowered = [w.lower() for w in tokens]
	compared_sides.append((label, path, tokens, lowered,
		ngrams(lowered, MIN_RUN_WORDS)))

skip = {os.path.abspath(report_path)}
if report_path.endswith(".md"):
	skip.add(os.path.abspath(report_path[:-len(".md")] + ".checks.md"))

candidates = []
for root, dirs, files in os.walk(materials_dir):
	dirs.sort()
	for fname in sorted(files):
		path = os.path.abspath(os.path.join(root, fname))
		if path not in skip:
			candidates.append(path)

compared_count = 0
hit = None
for path in candidates:
	tokens = read_tokens(path)
	if tokens is None:
		unreadable.append(os.path.relpath(path, materials_dir))
		continue
	compared_count += 1
	if hit is not None:
		continue
	lowered = [w.lower() for w in tokens]
	if len(lowered) < MIN_RUN_WORDS:
		continue
	cand_grams = ngrams(lowered, MIN_RUN_WORDS)
	for label, side_path, side_tokens, side_lowered, side_grams in compared_sides:
		if side_path == path or cand_grams.isdisjoint(side_grams):
			continue
		for src_start, src_end, tgt_start, _, total in matched_groups(
				lowered, side_lowered):
			if total < SPAN_WORDS:
				continue
			if total <= QUESTION_MAX_WORDS and is_one_question(
					lowered, src_start, src_end):
				continue
			hit = (os.path.relpath(path, materials_dir), label,
				" ".join(side_tokens[tgt_start:tgt_start + 12]))
			break
		if hit is not None:
			break

print("COMPARED\x1f%d" % compared_count)
if unreadable:
	shown = ", ".join(unreadable[:UNREADABLE_NAMES_SHOWN])
	if len(unreadable) > UNREADABLE_NAMES_SHOWN:
		shown += ", and %d more" % (len(unreadable) - UNREADABLE_NAMES_SHOWN)
	print("UNREADABLE\x1fcould not read %d file%s under the materials root, so"
		" check 22's verbatim scan is incomplete: %s (extract its text beside"
		" it, or score check 22 not-met and record the deviation)"
		% (len(unreadable), "" if len(unreadable) == 1 else "s", shown))
if hit is not None:
	print("SPAN\x1f" + "\x1f".join(hit))
PYEOF

compared_count=0
unreadable_msg=""
span_file=""
span_side=""
span_opening=""
while IFS=$'\x1f' read -r tag a b c; do
	case "$tag" in
	COMPARED) compared_count="$a" ;;
	UNREADABLE) unreadable_msg="$a" ;;
	SPAN)
		span_file="$a"
		span_side="$b"
		span_opening="$c"
		;;
	esac
done <"$work/span"

# A file the scan could not read is never a clean result: the report below
# would otherwise claim nothing was pasted out of material nobody compared.
[ -z "$unreadable_msg" ] || fail "$unreadable_msg"

if [ -n "$span_file" ]; then
	[ "${verdict[22]:-}" = "not-met" ] ||
		fail "$span_file shares ${VERBATIM_SPAN_WORDS}+ words verbatim with $span_side, opening: \"$span_opening\" (check 22 scored '${verdict[22]:-missing}', want not-met with a deviation)"
fi

echo "OK: scoreboard and deviations block agree, end matter is admissible, format elements are named, no undeclared verbatim span found (compared the report and any notes file against $compared_count files under $materials). Every verdict on the scoreboard is the writer's own; this script re-scores none of them."
