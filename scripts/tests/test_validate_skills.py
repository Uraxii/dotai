from __future__ import annotations

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
    *skills_dirs: Path, ci: str | None = None
) -> subprocess.CompletedProcess[str]:
    environment = {key: value for key, value in os.environ.items() if key != "CI"}
    if ci is not None:
        environment["CI"] = ci
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *(str(path) for path in skills_dirs)],
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

    def test_passes_on_every_plugin_skills_tree_at_once(self) -> None:
        trees = sorted((REPOSITORY_ROOT / "plugins").glob("*/skills"))
        self.assertGreater(len(trees), 1, "the repository ships several plugins")

        result = run_validator(*trees)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(f"{len(trees)} trees", result.stdout)

    def test_fails_when_a_named_tree_does_not_exist(self) -> None:
        # CI passes plugins/*/skills. A glob that matches nothing arrives as
        # that literal string, and validating nothing has to be loud.
        result = run_validator(REPOSITORY_ROOT / "plugins" / "*" / "skills2")

        self.assertNotEqual(0, result.returncode, result.stdout)
        self.assertIn("no skills tree", result.stderr)

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
    def test_requires_the_principle_prefix_across_plugin_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin_root = Path(directory)
            citing_tree = plugin_root / "citing" / "skills"
            owning_tree = plugin_root / "owning" / "skills"
            write_skill(citing_tree, "sample", "Apply **prove-it-works** first.\n")
            write_skill(owning_tree, "principle-prove-it-works")

            result = run_validator(citing_tree, owning_tree)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("prove-it-works", result.stderr)
            self.assertIn("principle-prove-it-works", result.stderr)

            write_skill(
                citing_tree, "sample", "Apply **principle-prove-it-works** first.\n"
            )
            write_skill(
                citing_tree,
                "safe-words",
                " ".join(
                    f"**{word}**"
                    for word in (
                        "tutorial",
                        "reference",
                        "explanation",
                        "how-to",
                        "must",
                        "evidence",
                        "target",
                        "question",
                        "recall",
                        "babysit",
                    )
                )
                + "\n",
            )

            result = run_validator(citing_tree, owning_tree)

            self.assertEqual(0, result.returncode, result.stderr)

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

    def test_flags_a_reference_to_a_skill_this_plugin_deleted(self) -> None:
        # bro and teach were exempted globally to quiet one UPSTREAM.md
        # sentence, which also hid every stale mention added afterwards.
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "skills"
            write_removed_skill(repository, skills_dir, "bro")
            write_skill(skills_dir, "sample", "Answer in **bro** register.\n")

            result = run_validator(skills_dir)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("bro", result.stderr)
            self.assertIn("deleted", result.stderr)

    def test_ignores_a_skill_that_only_ever_existed_on_another_branch(self) -> None:
        # --all made every ref's history count, so a name a merged-and-forgotten
        # branch once carried stayed "historical" for good and a developer's
        # result depended on which branches their clone happened to hold.
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "skills"
            skills_dir.mkdir(parents=True)
            (skills_dir / ".keep").write_text("")
            subprocess.run(["git", "init", "-b", "main"], cwd=repository,
                           check=True, capture_output=True)
            commit_all(repository, "Start the tree")
            subprocess.run(["git", "checkout", "-b", "side"], cwd=repository,
                           check=True, capture_output=True)
            write_skill(skills_dir, "sidekick")
            commit_all(repository, "Add sidekick")
            shutil.rmtree(skills_dir / "sidekick")
            commit_all(repository, "Delete sidekick")
            subprocess.run(["git", "checkout", "main"], cwd=repository,
                           check=True, capture_output=True)
            write_skill(skills_dir, "sample", "Answer in **sidekick** register.\n")

            result = run_validator(skills_dir, ci="true")

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

    def assert_degraded(self, skills_dir: Path, ci: str | None, code: int) -> None:
        result = run_validator(skills_dir, ci=ci)

        self.assertIn("DEGRADED", result.stderr)
        self.assertNotIn("ok:", result.stdout)
        self.assertEqual(code, result.returncode, result.stderr)

    def test_warns_and_withholds_the_ok_line_outside_a_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            write_skill(skills_dir, "sample", "Answer in **caveman** register.\n")

            self.assert_degraded(skills_dir, ci=None, code=0)

    def test_fails_outside_a_git_repository_in_ci(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            write_skill(skills_dir, "sample", "Answer in **caveman** register.\n")

            self.assert_degraded(skills_dir, ci="true", code=1)

    def test_reads_ci_as_a_value_rather_than_as_a_set_variable(self) -> None:
        # CI=false and CI=0 are how a developer says "not CI", and an empty
        # CI is how a shell says the same thing.
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            write_skill(skills_dir, "sample", "Body.\n")

            for value, code in (("false", 0), ("0", 0), ("", 0),
                                ("true", 1), ("1", 1)):
                with self.subTest(ci=value):
                    self.assert_degraded(skills_dir, ci=value, code=code)

    def test_reports_degraded_alongside_a_failure_the_weaker_rules_caught(self) -> None:
        # A run that exits 1 on the heuristics alone still has to say that the
        # history rule never ran, or the log cannot be told apart from a run
        # that checked every deleted name and found one.
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            write_principle_family(skills_dir)
            write_skill(skills_dir, "sample", "Apply **principle-ghost** first.\n")

            result = run_validator(skills_dir, ci="true")

            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("FAIL:", result.stderr)
            self.assertIn("principle-ghost", result.stderr)
            self.assertIn("DEGRADED:", result.stderr)

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

            self.assert_degraded(clone / "skills", ci="true", code=1)

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

            result = run_validator(clone / "skills", ci="true")

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("caveman", result.stderr)


def write_split_repository(repository: Path) -> tuple[Path, Path]:
    """A repository shaped like this one after the split: pstack plus one more.

    The skills all began in pstack, so pstack is the tree whose git history
    carries the deletions, and the second tree is the one whose own history
    starts at the move commit.
    """
    pstack = repository / "plugins" / "pstack" / "skills"
    azure = repository / "plugins" / "azure" / "skills"
    write_removed_skill(repository, pstack, "caveman")
    write_skill(pstack, "principle-naming")
    write_skill(pstack, "principle-decomposition")
    write_skill(azure, "devops")
    commit_all(repository, "Split azure out of pstack")
    return pstack, azure


class MultipleSkillsTreeTests(unittest.TestCase):
    """One invocation over every tree, because a per-plugin loop cannot see across.

    A citation can name a skill in a sibling plugin. A validator run against
    one tree at a time cannot see a prefixed skill that a sibling owns.
    """

    def test_accepts_a_citation_that_names_a_skill_in_another_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            pstack, azure = write_split_repository(repository)
            write_skill(azure, "sample", "Apply `principle-naming` first.\n")

            result = run_validator(pstack, azure)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_accepts_a_citation_that_resolves_in_its_own_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            pstack, azure = write_split_repository(repository)
            write_skill(pstack, "sample", "Apply `principle-naming` first.\n")

            result = run_validator(pstack, azure)

            self.assertEqual(0, result.returncode, result.stderr)

    def test_validates_every_tree_rather_than_only_the_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            pstack, azure = write_split_repository(repository)
            write_skill(azure, "sample", "See [missing](./nope.md).\n")

            result = run_validator(pstack, azure)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("nope.md", result.stderr)

    def test_catches_a_pre_move_deletion_in_a_tree_that_never_held_it(self) -> None:
        # azure/skills begins at the move commit, so its own history knows
        # nothing about caveman. The trees share one historical set for
        # exactly this reason.
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            pstack, azure = write_split_repository(repository)
            write_skill(azure, "sample", "Answer in **caveman** register.\n")

            result = run_validator(pstack, azure)

            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("caveman", result.stderr)
            self.assertIn("deleted", result.stderr)

    def test_a_single_tree_alone_misses_the_pre_move_deletion(self) -> None:
        # The measurement behind the one-invocation rule. Keep it, so a future
        # change back to a per-plugin loop shows what it costs.
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            _, azure = write_split_repository(repository)
            write_skill(azure, "sample", "Answer in **caveman** register.\n")

            result = run_validator(azure)

            self.assertEqual(0, result.returncode, result.stderr)


class BareInvocationTests(unittest.TestCase):
    """What the command does when a person types it with no argument.

    The default used to be `plugins/pstack/skills`: one tree of eleven, both
    whole-picture rules off, exit 0. That is the defect this script exists to
    catch, reproduced by the shortest thing anyone would type.
    """

    def test_it_covers_every_tree_the_glob_covers(self) -> None:
        trees = sorted((REPOSITORY_ROOT / "plugins").glob("*/skills"))
        self.assertGreater(len(trees), 1)

        bare = run_validator()
        explicit = run_validator(*trees)

        self.assertEqual(0, bare.returncode, bare.stderr)
        self.assertEqual(explicit.stdout, bare.stdout)
        self.assertIn(f"in {len(trees)} trees", bare.stdout)


class SuccessLineTests(unittest.TestCase):
    def test_it_says_one_tree_rather_than_1_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            skills_dir = repository / "plugins" / "solo" / "skills"
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=repository,
                check=True,
                capture_output=True,
            )
            write_skill(skills_dir, "sample")
            commit_all(repository, "Add the only skill")

            result = run_validator(skills_dir)

            self.assertIn("ok: 1 skill in 1 tree.", result.stdout)

    def test_it_says_which_citations_go_unchecked(self) -> None:
        result = run_validator(SKILLS_DIR)

        self.assertIn("in backticks or bold", result.stdout)
        self.assertIn("plain prose is not checked", result.stdout)


if __name__ == "__main__":
    unittest.main()
