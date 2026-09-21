import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
REPOSITORY_ROOT = PLUGIN_ROOT.parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "validate-skills.py"
SKILLS_DIR = PLUGIN_ROOT / "skills"


def run_validator(skills_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(skills_dir)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ValidateSkillsTests(unittest.TestCase):
    def test_passes_on_the_real_skills_tree(self) -> None:
        result = run_validator(SKILLS_DIR)

        self.assertEqual(0, result.returncode, result.stderr)

    def test_fails_on_a_broken_relative_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            skill_dir = skills_dir / "sample"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: sample\ndescription: A sample skill.\n---\n\n"
                "See [missing](./nope.md).\n"
            )

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("nope.md", result.stderr)
            self.assertIn("missing", result.stderr)

    def test_fails_when_a_link_escapes_the_skills_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            skill_dir = skills_dir / "sample"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: sample\ndescription: A sample skill.\n---\n\n"
                "See [outside](../../outside.md).\n"
            )

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("escapes skills tree", result.stderr)

    def test_ignores_links_inside_fenced_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            skill_dir = skills_dir / "sample"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: sample\ndescription: A sample skill.\n---\n\n"
                "```md\n[example](./nope.md)\n```\n"
            )

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_fails_when_frontmatter_name_does_not_match_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            skill_dir = skills_dir / "sample"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: wrong-name\ndescription: A sample skill.\n---\n\nBody.\n"
            )

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode)
            self.assertIn('!= directory "sample"', result.stderr)

    def test_fails_when_description_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            skill_dir = skills_dir / "sample"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: sample\n---\n\nBody.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("no description frontmatter", result.stderr)


if __name__ == "__main__":
    unittest.main()
