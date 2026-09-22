#!/usr/bin/env python3
"""Validate one or more plugin skills trees in a single run: links resolve
inside their own tree, skill names cited in bold or backticks resolve to a
skill directory in the checked trees, and every SKILL.md frontmatter names its
own directory and carries a description.

Deleting a skill is what leaves a dead reference behind, so the names git has
carried under these directories decide which emphasised words are skill names.

Every tree goes in one run. Two rules need the whole picture and a per-plugin
loop cannot give it to them. A citation can name a skill in a sibling plugin,
and a missing principle- prefix can only be recognised when that sibling is
visible. A tree split off an older one has a git history starting at the move,
so the deleted-skill rule only works when the trees share one historical set.

With no argument this validates every `plugins/*/skills` tree, which is what
CI runs. Naming trees on the command line checks only those, and turns both
whole-picture rules off for the trees left out."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


__all__ = ["main", "validate_skills_tree", "validate_skills_trees"]

LINK_RE = re.compile(r"\]\(([^)\n]*)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# Skills are cited as **name** or `name`, never as markdown links.
EMPHASIS_RE = re.compile(r"\*\*([^*\n]+)\*\*|`([^`\n]+)`")
SKILL_FRAME_RE = re.compile(r"(?:\*\*([^*\n]+)\*\*|`([^`\n]+)`)\s+skill\b")
SKILL_NAME_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+")

HISTORY_UNAVAILABLE = (
    "git could not read this tree's history, so references to deleted skills "
    "went unchecked and only the weaker rules ran. Validate inside a full "
    "checkout; CI needs actions/checkout with fetch-depth: 0."
)

# Skills that ship with the harness or another plugin, so this tree names them
# on purpose and they never resolve to a directory here.
#
# Membership means the name resolves for a reader, just not in this repository.
# A skill this plugin deleted does not qualify, however loudly some document
# says so. Exempting one globally hides every stale reference to it added
# afterwards, and catching those is why this validator exists. A document that
# has to discuss a deleted skill names it in plain prose, never in emphasis,
# the way UPSTREAM.md does.
EXTERNAL_SKILLS = frozenset(
    {
        "babysit",
        "databricks-use-dbt-models",
        "loop",
        "recall",
        "verify",
        "writing-skills",
    }
)


def strip_fenced_code(text: str) -> str:
    # Replace fenced content with a same-length run of newlines so line
    # numbers in reported problems still point at the right source line.
    return FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def link_targets(text: str) -> list[str]:
    targets = []
    for match in LINK_RE.finditer(strip_fenced_code(text)):
        raw = match.group(1).strip()
        if raw.startswith("<"):
            end = raw.find(">")
            raw = raw[1:end] if end != -1 else raw[1:]
        targets.append(raw.split()[0] if raw.split() else raw)
    return targets


def path_is_inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def link_problems(skills_dir: Path) -> list[str]:
    root = skills_dir.resolve()
    problems = []
    for path in sorted(root.rglob("*.md")):
        for target in link_targets(path.read_text()):
            if not target or target.startswith("#"):
                continue
            scheme = re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target)
            if scheme:
                continue
            encoded = target.split("?")[0].split("#")[0]
            if not encoded:
                continue
            decoded = unquote(encoded)
            resolved = (path.parent / decoded).resolve()
            if Path(decoded).is_absolute() or not path_is_inside(root, resolved):
                problems.append(f"{path.relative_to(root)} -> {target} (escapes skills tree)")
            elif not resolved.exists():
                problems.append(f"{path.relative_to(root)} -> {target} (missing)")
    return problems


def skill_names(skills_dir: Path) -> set[str]:
    return {
        entry.name
        for entry in skills_dir.iterdir()
        if entry.is_dir() and (entry / "SKILL.md").exists()
    }


def skill_families(names: set[str]) -> set[str]:
    # A prefix shared by two or more real skill directories, such as
    # "principle", marks a naming family. A hyphenated token in that family
    # is a skill reference; "read-only" and other hyphenated prose is not.
    prefixes = Counter(name.split("-")[0] for name in names if "-" in name)
    return {prefix for prefix, count in prefixes.items() if count >= 2}


def skill_names_in_history(skills_dir: Path) -> set[str] | None:
    """Every name that held a SKILL.md in this directory along HEAD's history.

    Scoped to the checked-out ref, not every ref: `--all` made the answer
    depend on which branches a clone happens to carry, and let a name some
    merged-and-abandoned branch once used count as historical for good.

    "Answer in **caveman** register" reads as prose until you know caveman was
    a skill here, which is why this set, and not the shape of the word, is what
    exposes a stale reference in every citation syntax.

    Returns None when git cannot answer, outside a checkout or in a shallow
    clone whose truncated log would omit the very commit that deleted a skill.
    Callers report that rather than reading it as an empty history: this rule
    having been skipped is the difference between a checked tree and an
    unchecked one.
    """
    try:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=skills_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if shallow != "false":
            return None
        listing = subprocess.run(
            ["git", "log", "HEAD", "--format=", "--name-only", "--relative", "--", "."],
            cwd=skills_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {
        path.split("/")[0]
        for path in listing.split("\n")
        if path.endswith("/SKILL.md") and path.count("/") == 1
    }


def referenced_skills(
    text: str, families: set[str], historical: set[str], live_names: set[str]
) -> set[str]:
    body = strip_fenced_code(text)
    references = set()
    for match in EMPHASIS_RE.finditer(body):
        token = (match.group(1) or match.group(2)).strip()
        if token in historical:
            references.add(token)
        elif SKILL_NAME_RE.fullmatch(token) and token.split("-")[0] in families:
            references.add(token)
        elif (
            SKILL_NAME_RE.fullmatch(token)
            and token not in live_names
            and f"principle-{token}" in live_names
        ):
            references.add(token)
    for match in SKILL_FRAME_RE.finditer(body):
        token = (match.group(1) or match.group(2)).strip()
        if ":" in token or "*" in token:
            continue
        if re.fullmatch(r"[a-z][a-z0-9-]*", token):
            references.add(token)
    return references - EXTERNAL_SKILLS


def documents_naming_skills(skills_dir: Path) -> list[Path]:
    documents = list(skills_dir.rglob("*.md"))
    agents_dir = skills_dir.parent / "agents"
    if agents_dir.is_dir():
        documents.extend(agents_dir.rglob("*.md"))
    return sorted(documents)


def reference_remedy(reference: str, historical: set[str]) -> str:
    if reference in historical:
        return "was a skill here and was deleted. Drop the reference or restore the directory"
    return "no skill directory of that name. Drop the emphasis if the word is prose"


def prefixed_reference_remedy(reference: str) -> str:
    return f"cite **principle-{reference}** instead"


def skill_reference_problems(
    skills_dir: Path, historical: set[str], elsewhere: dict[str, str]
) -> list[str]:
    # Three rules, each covering what the others cannot. History catches a
    # deleted name in any citation syntax, but only names git ever carried.
    # Prefix families catch a hyphenated name that never existed, such as a
    # misremembered principle-*. A missing principle- prefix has to be checked
    # separately because its first segment may not be a skill family. The
    # "... skill" frame catches a non-hyphenated name that never existed,
    # which has no other tell. Dropping any one leaves a stale reference class
    # with nothing looking for it.
    root = skills_dir.resolve()
    names = skill_names(root)
    families = skill_families(names)
    # A sibling can own a cited skill or the corresponding prefixed skill.
    # Both cases need the shared live-name set from this invocation.
    known = historical | set(elsewhere)
    live_names = names | set(elsewhere)
    problems = []
    for path in documents_naming_skills(root):
        inside = path_is_inside(root, path)
        label = path.relative_to(root if inside else root.parent)
        for reference in sorted(
            referenced_skills(path.read_text(), families, known, live_names)
        ):
            if reference not in live_names:
                if f"principle-{reference}" in live_names:
                    remedy = prefixed_reference_remedy(reference)
                else:
                    remedy = reference_remedy(reference, historical)
                problems.append(f"{label} -> **{reference}** ({remedy})")
    return problems


def frontmatter_value(text: str, key: str) -> str | None:
    block = FRONTMATTER_RE.match(text)
    if not block:
        return None
    for line in block.group(1).split("\n"):
        if line.startswith(f"{key}: "):
            return line[len(key) + 2 :]
    return None


def skill_metadata_problems(skills_dir: Path) -> list[str]:
    problems = []
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if not entry.is_dir() or not skill_md.exists():
            continue
        text = skill_md.read_text()
        name = frontmatter_value(text, "name")
        if name != entry.name:
            problems.append(
                f'{entry.name}/SKILL.md: frontmatter name "{name}" '
                f'!= directory "{entry.name}"'
            )
        description = frontmatter_value(text, "description")
        if not description:
            problems.append(f"{entry.name}/SKILL.md: no description frontmatter")
    return problems


def validate_skills_tree(
    skills_dir: Path, historical: set[str], elsewhere: dict[str, str]
) -> list[str]:
    """Problems in one tree, given what every tree together knows.

    `historical` is every name that ever held a SKILL.md in any of the trees
    being validated. `elsewhere` maps a live skill name to the plugin that
    owns it, for the skills this tree does not own.
    """
    return (
        link_problems(skills_dir)
        + skill_reference_problems(skills_dir, historical, elsewhere)
        + skill_metadata_problems(skills_dir)
    )


def validate_skills_trees(trees: list[Path]) -> tuple[list[str], bool]:
    """Problems across every tree, and whether the deleted-skill rule ran.

    Both halves are the result. A caller that reads only the problems cannot
    tell a checked tree from one where git answered nothing.
    """
    histories = [skill_names_in_history(tree.resolve()) for tree in trees]
    # One shared set. A tree split out of another starts its own history at
    # the move commit, so on its own it remembers no deletion at all.
    historical: set[str] = set().union(*[names for names in histories if names])
    owners = {
        name: tree.resolve().parent.name
        for tree in trees
        for name in skill_names(tree.resolve())
    }
    problems = []
    for tree in trees:
        local = skill_names(tree.resolve())
        elsewhere = {
            name: owner for name, owner in owners.items() if name not in local
        }
        problems += validate_skills_tree(tree, historical, elsewhere)
    return problems, all(names is not None for names in histories)


def ci_enabled() -> bool:
    return os.environ.get("CI", "").strip().lower() not in {"", "0", "false"}


def count_phrase(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def default_trees() -> list[Path]:
    """Every skills tree in the repository, swept rather than named.

    The default used to be `plugins/pstack/skills` alone. That is one tree
    of eleven, with both whole-picture rules switched off, and it exited 0,
    so the bare command gave a false pass on exactly the narrowing this
    script was written to catch. Sweeping the directory cannot go stale
    when a plugin arrives.
    """
    return sorted((Path(__file__).resolve().parents[1] / "plugins").glob("*/skills"))


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    trees = [Path(argument) for argument in arguments] or default_trees()
    if not trees:
        print("FAIL: no plugins/*/skills tree to validate", file=sys.stderr)
        return 1
    absent = [tree for tree in trees if not tree.is_dir()]
    if absent:
        for tree in absent:
            print(f"FAIL: {tree} (no skills tree there)", file=sys.stderr)
        return 1
    problems, history_read = validate_skills_trees(trees)
    for problem in problems:
        print(f"FAIL: {problem}", file=sys.stderr)
    if not history_read:
        # Said on every degraded run, passing or failing. Withholding it
        # whenever something else failed would leave the runs that need it
        # most looking exactly like a run that checked every deleted name.
        # CI has no excuse for a history it cannot read, so it fails there. A
        # developer working from a tarball gets the warning and weaker rules.
        print(f"DEGRADED: {HISTORY_UNAVAILABLE}", file=sys.stderr)
        return 1 if problems or ci_enabled() else 0
    if problems:
        return 1
    skills = sum(len(skill_names(tree.resolve())) for tree in trees)
    print(
        f"ok: {count_phrase(skills, 'skill')} in "
        f"{count_phrase(len(trees), 'tree')}. Every markdown link resolves, "
        "every skill citation in backticks or bold resolves to a skill in the "
        "checked trees and keeps a required principle- prefix, and every "
        "SKILL.md frontmatter names its own directory and carries a "
        "description. A skill named in plain prose is not checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
