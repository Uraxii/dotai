import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "pstack"
VALIDATOR = REPOSITORY_ROOT / "scripts" / "validate-skills.py"
SKILLS_DIR = PLUGIN_ROOT / "skills"


def run_validator(
    skills_dir: Path, ci: bool = False
) -> subprocess.CompletedProcess[str]:
    environment = {key: value for key, value in os.environ.items() if key != "CI"}
    if ci:
        environment["CI"] = "true"
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(skills_dir)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
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


def commit_all(repository: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-m", message],
        cwd=repository, check=True, capture_output=True,
    )


def write_removed_skill(repository: Path, skills_dir: Path, name: str) -> None:
    """Give the repository a history in which `name` was a skill and then went away.

    The validator learns which names used to be skills from git, so a test for a
    stale reference has to leave that history behind the same way a real deletion
    does: commit the skill, remove the directory, commit again.
    """
    if not (repository / ".git").exists():
        subprocess.run(["git", "init", "-b", "main"], cwd=repository, check=True,
                       capture_output=True)
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / ".keep").write_text("")
        commit_all(repository, "Start the tree")
    write_skill(skills_dir, name)
    commit_all(repository, f"Add {name}")
    shutil.rmtree(skills_dir / name)
    commit_all(repository, f"Delete {name}")


class RemovedSkillReferenceTests(unittest.TestCase):
    """PR #56 deleted thirteen skills while a planted **caveman** reference passed.

    A name that is not a skill directory is worth flagging in every syntax the
    tree uses to cite skills, which is what these cases pin down.
    """

    def assert_reference_is_flagged(self, citation: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "skills"
            write_removed_skill(repository, skills_dir, "caveman")
            write_skill(skills_dir, "sample", citation)

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("caveman", result.stderr)

    def test_fails_on_a_bare_bold_reference_to_a_removed_skill(self) -> None:
        self.assert_reference_is_flagged("Answer in **caveman** register.\n")

    def test_fails_on_a_bare_backticked_reference_to_a_removed_skill(self) -> None:
        self.assert_reference_is_flagged("Answer in `caveman` register.\n")

    def test_fails_on_the_bold_skill_frame_for_a_removed_skill(self) -> None:
        self.assert_reference_is_flagged("Load the **caveman** skill now.\n")

    def test_fails_on_the_backticked_skill_frame_for_a_removed_skill(self) -> None:
        self.assert_reference_is_flagged("Load the `caveman` skill now.\n")

    def test_fails_on_a_removed_skill_whose_prefix_family_has_one_member(self) -> None:
        # Deleting setup-dotai left setup-pstack alone in the setup- family, and the
        # family threshold of two then hid every remaining setup-dotai reference.
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "skills"
            write_removed_skill(repository, skills_dir, "setup-dotai")
            write_skill(skills_dir, "setup-pstack")
            write_skill(skills_dir, "sample", "Run `setup-dotai` first.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("setup-dotai", result.stderr)

    def test_accepts_a_skill_that_history_removed_and_a_later_commit_restored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "skills"
            write_removed_skill(repository, skills_dir, "caveman")
            write_skill(skills_dir, "caveman")
            write_skill(skills_dir, "sample", "Answer in **caveman** register.\n")

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_accepts_prose_words_that_were_never_skills(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "skills"
            write_removed_skill(repository, skills_dir, "caveman")
            write_skill(
                skills_dir,
                "sample",
                "Keep it **read-only**, run `git status` on `main`, and **never** guess.\n",
            )

            result = run_validator(skills_dir)

            self.assertEqual(0, result.returncode, result.stderr)

class UnreadableHistoryTests(unittest.TestCase):
    """History is one of the rules, so a run that could not read it has not
    checked what the plain "ok:" line claims.

    PR #56 shipped a stale reference behind a green line. A validator that
    silently drops back to its weaker rules and still prints "ok:" reintroduces
    exactly that failure, so an unreadable history has to be said out loud.
    """

    def assert_degraded(self, skills_dir: Path, ci: bool) -> None:
        result = run_validator(skills_dir, ci=ci)

        self.assertIn("DEGRADED", result.stderr)
        self.assertNotIn("ok:", result.stdout)
        self.assertEqual(1 if ci else 0, result.returncode, result.stderr)

    def test_warns_and_withholds_the_ok_line_outside_a_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            write_skill(skills_dir, "sample", "Answer in **caveman** register.\n")

            self.assert_degraded(skills_dir, ci=False)

    def test_fails_outside_a_git_repository_in_ci(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            write_skill(skills_dir, "sample", "Answer in **caveman** register.\n")

            self.assert_degraded(skills_dir, ci=True)

    def test_fails_in_a_shallow_clone_in_ci(self) -> None:
        # A shallow clone answers `git log` without error and simply omits the
        # commit that deleted a skill, so CI keeping fetch-depth: 0 is load
        # bearing and a shallow checkout has to fail rather than look clean.
        with tempfile.TemporaryDirectory() as directory:
            origin = Path(directory) / "origin"
            origin.mkdir()
            skills_dir = origin / "skills"
            write_removed_skill(origin, skills_dir, "caveman")
            clone = Path(directory) / "clone"
            subprocess.run(
                ["git", "clone", "--depth", "1", origin.as_uri(), str(clone)],
                check=True, capture_output=True,
            )

            self.assert_degraded(clone / "skills", ci=True)

    def test_reads_history_from_a_full_clone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            origin = Path(directory) / "origin"
            origin.mkdir()
            skills_dir = origin / "skills"
            write_removed_skill(origin, skills_dir, "caveman")
            clone = Path(directory) / "clone"
            subprocess.run(
                ["git", "clone", origin.as_uri(), str(clone)],
                check=True, capture_output=True,
            )
            write_skill(clone / "skills", "sample", "Answer in **caveman** register.\n")

            result = run_validator(clone / "skills", ci=True)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("caveman", result.stderr)


if __name__ == "__main__":
    unittest.main()
