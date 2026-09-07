"""One placement rule for agent git worktrees, shared by every tool.

In plain words: this says where an AI agent's private copy of the repo goes -
a fixed folder inside the repo instead of wherever each tool would pick - so
the copies are all in one predictable place and easy to find or delete.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_ENV_VAR = "DOTAI_WORKTREE_BASE"
DEFAULT_BASE = ".nikki-agents/worktrees"


def base_for(repo_root: Path | str) -> Path:
    """Directory holding every agent worktree of the repo at repo_root."""
    relative = os.environ.get(BASE_ENV_VAR) or DEFAULT_BASE
    return Path(repo_root) / relative


def is_inside_base(target: Path | str, repo_root: Path | str) -> bool:
    """True when target lands inside the base once ".." and links resolve."""
    base = base_for(repo_root).resolve()
    return Path(target).resolve().is_relative_to(base)
