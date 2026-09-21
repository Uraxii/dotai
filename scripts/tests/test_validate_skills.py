import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "pstack"
VALIDATOR = REPOSITORY_ROOT / "scripts" / "validate-skills.py"
SKILLS_DIR = PLUGIN_ROOT / "skills"


def run_validator(skills_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(skills_dir)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_skill(skills_dir: Path, name: str, body: str = "Body.\n") -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: The {name} skill.\n---\n\n{body}"
    )
    return skill_dir


def write_principle_family(skills_dir: Path) -> None:
    # Two same-prefix directories are what make "principle-" a known family,
    # so a reference to a third, missing one is recognisably a skill name.
    write_skill(skills_dir, "principle-one")
    write_skill(skills_dir, "principle-two")


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


class BoldSkillReferenceTests(unittest.TestCase):
    def test_fails_on_a_bold_reference_to_a_missing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_principle_family(skills_dir)
            write_skill(skills_dir, "sample", "Apply **principle-ghost** first.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("principle-ghost", result.stderr)

    def test_fails_on_a_backticked_reference_to_a_missing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_principle_family(skills_dir)
            write_skill(skills_dir, "sample", "Apply `principle-ghost` first.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("principle-ghost", result.stderr)

    def test_accepts_bold_references_to_existing_skills(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_principle_family(skills_dir)
            write_skill(skills_dir, "sample", "Apply **principle-one** first.\n")

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_fails_on_the_skill_frame_for_a_missing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_skill(skills_dir, "sample", "Run the **ghostwriter** skill now.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("ghostwriter", result.stderr)

    def test_accepts_the_skill_frame_for_an_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_skill(skills_dir, "sample", "Run the **helper** skill now.\n")
            write_skill(skills_dir, "helper")

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_ignores_hyphenated_prose_outside_any_skill_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_principle_family(skills_dir)
            write_skill(
                skills_dir,
                "sample",
                "Keep it **read-only** and `up-to-date`, never `typescript-best-practices`.\n",
            )

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_ignores_external_skills_named_in_the_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_skill(
                skills_dir, "sample", "Not the bundled **babysit** skill, the playbook.\n"
            )

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_ignores_namespaced_and_glob_skill_references(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_principle_family(skills_dir)
            write_skill(
                skills_dir,
                "sample",
                "See **plugin-dev:skill-development** and every `principle-*` skill.\n",
            )

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_ignores_bold_references_inside_fenced_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            write_principle_family(skills_dir)
            write_skill(
                skills_dir, "sample", "```md\nApply **principle-ghost** first.\n```\n"
            )

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_checks_agent_markdown_beside_the_skills_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin_root = Path(directory)
            skills_dir = plugin_root / "skills"
            write_principle_family(skills_dir)
            agents_dir = plugin_root / "agents"
            agents_dir.mkdir()
            (agents_dir / "worker.md").write_text("Apply **principle-ghost** first.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("principle-ghost", result.stderr)


if __name__ == "__main__":
    unittest.main()
