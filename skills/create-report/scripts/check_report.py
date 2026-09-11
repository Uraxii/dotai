#!/usr/bin/env python3
"""Checks a finished report against the scoreboard filed beside it.

In plain words: the writer scores their own report against 23 checks in a
sibling file named <report-name>.checks.md. This script reads both files and
says whether they tell the same story. It re-scores no check. It only catches
a scoreboard that disagrees with the report: a check scored twice or not at
all, a not-met row with no deviation entry to match it, end matter of a kind
the format does not allow, a format-elements note that skips an element the
chosen format drops, and a long run of the operator's own material
reproduced in the report without anyone declaring it.

Design: .nikki-agents/deviations-mechanism-design.md.
Run: python3 <this-skill-directory>/scripts/check_report.py <report.md> <materials-dir>
"""
from __future__ import annotations

import difflib
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple, NoReturn

__all__ = ["main"]

USAGE = "check_report.py <report.md> <materials-dir>"
CHECK_COUNT = 23
# ponytail: difflib run-grouping over case- and whitespace-normalized tokens.
# Ceiling: it joins matched runs separated by insertions of up to
# RUN_GAP_WORDS, so padding a paste with "[sic]" no longer hides it, but a
# rewrite that changes more than that between runs still passes. Real
# paraphrase detection needs semantic matching, which this is not.
VERBATIM_SPAN_WORDS = 40
MIN_RUN_WORDS = 12
RUN_GAP_WORDS = 20
QUESTION_EXEMPT_MAX_WORDS = 80
SPAN_OPENING_WORDS = 12
UNREADABLE_NAMES_SHOWN = 5
SENTENCE_ENDS = (".", "!", "?")
VERDICTS = ("met", "not-met", "n-a")
SCOREBOARD_CELLS = 5
MARKDOWN_SUFFIX = ".md"
ADMISSIBLE_END_MATTER = frozenset(
    ("Sources", "Deviations", "Format elements", "Cover letter")
)
END_MATTER_STARTS = frozenset(("Sources", "Deviations", "Format elements"))
ATTACHMENT_PREFIX = "Attachment: "
CLAIMS_HEADING = "## Excluded elements each format claims"

NO_PARSEABLE_ROWS = """scoreboard has no parseable rows: {scoreboard}
Expected a markdown table, one row per check, leading and trailing pipe on
every row:
| check | verdict | authoriser | quoted rule | reader loses |
|---|---|---|---|---|
| 1 | met |  |  |  |"""

UNREADABLE_FILES = (
    "could not read {count} file{plural} under the materials root, so check"
    " 22's verbatim scan is incomplete: {names} (extract its text beside it,"
    " or score check 22 not-met and record the deviation)"
)

UNDECLARED_SPAN = (
    '{source} shares {words}+ words verbatim with {side}, opening: "{opening}"'
    " (check 22 scored '{scored}', want not-met with a deviation)"
)

EVERYTHING_AGREES = (
    "OK: scoreboard and deviations block agree, end matter is admissible,"
    " format elements are named, no undeclared verbatim span found (compared"
    " the report and any notes file against {count} files under {materials})."
    " Every verdict on the scoreboard is the writer's own; this script"
    " re-scores none of them."
)


def absolute(path: str | Path) -> Path:
    """An absolute path with '.' and '..' collapsed, symlinks left alone."""
    return Path(os.path.abspath(path))


SKILL_DIR = absolute(__file__).parent.parent
COLLISIONS = SKILL_DIR / "references" / "collisions.md"


def fail(message: str) -> NoReturn:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def sibling(report: str, suffix: str) -> str:
    """The report's path with its '.md' tail swapped for another one."""
    if report.endswith(MARKDOWN_SUFFIX):
        return report[: -len(MARKDOWN_SUFFIX)] + suffix
    return report + suffix


class ScoreboardRow(NamedTuple):
    check: str
    verdict: str
    authoriser: str
    quoted_rule: str
    reader_loses: str


class DeviationEntry(NamedTuple):
    check: str
    rest: str


class SpanHit(NamedTuple):
    source: str
    side: str
    opening: str


class VerbatimScan(NamedTuple):
    compared_count: int
    unreadable: list[str]
    hit: SpanHit | None


def parse_scoreboard(scoreboard: Path) -> tuple[str, list[ScoreboardRow]]:
    """The declared format and every five-cell numbered row of the table."""
    declared_format = ""
    rows: list[ScoreboardRow] = []
    for line in scoreboard.read_text(encoding="utf-8").splitlines():
        declared = re.match(r"^Format:\s*(.+?)\s*$", line)
        if declared:
            declared_format = declared.group(1)
            continue
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != SCOREBOARD_CELLS or not cells[0].isdigit():
            continue
        rows.append(ScoreboardRow(*cells))
    return declared_format, rows


def index_rows(
    rows: list[ScoreboardRow], scoreboard: str
) -> dict[str, ScoreboardRow]:
    """One row per check, with every check from 1 to CHECK_COUNT present."""
    by_check: dict[str, ScoreboardRow] = {}
    for row in rows:
        if row.verdict not in VERDICTS:
            fail(
                f"check {row.check} verdict is '{row.verdict}',"
                " want met|not-met|n-a"
            )
        if row.check in by_check:
            fail(f"scoreboard row for check {row.check} repeats")
        by_check[row.check] = row
    if not by_check:
        fail(NO_PARSEABLE_ROWS.format(scoreboard=scoreboard))
    for number in range(1, CHECK_COUNT + 1):
        if str(number) not in by_check:
            fail(f"scoreboard has no row for check {number}")
    return by_check


def parse_deviations(report: Path) -> list[DeviationEntry]:
    """Every entry under the report's own '## Deviations' heading."""
    entries: list[DeviationEntry] = []
    in_block = False
    for line in report.read_text(encoding="utf-8").splitlines():
        if re.match(r"^##\s+Deviations\s*$", line):
            in_block = True
            continue
        if in_block and re.match(r"^##\s", line):
            break
        if not in_block:
            continue
        entry = re.match(r"^-\s+(?:Check\s+(\d+)|Rule\s+.+?)\.\s*(.*)$", line)
        if entry:
            entries.append(
                DeviationEntry(entry.group(1) or "", entry.group(2))
            )
    return entries


def check_deviations_agree(
    report: Path, report_arg: str, by_check: dict[str, ScoreboardRow]
) -> None:
    """Not-met rows and deviation entries must match one for one."""
    entries = parse_deviations(report)
    not_met = [
        number
        for number in range(1, CHECK_COUNT + 1)
        if by_check[str(number)].verdict == "not-met"
    ]
    if len(not_met) != len(entries):
        fail(
            f"{len(not_met)} checks not met, {len(entries)} deviation entries"
            f" in {report_arg}"
        )
    for number in not_met:
        row = by_check[str(number)]
        for value, name in (
            (row.authoriser, "authoriser"),
            (row.quoted_rule, "quoted rule"),
            (row.reader_loses, "reader loses"),
        ):
            if not value:
                fail(f"check {number} is not-met with no {name} field")
    for entry in entries:
        if not entry.check:
            continue
        row = by_check.get(entry.check)
        scored = row.verdict if row else "missing"
        if scored != "not-met":
            fail(
                f"deviations entry cites check {entry.check},"
                f" scoreboard scores it {scored}"
            )


def is_attachment(heading: str) -> bool:
    return heading.startswith(ATTACHMENT_PREFIX) and len(heading) > len(
        ATTACHMENT_PREFIX
    )


def first_inadmissible_heading(report: Path) -> str | None:
    """The first end-matter heading whose type the report contract bars.

    A cover letter sits before the body, so it never starts the scan. The
    scan runs from the first end-of-body heading to the end of the file.
    """
    headings = []
    for line in report.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            headings.append(heading.group(1))
    start = next(
        (
            index
            for index, text in enumerate(headings)
            if text in END_MATTER_STARTS or is_attachment(text)
        ),
        None,
    )
    if start is None:
        return None
    for text in headings[start:]:
        if text not in ADMISSIBLE_END_MATTER and not is_attachment(text):
            return text
    return None


def collision_rows(collisions: Path) -> list[list[str]]:
    """Every two-cell data row of the excluded-elements table."""
    rows: list[list[str]] = []
    in_table = False
    for line in collisions.read_text(encoding="utf-8").splitlines():
        if line.strip() == CLAIMS_HEADING:
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if (
            len(cells) == 2
            and cells[0] not in ("format", "")
            and not cells[0].startswith("-")
        ):
            rows.append(cells)
    return rows


def claimed_elements(collisions: Path, declared_format: str) -> list[str]:
    """The elements the first matching format row says that format drops."""
    wanted = declared_format.strip().lower()
    for formats_cell, elements_cell in collision_rows(collisions):
        for token in formats_cell.split(","):
            token = token.strip().lower()
            if wanted != token and not wanted.startswith(token):
                continue
            if elements_cell.strip().lower() == "none":
                return []
            return [e.strip().lower() for e in elements_cell.split(";")]
    return []


def named_elements(report: Path) -> list[str]:
    """Every element the report's own '## Format elements' note names."""
    named: list[str] = []
    in_block = False
    for line in report.read_text(encoding="utf-8").splitlines():
        if re.match(r"^##\s+Format elements\s*$", line):
            in_block = True
            continue
        if in_block and re.match(r"^##\s", line):
            break
        if not in_block or not line.strip():
            continue
        for part in line.split(","):
            part = part.strip().rstrip(".").lower()
            if part:
                named.append(part)
    return named


def check_format_elements(report: Path, declared_format: str) -> None:
    claimed = claimed_elements(COLLISIONS, declared_format)
    if not claimed:
        return
    named = named_elements(report)
    missing = [element for element in claimed if element not in named]
    if missing:
        fail(
            f"format '{declared_format}' claims {len(claimed)} excluded"
            f" elements, format-elements note names {len(named)}: missing "
            + ", ".join(missing)
        )


def read_tokens(path: Path) -> list[str] | None:
    """Whitespace-separated tokens, or None when the file will not read.

    None means the scan could not read this file at all. The caller reports
    those; it never treats them as carrying no source text.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    return re.findall(r"\S+", text)


def ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


class MatchedGroup(NamedTuple):
    source_start: int
    source_end: int
    target_start: int
    target_end: int
    words: int


def matched_groups(source: list[str], target: list[str]) -> list[MatchedGroup]:
    """Matched runs, joined across insertions of up to RUN_GAP_WORDS."""
    # autojunk=False: SequenceMatcher's default drops any token appearing in
    # more than 1% of a long sequence, which throws away exactly the common
    # words a pasted clause is made of.
    matcher = difflib.SequenceMatcher(None, source, target, autojunk=False)
    groups: list[MatchedGroup] = []
    for block in matcher.get_matching_blocks():
        if block.size < MIN_RUN_WORDS:
            continue
        source_end, target_end = block.a + block.size, block.b + block.size
        last = groups[-1] if groups else None
        if (last and block.a - last.source_end <= RUN_GAP_WORDS
                and block.b - last.target_end <= RUN_GAP_WORDS):
            groups[-1] = MatchedGroup(
                last.source_start, source_end, last.target_start, target_end,
                last.words + block.size)
            continue
        groups.append(MatchedGroup(
            block.a, source_end, block.b, target_end, block.size))
    return groups


def is_one_question(tokens: list[str], start: int, end: int) -> bool:
    """True when the group sits inside a single interrogative sentence.

    Check 22 bars session context, chat logs and raw source text. The
    operator's written-out question is none of the three, and the report
    contract requires the report to restate it, so such a group is not a
    paste. Any sentence end strictly inside the group disqualifies it.
    """
    for index in range(start, len(tokens)):
        if tokens[index].endswith(SENTENCE_ENDS):
            return index >= end - 1 and tokens[index].endswith("?")
    return False


class ComparedSide(NamedTuple):
    label: str
    path: Path
    tokens: list[str]
    lowered: list[str]
    grams: set[tuple[str, ...]]


def notes_path(report: Path) -> Path | None:
    if not str(report).endswith(MARKDOWN_SUFFIX):
        return None
    return Path(sibling(str(report), ".notes.md"))


def report_sides(
    report: Path, materials: Path
) -> tuple[list[ComparedSide], list[str]]:
    """The report and its notes file, tokenised, plus what would not read."""
    sides: list[ComparedSide] = []
    unreadable: list[str] = []
    for label, path in (("the report", report),
                        ("the report's notes file", notes_path(report))):
        if path is None or not path.is_file():
            continue
        tokens = read_tokens(path)
        if tokens is None:
            unreadable.append(str(path.relative_to(materials)))
            continue
        lowered = [word.lower() for word in tokens]
        sides.append(ComparedSide(label, path, tokens, lowered,
                                  ngrams(lowered, MIN_RUN_WORDS)))
    return sides, unreadable


def candidate_files(materials: Path, skip: set[Path]) -> list[Path]:
    """Every file under the materials root except the report's own pair."""
    found: list[Path] = []
    for root, dirs, files in os.walk(materials):
        dirs.sort()
        for name in sorted(files):
            path = absolute(Path(root) / name)
            if path not in skip:
                found.append(path)
    return found


def first_span(path: Path, tokens: list[str], sides: list[ComparedSide],
               materials: Path) -> SpanHit | None:
    """The first undeclared verbatim span this file shares with the report."""
    lowered = [word.lower() for word in tokens]
    if len(lowered) < MIN_RUN_WORDS:
        return None
    grams = ngrams(lowered, MIN_RUN_WORDS)
    for side in sides:
        if side.path == path or grams.isdisjoint(side.grams):
            continue
        for group in matched_groups(lowered, side.lowered):
            if group.words < VERBATIM_SPAN_WORDS:
                continue
            if group.words <= QUESTION_EXEMPT_MAX_WORDS and is_one_question(
                    lowered, group.source_start, group.source_end):
                continue
            start = group.target_start
            opening = " ".join(side.tokens[start:start + SPAN_OPENING_WORDS])
            return SpanHit(str(path.relative_to(materials)), side.label,
                           opening)
    return None


def scan_verbatim(report: Path, materials: Path) -> VerbatimScan:
    """Walks the materials root the operator named, not the output folder.

    Round 5's case 5: a writer scored check 22 'met' on a report carrying 637
    words of pasted source text, and the count test passed because the
    scoreboard and the empty deviations block agreed with each other. Neither
    reads the report. This scan does. A match is not itself a fail, since a
    verbatim clause the operator asked for is a legal report, but it must be
    check 22 not-met with a recorded deviation. An '## Attachment:' section
    buys no exemption: recording the deviation is the point.
    """
    sides, unreadable = report_sides(report, materials)
    skip = {report}
    if str(report).endswith(MARKDOWN_SUFFIX):
        skip.add(Path(sibling(str(report), ".checks.md")))
    compared_count = 0
    hit: SpanHit | None = None
    for path in candidate_files(materials, skip):
        tokens = read_tokens(path)
        if tokens is None:
            unreadable.append(str(path.relative_to(materials)))
            continue
        compared_count += 1
        if hit is None:
            hit = first_span(path, tokens, sides, materials)
    return VerbatimScan(compared_count, unreadable, hit)


def unreadable_message(unreadable: list[str]) -> str:
    shown = ", ".join(unreadable[:UNREADABLE_NAMES_SHOWN])
    if len(unreadable) > UNREADABLE_NAMES_SHOWN:
        shown += f", and {len(unreadable) - UNREADABLE_NAMES_SHOWN} more"
    return UNREADABLE_FILES.format(
        count=len(unreadable),
        plural="" if len(unreadable) == 1 else "s",
        names=shown,
    )


def check_verbatim(
    report: Path, materials: Path, by_check: dict[str, ScoreboardRow]
) -> int:
    """Runs the span scan and returns how many files it compared."""
    scan = scan_verbatim(report, materials)
    # A file the scan could not read is never a clean result: the report
    # below would otherwise claim nothing was pasted out of material nobody
    # compared.
    if scan.unreadable:
        fail(unreadable_message(scan.unreadable))
    if scan.hit and by_check["22"].verdict != "not-met":
        fail(UNDECLARED_SPAN.format(
            source=scan.hit.source, words=VERBATIM_SPAN_WORDS,
            side=scan.hit.side, opening=scan.hit.opening,
            scored=by_check["22"].verdict))
    return scan.compared_count


def parse_arguments(args: list[str]) -> tuple[str, Path, Path]:
    """The report as given, the report absolute, the materials root."""
    if len(args) == 1:
        fail(
            "materials directory not given, so check 22's verbatim scan"
            f" cannot run: {USAGE}, the folder the operator named"
        )
    if len(args) != 2:
        fail(f"usage: {USAGE}")
    report_arg, materials_arg = args
    if not Path(report_arg).is_file():
        fail(f"no report: {report_arg}")
    if not Path(materials_arg).is_dir():
        fail(f"no materials directory: {materials_arg}")
    materials = absolute(materials_arg)
    report = absolute(report_arg)
    if report.parent != materials and materials not in report.parent.parents:
        fail(
            f"materials directory {materials} does not contain the report's"
            f" own directory {report.parent}, so the scan would miss the"
            " operator's files"
        )
    return report_arg, report, materials


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    report_arg, report, materials = parse_arguments(args)
    scoreboard_arg = sibling(report_arg, ".checks.md")
    if not Path(scoreboard_arg).is_file():
        fail(f"no scoreboard beside the report: {scoreboard_arg}")
    declared_format, rows = parse_scoreboard(Path(scoreboard_arg))
    by_check = index_rows(rows, scoreboard_arg)
    check_deviations_agree(report, report_arg, by_check)
    inadmissible = first_inadmissible_heading(report)
    if inadmissible:
        fail(f"end-matter item '{inadmissible}' is not an admissible type"
             " (check 2)")
    check_format_elements(report, declared_format)
    compared_count = check_verbatim(report, materials, by_check)
    print(EVERYTHING_AGREES.format(count=compared_count, materials=materials))


if __name__ == "__main__":
    main()
