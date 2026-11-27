"""Write references/<language>.md from the guideline files.

Usage: guideline_references.py [--check]
With --check, exit 1 and name each reference that is not current.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))  # python -I leaves the script dir out

from guideline_files import Guideline, load_guidelines

SKILL = SCRIPTS.parent
REFERENCES = SKILL / "references"
TITLES = {
    "python": ("Python", ("python",)),
    "typescript": ("TypeScript and JavaScript", ("typescript", "javascript")),
    "csharp": ("C#", ("csharp",)),
    "gdscript": ("GDScript and Godot", ("gdscript",)),
}


def entry(guideline: Guideline) -> str:
    body = " ".join(guideline.body.split())
    return f"- `{guideline.id}` ({guideline.severity}): {body}"


def reference(title: str, languages: tuple[str, ...],
              guidelines: list[Guideline]) -> str:
    matching = [
        guideline for guideline in guidelines
        if guideline.enabled and set(guideline.languages) & set(languages)
    ]
    own = [g for g in matching if not g.id.startswith("all.")]
    shared = [g for g in matching if g.id.startswith("all.")]
    lines = [
        f"# {title} guidelines",
        "",
        "Generated from `guidelines/` by `scripts/guideline_references.py`.",
        "Edit the guideline files, then run the script.",
        "",
        *(entry(guideline) for guideline in own),
        "",
        "## All languages",
        "",
        *(entry(guideline) for guideline in shared),
    ]
    return "\n".join(lines) + "\n"


def expected() -> dict[Path, str]:
    guidelines, problems = load_guidelines(SKILL / "guidelines")
    if problems:
        raise SystemExit("\n".join(problems))
    ordered = sorted(guidelines, key=lambda guideline: guideline.id)
    return {
        REFERENCES / f"{name}.md": reference(title, languages, ordered)
        for name, (title, languages) in TITLES.items()
    }


def main(arguments: list[str]) -> int:
    stale = [
        path for path, text in expected().items()
        if not path.is_file() or path.read_text(encoding="utf-8") != text
    ]
    if "--check" in arguments:
        for path in stale:
            print(f"{path.relative_to(SKILL)} is not current; run "
                  f"scripts/guideline_references.py")
        return 1 if stale else 0
    for path, text in expected().items():
        if path in stale:
            path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
