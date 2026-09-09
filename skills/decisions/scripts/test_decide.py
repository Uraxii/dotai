"""Tests for decide.py, driven through the command line it ships."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

DECIDE = str(Path(__file__).parent / "decide.py")


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, DECIDE, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def test_first_record_writes_header_then_row() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = root / "notes" / "d.tsv"
        done = run(
            [
                "record",
                "log-format",
                "one tsv file per project",
                "greppable and needs no service",
                "skills/decisions/scripts/decide.py",
                str(log),
            ],
            root,
        )
        assert done.returncode == 0, done.stderr
        assert done.stdout.strip() == str(log)
        lines = log.read_text().splitlines()
        assert lines[0] == "ts\ttopic\tdecision\twhy\tevidence"
        assert len(lines) == 2
        assert lines[1].split("\t")[1:] == [
            "log-format",
            "one tsv file per project",
            "greppable and needs no service",
            "skills/decisions/scripts/decide.py",
        ]


def test_newest_row_for_a_topic_is_the_one_in_force() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = root / "d.tsv"
        run(["record", "storage", "keep it in the kb", "was there already",
             "kb_decision.py", str(log)], root)
        run(["record", "other", "unrelated call", "keeps two topics apart",
             "n/a", str(log)], root)
        run(["record", "storage", "move it to one tsv file", "no container",
             "commit abc123", str(log)], root)

        current = run(["now", str(log)], root)
        assert current.returncode == 0, current.stderr
        assert "move it to one tsv file" in current.stdout
        assert "keep it in the kb" not in current.stdout
        assert "unrelated call" in current.stdout

        chain = run(["log", "storage", str(log)], root)
        assert chain.returncode == 0, chain.stderr
        assert chain.stdout.index("keep it in the kb") < chain.stdout.index(
            "move it to one tsv file"
        )
        assert "unrelated call" not in chain.stdout


def test_tabs_newlines_and_formula_leads_are_neutralised() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = root / "d.tsv"
        done = run(["record", "hostile", "=cmd|'/c calc'!A1",
                    "a why with\ta tab and\na newline", "file.py:1", str(log)],
                   root)
        assert done.returncode == 0, done.stderr
        lines = log.read_text().splitlines()
        assert len(lines) == 2
        cells = lines[1].split("\t")
        assert len(cells) == 5
        assert cells[2] == "'=cmd|'/c calc'!A1"
        assert cells[3] == "a why with a tab and a newline"


def test_gitignore_gains_the_log_once() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        git_repo(root)
        run(["record", "t", "d", "w", "e"], root)
        first = (root / ".gitignore").read_text()
        run(["record", "t", "d2", "w", "e"], root)
        second = (root / ".gitignore").read_text()
        assert first.splitlines().count(".decisions.tsv") == 1
        assert second == first


def test_missing_log_says_so_without_a_traceback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing = root / "nope.tsv"
        for args in (["now", str(missing)], ["log", "any", str(missing)]):
            done = run(args, root)
            assert done.returncode != 0
            assert "Traceback" not in done.stderr
            assert str(missing) in done.stderr


def test_empty_topic_or_decision_is_refused() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = root / "d.tsv"
        assert run(["record", "  ", "d", "w", "e", str(log)], root).returncode
        assert run(["record", "t", "", "w", "e", str(log)], root).returncode
        assert not log.exists()


if __name__ == "__main__":
    tests = [
        test_first_record_writes_header_then_row,
        test_newest_row_for_a_topic_is_the_one_in_force,
        test_tabs_newlines_and_formula_leads_are_neutralised,
        test_gitignore_gains_the_log_once,
        test_missing_log_says_so_without_a_traceback,
        test_empty_topic_or_decision_is_refused,
    ]
    for test in tests:
        test()
    print("ok")
