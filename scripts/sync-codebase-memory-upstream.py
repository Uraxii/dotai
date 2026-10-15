#!/usr/bin/env python3
"""Copy codebase-memory-mcp's installer assets into plugins/codebase-memory.

`codebase-memory-mcp install` writes a skill, three agents per harness, and
global instruction text into the user's home. This plugin ships the same
content, so this script takes it from an upstream source checkout instead of
from an install: the skill and instruction strings come out of
src/cli/cli.c, and the agent files come from compiling upstream's own
renderer, src/cli/agent_profiles.c, with a C compiler.

Usage:

    git clone --branch v0.11.0 https://github.com/DeusData/codebase-memory-mcp /tmp/cbm
    scripts/sync-codebase-memory-upstream.py /tmp/cbm

Rerun it after an upstream release and review the diff.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "codebase-memory"
PLUGIN_NAME = "codebase-memory"
SERVER_NAME = "codebase-memory-mcp"
TIERS = ("codebase-memory-scout", "codebase-memory", "codebase-memory-auditor")
DIALECT_CLAUDE = 0
DIALECT_COPILOT = 4

RENDER_DRIVER = r"""
#include "cli/agent_profiles.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int cbm_toml_escape_basic_string(const char *in, char *out, size_t out_size) {
    if (strlen(in) + 1 > out_size) return 1;
    strcpy(out, in);
    return 0;
}
int main(int argc, char **argv) {
    char *text = cbm_render_graph_profile((cbm_graph_profile_dialect_t)atoi(argv[1]),
                                          (cbm_graph_tier_t)atoi(argv[2]),
                                          CBM_GRAPH_ACCESS_DIRECT, argv[3]);
    if (!text) return 1;
    fputs(text, stdout);
    free(text);
    return 0;
}
"""

SKILL_ANCHOR = "## Exploration Workflow\n"
SKILL_SETUP = """## Before the First Query
1. If the graph tools are deferred, load them with ToolSearch. Use the query `+codebase-memory list_projects index_repository search_graph trace_path get_code_snippet` with `max_results` 5.
2. Call `index_repository` with the path of the current checkout. The call is fast on an indexed checkout and returns the project name. A worktree is a separate checkout, so index it too.
3. Pass that project name to every later graph tool call.

"""

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\", "?": "?"}


def c_string_constant(source: str, name: str) -> str:
    """Return the decoded value of `static const char name[] = "..." "...";`."""
    match = re.search(rf"\bchar {re.escape(name)}\[\] =", source)
    if not match:
        raise SystemExit(f"cli.c no longer defines {name}")
    position = match.end()
    pieces = []
    while True:
        if source.startswith("/*", position):
            position = source.index("*/", position) + 2
        elif source.startswith("//", position):
            position = source.index("\n", position)
        elif source[position].isspace():
            position += 1
        elif source[position] == ";":
            return "".join(pieces)
        elif source[position] == '"':
            position += 1
            while source[position] != '"':
                if source[position] == "\\":
                    pieces.append(ESCAPES[source[position + 1]])
                    position += 2
                else:
                    pieces.append(source[position])
                    position += 1
            position += 1
        else:
            raise SystemExit(f"unexpected {source[position]!r} in {name}")


def render_profiles(upstream: Path, dialect: int) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as scratch:
        driver = Path(scratch) / "render.c"
        binary = Path(scratch) / "render"
        driver.write_text(RENDER_DRIVER)
        subprocess.run(
            [
                "cc", "-std=c11", f"-I{upstream / 'src'}", f"-I{upstream / 'vendored'}",
                "-o", str(binary), str(driver),
                str(upstream / "src/cli/agent_profiles.c"),
                str(upstream / "vendored/yyjson/yyjson.c"),
            ],
            check=True,
        )
        return {
            slug: subprocess.run(
                [str(binary), str(dialect), str(tier), SERVER_NAME],
                check=True, capture_output=True, text=True,
            ).stdout
            for tier, slug in enumerate(TIERS)
        }


def as_claude_plugin_agent(text: str) -> str:
    """Point a Claude agent at this plugin's namespaced MCP tools and skill.

    Claude Code names a plugin's MCP tools mcp__plugin_<plugin>_<server>__<tool>
    and its skills <plugin>:<skill>, and ignores mcpServers and permissionMode
    in plugin agent frontmatter.
    """
    text = text.replace(
        f"mcp__{SERVER_NAME}__", f"mcp__plugin_{PLUGIN_NAME}_{SERVER_NAME}__"
    )
    text = text.replace(f"mcpServers: [{SERVER_NAME}]\n", "")
    text = text.replace("permissionMode: plan\n", "")
    return text.replace(
        "skills: [codebase-memory]\n", f"skills: [{PLUGIN_NAME}:codebase-memory]\n"
    )


def with_local_setup(skill: str) -> str:
    """Add the session setup steps that upstream's skill lacks."""
    if SKILL_ANCHOR not in skill:
        raise SystemExit(f"upstream skill no longer has {SKILL_ANCHOR.strip()!r}")
    return skill.replace(SKILL_ANCHOR, SKILL_SETUP + SKILL_ANCHOR, 1)


def wanted_files(upstream: Path) -> dict[Path, str]:
    cli_source = (upstream / "src/cli/cli.c").read_text(encoding="utf-8")
    files = {
        Path("skills/codebase-memory/SKILL.md"): with_local_setup(
            c_string_constant(cli_source, "skill_content")
        ),
        Path("hooks/instructions.md"): c_string_constant(
            cli_source, "agent_instructions_content"
        ),
    }
    for slug, text in render_profiles(upstream, DIALECT_CLAUDE).items():
        files[Path(f"agents/claude/{slug}.md")] = as_claude_plugin_agent(text)
    for slug, text in render_profiles(upstream, DIALECT_COPILOT).items():
        files[Path(f"agents/copilot/{slug}.agent.md")] = text
    return files


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("upstream", type=Path, help="codebase-memory-mcp source checkout")
    options = parser.parse_args(arguments)
    for relative, text in wanted_files(options.upstream.resolve()).items():
        target = PLUGIN_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.relative_to(PLUGIN_ROOT.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
