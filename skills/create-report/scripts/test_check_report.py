"""Tests for check_report.py, driven through the command line it ships.

In plain words: each case below builds a small folder of files that looks
like a real report plus the scoreboard beside it, runs the checker over that
folder, and says which exit code and which sentence the run has to produce.
The cases are data, so the same list also drives the differential harness
that proved this port matches the shell script it replaced.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest

SCRIPT = Path(__file__).parent / "check_report.py"
SKILL_DIR = SCRIPT.parent.parent
CHECK_COUNT = 23
VERBATIM_SPAN_WORDS = 40
# Bytes no UTF-8 decoder accepts, so "the scan could not read this" is a
# property of the fixture rather than a dice roll on random bytes.
UNREADABLE_BYTES = b"\xff\xfe\x80\x81" * 16
EXAMPLE_ROW_HEADER = "| check | verdict | authoriser | quoted rule | reader loses |"


class Fixture(NamedTuple):
    name: str
    want_exit: int
    want_output: str
    report_rel: str
    files: tuple[tuple[str, str | bytes], ...]
    materials_rel: str | None = "."
    banned_output: str = ""
    dirs: tuple[str, ...] = ()


def board(declared_format: str, custom: dict[int, str] | None = None,
          skip: int | None = None, dup: int | None = None) -> str:
    """A scoreboard scoring every check met, minus or plus what is asked."""
    custom = custom or {}
    lines = [f"Format: {declared_format}", "",
             EXAMPLE_ROW_HEADER, "|---|---|---|---|---|"]
    for number in range(1, CHECK_COUNT + 1):
        if number == skip:
            continue
        row = custom.get(number, f"| {number} | met | | | |")
        lines.append(row)
        if number == dup:
            lines.append(row)
    return "\n".join(lines)


def clean_report() -> str:
    return """The proposal saves money and time, so it is approved.

## Body

Detail.

## Sources

- Example Source, 2026."""


def with_deviations(report: str, entry: str) -> str:
    return f"{report}\n\n## Deviations\n\n{entry}"


def span_words(count: int) -> str:
    """Tokens no other fixture text uses, so a match can only be planted."""
    return " ".join(f"span{number:02d}" for number in range(1, count + 1))


def report_with_span(text: str) -> str:
    """The text sits in the body, so the end-matter scan never sees it."""
    return f"""The proposal saves money and time, so it is approved.

## Body

{text}

## Sources

- Example Source, 2026."""


def clause_text() -> str:
    """Real legal prose, not distinct tokens: the paste fixtures have to
    survive the ordinary English a difflib scan sees in every file."""
    return """Subject to the limitations set forth in this Section, each party shall
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
conditioned by the indemnified party in any circumstance whatsoever."""


def operator_question() -> str:
    return (
        "Should Halden renew the master services agreement with Vantage on"
        " the current terms, or renegotiate the indemnity and liability"
        " provisions before the automatic renewal date of 31 March 2027,"
        " given the outage record of the past eighteen months and the pricing"
        " offered by the two alternative suppliers we approached in January?"
    )


def case5_report() -> str:
    """Round 5 case 5: cover letter, body, then the clause under an
    admissible '## Attachment:' heading."""
    return f"""## Cover letter

For the general counsel, ahead of the 31 March renewal date.

Halden should renegotiate before renewal, for reasons of cost and risk.

## Body

The indemnity provisions carry the exposure counsel asked about.

## Sources

- Vantage MSA, 2024.

## Attachment: MSA clause 4.2 and referenced provisions

{clause_text()}"""


def checklist_example_table() -> str:
    """The header, separator and example row out of the checklist itself."""
    lines = (SKILL_DIR / "references" / "checklist.md").read_text(
        encoding="utf-8"
    ).splitlines()
    start = lines.index(EXAMPLE_ROW_HEADER)
    return "\n".join(lines[start:start + 3])


def sic_padded_clause() -> str:
    """The clause with '[sic]' every 30 words, which breaks every contiguous
    window longer than 30 and leaves the reproduction word for word."""
    parts = []
    for position, token in enumerate(clause_text().split(), start=1):
        parts.append(token)
        if position % 30 == 0:
            parts.append("[sic]")
    return " ".join(parts)


def uppercased(text: str) -> str:
    return "  " + " ".join(word.upper() for word in text.split()) + " \n"


def deviation_rows(numbers: list[int]) -> dict[int, str]:
    return {
        number: f'| {number} | not-met | Op. | "waived" | reader loses it |'
        for number in numbers
    }


UNPARSEABLE_BOARD = "Format: point paper\n\n" + "".join(
    f"{number} | met |  |  | \n" for number in range(1, CHECK_COUNT + 1)
)
SKIP_IT = '- Check 5. Operator instruction: "skip it." Reader loses nothing.'
TEST_ENTRY = '- Check 5. Operator instruction: "test." Reader loses nothing.'
CLAUSE_22 = (
    '- Check 22. Operator instruction: "reproduce clause 4.2 word for word."'
    " Reader loses the paraphrase."
)
ROW_22_NOT_MET = (
    '| 22 | not-met | Operator | "reproduce clause 4.2 word for word." |'
    " reader loses the paraphrase |"
)


def _paste_fixtures() -> list[Fixture]:
    """The cases that plant real source text and watch check 22 catch it."""
    clause = clause_text()
    return [
        Fixture(
            "case 5: all checks met, 0 deviations, attached clause copied"
            " from analysis/",
            1,
            f'shares {VERBATIM_SPAN_WORDS}+ words verbatim with the report,'
            ' opening: "Subject to the limitations',
            "halden-position-paper.md",
            (
                ("halden-position-paper.md", case5_report()),
                ("halden-position-paper.checks.md", board("position paper")),
                ("halden-position-paper.notes.md",
                 "# Notes\n\n"
                 "- Renewal date 31 March 2027. Source:"
                 " correspondence/notice_bundle.md\n"
                 "- Indemnity exposure. Source: analysis/position_note.md"),
                ("correspondence/notice_bundle.md",
                 "# Notice bundle\n\nVantage gave notice on 2 February 2026."),
                ("analysis/position_note.md", f"# Position note\n\n{clause}"),
            ),
        ),
        Fixture(
            "clause pasted into the notes file only",
            1,
            f"msa.md shares {VERBATIM_SPAN_WORDS}+ words verbatim with the"
            " report's notes file",
            "report.md",
            (
                ("report.md", clean_report()),
                ("report.checks.md", board("point paper")),
                ("report.notes.md", f"# Notes\n\n{clause}"),
                ("msa.md", f"# Master agreement\n\n{clause}"),
            ),
        ),
        Fixture(
            "clause reaches the report through its own notes file",
            1,
            f"report.notes.md shares {VERBATIM_SPAN_WORDS}+ words verbatim"
            " with the report",
            "report.md",
            (
                ("report.md", report_with_span(clause)),
                ("report.checks.md", board("point paper")),
                ("report.notes.md", f"# Notes\n\n{clause}"),
            ),
        ),
        Fixture(
            "report in out/, source one level up under the materials root",
            1,
            f"shares {VERBATIM_SPAN_WORDS}+ words verbatim with the report",
            "out/report.md",
            (
                ("out/report.md", report_with_span(clause)),
                ("out/report.checks.md", board("point paper")),
                ("msa.md", f"# Master agreement\n\n{clause}"),
            ),
        ),
        Fixture(
            "source of the report's own text is unreadable",
            1,
            "could not read 1 file under the materials root, so check 22's"
            " verbatim scan is incomplete: msa.pdf",
            "report.md",
            (
                ("report.md", report_with_span(clause)),
                ("report.checks.md", board("point paper")),
                ("msa.pdf", UNREADABLE_BYTES),
            ),
        ),
        Fixture(
            "paste padded with [sic] every 30 words",
            1,
            f"msa.md shares {VERBATIM_SPAN_WORDS}+ words verbatim with the"
            " report",
            "report.md",
            (
                ("report.md", report_with_span(sic_padded_clause())),
                ("report.checks.md", board("point paper")),
                ("msa.md", f"# Master agreement\n\n{clause}"),
            ),
        ),
    ]


def _span_fixtures() -> list[Fixture]:
    """The cases that plant a synthetic span and vary one thing about it."""
    span = span_words(VERBATIM_SPAN_WORDS)
    short_span = span_words(VERBATIM_SPAN_WORDS - 1)
    return [
        Fixture(
            "verbatim span shared with sibling, check 22 scored met",
            1,
            f"sibling.md shares {VERBATIM_SPAN_WORDS}+ words verbatim with"
            ' the report, opening: "span01 span02',
            "report.md",
            (
                ("report.md", report_with_span(span)),
                ("report.checks.md", board("point paper")),
                ("sibling.md", f"Source material.\n\n{span}\n\nEnd of source."),
            ),
        ),
        Fixture(
            "verbatim span shared, check 22 scored not-met and recorded",
            0,
            "no undeclared verbatim span found",
            "report.md",
            (
                ("report.md",
                 with_deviations(report_with_span(span), CLAUSE_22)),
                ("report.checks.md",
                 board("point paper", custom={22: ROW_22_NOT_MET})),
                ("sibling.md", span),
            ),
        ),
        Fixture(
            "verbatim span one word short of the threshold",
            0,
            "no undeclared verbatim span found",
            "report.md",
            (
                ("report.md", report_with_span(short_span)),
                ("report.checks.md", board("point paper")),
                ("sibling.md", short_span),
            ),
        ),
        Fixture(
            "verbatim span differs only in case and whitespace",
            1,
            f"sibling.md shares {VERBATIM_SPAN_WORDS}+ words verbatim",
            "report.md",
            (
                ("report.md", report_with_span(span)),
                ("report.checks.md", board("point paper")),
                ("sibling.md", uppercased(span)),
            ),
        ),
    ]


def _scoreboard_fixtures() -> list[Fixture]:
    """The cases that break the scoreboard table itself."""
    report = clean_report()
    checks = ("report.md", "report.checks.md")
    return [
        Fixture("clean report, nothing to flag", 0,
                "no undeclared verbatim span found", "report.md",
                ((checks[0], report), (checks[1], board("point paper")))),
        Fixture("no scoreboard beside the report", 1,
                "no scoreboard beside the report:", "report.md",
                ((checks[0], report),)),
        Fixture("scoreboard missing a row", 1,
                "scoreboard has no row for check 23", "report.md",
                ((checks[0], report),
                 (checks[1], board("point paper", skip=23)))),
        Fixture("scoreboard row repeats", 1,
                "scoreboard row for check 1 repeats", "report.md",
                ((checks[0], report),
                 (checks[1], board("point paper", dup=1)))),
        Fixture("scoreboard verdict not a valid token", 1,
                "check 10 verdict is 'maybe', want met|not-met|n-a",
                "report.md",
                ((checks[0], report),
                 (checks[1], board("point paper",
                                   custom={10: "| 10 | maybe | | | |"})))),
        Fixture("scoreboard rows without leading/trailing pipe parse to"
                " nothing", 1,
                "scoreboard has no parseable rows", "report.md",
                ((checks[0], report), (checks[1], UNPARSEABLE_BOARD))),
        Fixture("scoreboard built from the checklist's own example row", 1,
                "scoreboard has no row for check 2", "report.md",
                ((checks[0], report),
                 (checks[1],
                  f"Format: point paper\n\n{checklist_example_table()}"))),
        Fixture("case 5: seven not-met rows, no Deviations block", 1,
                "7 checks not met, 0 deviation entries", "report.md",
                ((checks[0], report),
                 (checks[1], board("point paper",
                                   custom=deviation_rows(
                                       [1, 3, 5, 7, 9, 11, 13]))))),
        Fixture("scoreboard not-met row missing a field", 1,
                "check 5 is not-met with no authoriser field", "report.md",
                ((checks[0], with_deviations(report, SKIP_IT)),
                 (checks[1], board("point paper",
                                   custom={5: "| 5 | not-met | | | |"})))),
        Fixture("scoreboard not-met row missing the quoted rule", 1,
                "check 5 is not-met with no quoted rule field", "report.md",
                ((checks[0], with_deviations(report, SKIP_IT)),
                 (checks[1], board(
                     "point paper",
                     custom={5: "| 5 | not-met | Op. | | reader loses it |"}
                 )))),
        Fixture("scoreboard not-met row missing reader-loses", 1,
                "check 5 is not-met with no reader loses field", "report.md",
                ((checks[0], with_deviations(report, SKIP_IT)),
                 (checks[1], board(
                     "point paper",
                     custom={5: '| 5 | not-met | Op. | "waived" | |'}
                 )))),
        Fixture("entry cites a check the scoreboard scores met", 1,
                "deviations entry cites check 5, scoreboard scores it met",
                "report.md",
                ((checks[0], with_deviations(report, TEST_ENTRY)),
                 (checks[1], board("point paper",
                                   custom=deviation_rows([7]))))),
        Fixture("end-matter heading not one of the five types", 1,
                "end-matter item 'Notes' is not an admissible type (check 2)",
                "report.md",
                ((checks[0], f"{report}\n\n## Notes\n\nShould not be here."),
                 (checks[1], board("point paper")))),
        Fixture("case 8: staff study names 1 of 4 claimed elements", 1,
                "format 'staff study' claims 4 excluded elements,"
                " format-elements note names 1: missing define terms,"
                " summarize background, explain calculations",
                "report.md",
                ((checks[0],
                  f"{report}\n\n## Format elements\n\nRestate the problem."),
                 (checks[1], board("staff study")))),
        Fixture("no other files beside the report", 0,
                "no undeclared verbatim span found", "report.md",
                ((checks[0], report), (checks[1], board("point paper")))),
        Fixture("unreadable sibling file is named, not skipped", 1,
                "could not read 1 file under the materials root", "report.md",
                ((checks[0], report), (checks[1], board("point paper")),
                 ("sibling.bin", UNREADABLE_BYTES))),
    ]


def _clean_tree_fixtures() -> list[Fixture]:
    """The cases a well-written report has to pass."""
    question = operator_question()
    clause = clause_text()
    return [
        Fixture(
            "report restates the operator's written-out question",
            0,
            "no undeclared verbatim span found",
            "report.md",
            (
                ("report.md",
                 "Halden should renegotiate before renewal. The written-out"
                 f" question this report answers is: {question} The reasons"
                 " group into cost, risk and supplier readiness.\n\n## Body"
                 "\n\nUptime fell short of the promised level in six of the"
                 " eighteen months reviewed.\n\n## Sources\n\n"
                 "- Vantage MSA, 2024."),
                ("report.checks.md", board("point paper")),
                ("README.md",
                 f"# {question}\n\nOperator brief. Materials are in this"
                 " folder."),
            ),
        ),
        Fixture(
            "paraphrased report over a realistic materials tree",
            0,
            "no undeclared verbatim span found",
            "report.md",
            (
                ("report.md",
                 "Halden should renegotiate before renewal.\n\n## Body\n\n"
                 "Uptime fell short in six of eighteen months. Both"
                 " alternative bids undercut\nthe incumbent on unit price."
                 "\n\n## Sources\n\n- Vantage MSA, 2024."),
                ("report.checks.md", board("point paper")),
                ("report.notes.md",
                 "# Notes\n\n- Uptime shortfall, 6 of 18 months. Source:"
                 " analysis/position_note.md\n- Two bids undercut incumbent."
                 " Source: correspondence/notice_bundle.md"),
                ("correspondence/notice_bundle.md",
                 f"# Notice bundle\n\n{clause}"),
                ("analysis/position_note.md", f"# Position note\n\n{clause}"),
            ),
        ),
    ]


def _argument_fixtures() -> list[Fixture]:
    """The cases about how the tool is called, not what it reads."""
    report = clean_report()
    return [
        Fixture(
            "no materials directory given",
            1,
            "materials directory not given",
            "report.md",
            (("report.md", report), ("report.checks.md", board("point paper"))),
            materials_rel=None,
            banned_output="no undeclared verbatim span found",
        ),
        Fixture(
            "materials directory does not contain the report",
            1,
            "does not contain the report's own directory",
            "out/report.md",
            (("out/report.md", report),
             ("out/report.checks.md", board("point paper"))),
            materials_rel="elsewhere",
            dirs=("out", "elsewhere"),
        ),
    ]


FIXTURES = (
    _scoreboard_fixtures()
    + _span_fixtures()
    + _paste_fixtures()
    + _clean_tree_fixtures()
    + _argument_fixtures()
)


def build_tree(root: Path, fixture: Fixture) -> None:
    """Writes the fixture's files and directories under root."""
    for name in fixture.dirs:
        (root / name).mkdir(parents=True, exist_ok=True)
    for relative, content in fixture.files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content + "\n", encoding="utf-8")


def run_checker(
    command: list[str], root: Path, fixture: Fixture
) -> subprocess.CompletedProcess[str]:
    """Runs one checker over a freshly built fixture tree."""
    args = [str(root / fixture.report_rel)]
    if fixture.materials_rel == ".":
        args.append(str(root))
    elif fixture.materials_rel is not None:
        args.append(str(root / fixture.materials_rel))
    return subprocess.run(
        command + args, capture_output=True, text=True, cwd=root
    )


def run_fixture(fixture: Fixture) -> tuple[int, str]:
    """The exit code and combined output of the checker on one fixture."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_tree(root, fixture)
        done = run_checker([sys.executable, str(SCRIPT)], root, fixture)
    return done.returncode, done.stdout + done.stderr


@pytest.mark.parametrize(
    "fixture", FIXTURES, ids=[fixture.name for fixture in FIXTURES]
)
def test_fixture_tree_gets_the_expected_verdict(fixture: Fixture) -> None:
    status, output = run_fixture(fixture)
    assert status == fixture.want_exit, output
    assert fixture.want_output in output
    if fixture.banned_output:
        assert fixture.banned_output not in output


def test_every_fixture_from_the_shell_script_is_covered() -> None:
    assert len(FIXTURES) == 30
    assert len({fixture.name for fixture in FIXTURES}) == 30


# Line-break characters other than newline, as they arrive in text pasted
# out of a PDF or a word processor.
LINE_SEPARATOR = "\u2028"
NEXT_LINE = "\u0085"

REGRESSIONS = (
    Fixture(
        "U+2028 does not start the entry under '## Deviations'",
        1,
        "1 checks not met, 0 deviation entries",
        "report.md",
        (
            ("report.md",
             f"{clean_report()}\n\n## Deviations{LINE_SEPARATOR}"
             "- Check 3. It happened."),
            ("report.checks.md",
             board("point paper",
                   custom={3: '| 3 | not-met | Op. | "waived" | loss |'})),
        ),
    ),
    Fixture(
        "U+0085 mid-line does not invent an end-matter heading",
        0,
        "no undeclared verbatim span found",
        "report.md",
        (
            ("report.md", f"{clean_report()}{NEXT_LINE}## Cheese"),
            ("report.checks.md", board("point paper")),
        ),
    ),
)


@pytest.mark.parametrize(
    "fixture", REGRESSIONS, ids=[fixture.name for fixture in REGRESSIONS]
)
def test_only_a_newline_starts_a_new_line(fixture: Fixture) -> None:
    """A report carries U+2028, U+0085 and friends whenever someone pastes
    out of a PDF or a word processor. They are characters inside a line, not
    line breaks, so neither one may change a verdict."""
    status, output = run_fixture(fixture)
    assert status == fixture.want_exit, output
    assert fixture.want_output in output


def test_empty_materials_argument_is_not_the_current_directory() -> None:
    """A caller whose materials variable went unset must be refused, never
    handed a green verdict over a tree nobody scanned."""
    fixture = next(f for f in FIXTURES if f.name == "clean report, nothing"
                   " to flag")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_tree(root, fixture)
        done = subprocess.run(
            [sys.executable, str(SCRIPT), str(root / "report.md"), ""],
            capture_output=True, text=True, cwd=root,
        )
    assert done.returncode == 1
    assert done.stdout == ""
    assert done.stderr == "FAIL: no materials directory: \n"


def test_a_failure_names_itself_on_stderr_and_exits_one() -> None:
    """The FAIL prefix and the stream it goes to are part of the contract."""
    fixture = next(
        f for f in FIXTURES if f.name == "no scoreboard beside the report"
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_tree(root, fixture)
        done = run_checker([sys.executable, str(SCRIPT)], root, fixture)
    assert done.returncode == 1
    assert done.stdout == ""
    assert done.stderr.startswith("FAIL: no scoreboard beside the report:")
