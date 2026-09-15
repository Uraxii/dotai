"""Tests that the blank-frame gate rejects a capture nothing painted into.

The numbers below are not invented. Each one was measured by running
`lab shot` against a real podman lab on 2026-09-12, one case per capture:

    nothing ran          stddev=0        colors=1    bytes=250
    command exited       stddev=0        colors=1    bytes=250
    dialog box only      stddev=5213.05  colors=2    bytes=444
    real test pattern    stddev=19661.3  colors=530  bytes=8852

The third case is the one that matters. A frame that is 99% one colour with
one small widget in the middle passed a `stddev == 0` gate, so a window that
never painted was reported as a successful screenshot. These tests pin the
rule that separates it from the real capture.

They need no podman: the gate reads the text of one `identify` line.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

import lab_container

# `lab` is a command, so it carries no `.py` suffix and a plain import misses
# it. Name its loader instead of guessing one from the extension.
LOADER = importlib.machinery.SourceFileLoader(
    "lab", str(Path(__file__).resolve().parent / "lab")
)
SPEC = importlib.util.spec_from_loader("lab", LOADER)
lab = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(lab)

NOTHING_RAN = "stddev=0 colors=1 bytes=250"
COMMAND_EXITED = "stddev=0 colors=1 bytes=250"
DIALOG_ONLY = "stddev=5213.05 colors=2 bytes=444"
REAL_PATTERN = "stddev=19661.3 colors=530 bytes=8852"


class IsBlankTest(unittest.TestCase):
    """The four measured captures, and the rule that sorts them."""

    def test_a_display_nothing_ran_on_is_blank(self) -> None:
        self.assertTrue(lab.is_blank(NOTHING_RAN))

    def test_a_command_that_exited_without_painting_is_blank(self) -> None:
        self.assertTrue(lab.is_blank(COMMAND_EXITED))

    def test_a_frame_holding_only_a_dialog_box_is_blank(self) -> None:
        self.assertTrue(lab.is_blank(DIALOG_ONLY))

    def test_a_real_multicolour_capture_is_not_blank(self) -> None:
        self.assertFalse(lab.is_blank(REAL_PATTERN))

    def test_three_colours_is_the_first_frame_that_passes(self) -> None:
        self.assertTrue(lab.is_blank("stddev=1 colors=2 bytes=9"))
        self.assertFalse(lab.is_blank("stddev=1 colors=3 bytes=9"))

    def test_a_line_without_a_colour_count_is_an_error(self) -> None:
        with self.assertRaises(lab_container.LabError):
            lab.is_blank("stddev=19661.3 bytes=8852")


if __name__ == "__main__":
    unittest.main()
