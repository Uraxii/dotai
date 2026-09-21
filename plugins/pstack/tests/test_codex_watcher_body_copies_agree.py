"""The watcher body lives in three files; a fix must land in all three.

`agents/developer-codex.md` and `agents/reviewer-codex.md` carry the Codex
watcher's real system prompt inline, below their own frontmatter.
`skills/poteto-mode/references/codex-watcher-body.md` is the copy a reader
reaches through the skill. Editing only the reference copy ships nothing,
which is exactly what happened once; this test is the tripwire.
"""

import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = PLUGIN_ROOT / "skills/poteto-mode/references/codex-watcher-body.md"
AGENTS = (
    PLUGIN_ROOT / "agents/developer-codex.md",
    PLUGIN_ROOT / "agents/reviewer-codex.md",
)
HEADING = "### Codex watcher"


def body(path: Path) -> str:
    """The watcher body of `path`, from its `### Codex watcher` heading on."""
    text = path.read_text()
    start = text.find(HEADING)
    assert start != -1, f"{path} has no {HEADING!r} heading"
    return text[start:]


class CodexWatcherBodyCopiesTests(unittest.TestCase):
    def test_every_agent_body_matches_the_reference_copy(self) -> None:
        expected = body(REFERENCE)
        for agent in AGENTS:
            with self.subTest(agent=agent.name):
                self.assertEqual(
                    expected,
                    body(agent),
                    f"{agent} has drifted from {REFERENCE}. Copy the body into "
                    "all three files, not just the one you edited.",
                )


if __name__ == "__main__":
    unittest.main()
