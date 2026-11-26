#!/usr/bin/env python3
"""Generate every plugin manifest and both marketplace files from one list.

Every plugin in the repository needs a `plugin.json`, a
`.claude-plugin/plugin.json`, and a `.codex-plugin/plugin.json`, and each
must appear in `.claude-plugin/marketplace.json`, in
`.agents/plugins/marketplace.json`, and in the plugin table in `README.md`.
Each plugin and each of its skills also gets a `README.md`, except a
plugin README listed in HAND_WRITTEN_READMES.
That is three manifests, two marketplace entries, and one table row per
plugin, whose names, versions, and descriptions all have to agree.

A plugin that only suits some harnesses lists them in `harnesses`; it then
gets no manifest or marketplace entry for the others.

Edit PLUGINS below and rerun this script. Never hand-edit a generated
file: `--check` exits 2 when one has drifted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/Uraxii/dotai"
AUTHOR = {"name": "Uraxii", "url": "https://github.com/Uraxii"}
MARKETPLACE_DESCRIPTION = (
    "Skills and agents for software development work."
)

# The version a plugin gets when its entry below carries no explicit one.
FIRST_RELEASE = "1.0.0"

PLUGIN_TABLE_START = "<!-- dotai:plugins:start -->"
PLUGIN_TABLE_END = "<!-- dotai:plugins:end -->"
# Plugins whose README.md a person writes; the generator leaves it alone.
HAND_WRITTEN_READMES = {"ox-vibesec", "pstack", "shunt"}
HOOK_WIRING_PATHS = {
    "claude": Path("hooks/claude-hooks.json"),
    "codex": Path("hooks/codex-hooks.json"),
    "copilot": Path("hooks.json"),
}

def pstack_entry() -> dict[str, object]:
    """pstack is the unmodified michael-denyer/pstack-claude plugin.

    Its own manifest is the source, so the generator reads its name,
    version, and description and never writes under plugins/pstack.
    """
    manifest = json.loads(
        (REPOSITORY_ROOT / "plugins/pstack/.claude-plugin/plugin.json").read_text()
    )
    return {
        "name": manifest["name"],
        "version": manifest["version"],
        "description": manifest["description"],
        "marketplace_version": True,
    }


PSTACK = pstack_entry()

PLUGINS: list[dict[str, object]] = [
    PSTACK,
    {
        "name": "artifact",
        "version": "1.1.0",
        "description": (
            "Explain a code change as a self-contained interactive HTML page."
        ),
        "short": "Rich HTML explanations of a diff, branch, or PR.",
        "long": (
            "Turns a diff, branch, or pull request into one HTML file that "
            "explains what moved, why it moved, and what a reviewer should "
            "look at first. The page carries its own styles and scripts, so "
            "it opens in a browser with no server behind it."
        ),
        "keywords": ["html", "code-review"],
        "prompts": [
            "Explain this branch as an HTML page.",
            "Turn the diff against main into a reviewable HTML explainer.",
        ],
    },
    {
        "name": "notion",
        "version": "1.1.0",
        "description": (
            "Reach Notion from the command line, and publish a code-change "
            "explainer as a Notion page."
        ),
        "short": "Notion CLI access and Notion-page explainers.",
        "long": (
            "Drives the Notion API through the ntn command line tool: read "
            "and search content, create pages, query databases, upload "
            "files, and deploy workers. Also publishes an explanation of a "
            "diff, branch, or pull request as a native Notion page."
        ),
        "keywords": ["notion", "cli"],
        "prompts": [
            "Create a Notion page from these notes.",
            "Explain this pull request as a Notion page.",
        ],
    },
    {
        "name": "azure",
        "version": "1.1.0",
        "description": (
            "Read Azure DevOps projects, repos, pipelines, releases, and "
            "work items over the REST API."
        ),
        "short": "Read-only Azure DevOps queries.",
        "long": (
            "Answers inventory questions about an Azure DevOps organization "
            "over the read-only REST API: which projects and repositories "
            "exist, what the build and release pipelines did, which "
            "environments and Kubernetes resources they deploy to, and "
            "which work items a WIQL query returns."
        ),
        "keywords": ["azure-devops", "ci"],
        "prompts": [
            "List the build pipelines in this Azure DevOps project.",
            "Which release last deployed to the production environment?",
        ],
    },
    {
        "name": "llm-wiki",
        "version": "1.2.0",
        "description": (
            "Keep research findings in a searchable project knowledgebase "
            "instead of re-deriving them."
        ),
        "short": "Project knowledgebase for research findings.",
        "long": (
            "Captures a finding and the source it came from in a "
            "project-local .kb store, or a global one, through the llmwiki "
            "command line tool. Search matches on meaning, so an answer "
            "written down in an earlier session comes back instead of being "
            "researched again."
        ),
        "keywords": ["knowledge-base", "research"],
        "prompts": [
            "Save what we just found out to the knowledgebase.",
            "Search the knowledgebase before researching this.",
        ],
    },
    {
        "name": "proton",
        "version": "1.1.0",
        "description": (
            "Read and store secrets in Proton Pass through pass-cli, so none "
            "lands in a repo or a shell history."
        ),
        "short": "Proton Pass secret retrieval and storage.",
        "long": (
            "Fetches an API key, token, password, or SSH key from Proton "
            "Pass with the pass-cli tool, authenticating with a personal "
            "access token held in the operating system keyring. Every read "
            "states its reason, an expired session recovers on its own, and "
            "a new secret goes back to Proton Pass rather than into a file."
        ),
        "keywords": ["secrets", "proton-pass"],
        "prompts": [
            "Get the API key for this service from Proton Pass.",
            "Store this new token in Proton Pass.",
        ],
    },
    {
        "name": "sandbox",
        "version": "1.1.0",
        "description": (
            "Give an agent a throwaway podman container with its own clone "
            "of the repo, ports, and a virtual display."
        ),
        "short": "Throwaway podman containers for agent work.",
        "long": (
            "Brings up a disposable podman container holding a private clone "
            "of a repository, published ports, and a virtual display the "
            "agent can screenshot. Use it when work must not touch the real "
            "checkout, when several agents each need their own tree and "
            "ports on one machine, or when a windowed application has to run "
            "with no desktop available."
        ),
        "keywords": ["podman", "containers"],
        "prompts": [
            "Run this migration in a throwaway podman sandbox.",
            "Start a sandbox container and screenshot the app.",
        ],
    },
    {
        "name": "codex-worker",
        "version": "1.1.0",
        "harnesses": ["claude"],
        "description": (
            "Delegate a code change from Claude Code to an outside Codex CLI "
            "worker."
        ),
        "short": "Run Codex CLI workers from Claude Code.",
        "long": (
            "Guides a Claude Code session that hands a code change to a Codex "
            "CLI run. Covers the sandbox scope, the background run, "
            "monitoring, follow-ups, and an independent review. Do not use it "
            "when the agent itself runs inside Codex."
        ),
        "keywords": ["delegation", "cli-worker"],
        "prompts": [
            "Delegate this change to a Codex worker.",
            "Run a Codex worker on this branch and review its diff.",
        ],
    },
    {
        # Claude Code loads hooks/hooks.json implicitly. OX --status checks that exact path.
        "name": "ox-vibesec",
        "version": "1.3.0",
        "harnesses": ["claude"],
        "hooks": ["devin"],
        "devin_manifest": {
            "description": "Run OX VibeSec security guidance and tool checks in Devin.",
            "skills": [],
        },
        "description": (
            "Wire the OX Security VibeSec hooks and its status and login "
            "commands through a plugin instead of settings.json."
        ),
    },
    {
        "name": "mpocock",
        "version": "1.4.0",
        "hooks": ["claude", "codex"],
        "description": (
            "Matt Pocock's handoff and wayfinder skills: compact a "
            "conversation into a handoff document, and plan work too big for "
            "one session as a map of decision tickets."
        ),
        "short": "Session handoffs and wayfinding maps.",
        "long": (
            "handoff writes down what a session established, what it decided, "
            "and what is still open, in a form a fresh agent reads instead of "
            "the transcript. wayfinder charts work too big for one session as "
            "a shared map of decision tickets on the issue tracker, then "
            "resolves them one at a time. Both come from Matt Pocock's skills "
            "repository, https://github.com/mattpocock/skills, under MIT."
        ),
        "keywords": ["handoff", "context", "planning"],
        "prompts": [
            "Write a handoff document for this session.",
            "Wayfind this idea into a map of decision tickets.",
        ],
    },
    {
        "name": "skills",
        "version": "1.2.0",
        "hooks": ["claude", "codex", "copilot"],
        "description": (
            "Review and author SKILL.md files, finding and repairing the "
            "smells that stop a skill triggering."
        ),
        "short": "Review and repair SKILL.md files.",
        "long": (
            "Reads a SKILL.md against a list of known smells, such as a "
            "description that never says when to use the skill, "
            "instructions that restate what the model already does, and a "
            "body too long to load. Reports each smell with its repair, and "
            "writes a new skill to the same bar."
        ),
        "keywords": ["skill-authoring", "review"],
        "prompts": [
            "Review this SKILL.md and tell me why it never triggers.",
            "Write a new skill for this workflow.",
        ],
    },
    {
        "name": "codebase-memory",
        "version": "2.3.0",
        "hooks": ["claude", "copilot"],
        "agents": ["claude", "copilot"],
        "mcp_servers": {
            "codebase-memory-mcp": {"command": "codebase-memory-mcp", "args": []}
        },
        "description": (
            "Query a code graph through the codebase-memory-mcp server, "
            "skill, and graph-verification agents."
        ),
        "short": "Code-graph MCP tools, skill, and agents for Claude Code and Copilot CLI.",
        "long": (
            "Registers the codebase-memory-mcp server and ships upstream's "
            "codebase-memory skill, its scout, verify, and auditor agents, "
            "and its hooks. A session-start and subagent-start hook injects "
            "the graph-first instructions and any graph context into the "
            "session and every subagent. Needs the codebase-memory-mcp "
            "binary on PATH. Claude Code and Copilot CLI only for now."
        ),
        "keywords": ["code-intelligence", "static-analysis", "mcp"],
        "prompts": [
            "Who calls this function?",
            "What breaks if I change this symbol?",
        ],
    },
    {
        "name": "caveman",
        "version": "1.1.0",
        "description": (
            "Answer in a compressed register that drops filler and keeps "
            "every technical fact."
        ),
        "short": "A terse reply style that keeps the substance.",
        "long": (
            "Switches replies into a compressed style for the rest of the "
            "session: no pleasantries, no hedging, no narration of tool "
            "calls. Numbers, code, error strings, and negations stay exact, "
            "and the style steps aside for security warnings and for "
            "anything a reader could misread when compressed."
        ),
        "keywords": ["writing-style", "token-efficiency"],
        "prompts": [
            "Turn on caveman mode for the rest of this session.",
            "Be brief and use fewer tokens from here on.",
        ],
    },
    {
        "name": "asd-ste100",
        "version": "1.1.0",
        "description": (
            "Rewrite ambiguous English into ASD-STE100 Simplified Technical "
            "English so agents and readers cannot misread it."
        ),
        "short": "Rewrite English so it has one reading.",
        "long": (
            "Applies the ASD-STE100 Simplified Technical English rules to "
            "text that an agent or a downstream system must parse without a "
            "human to resolve ambiguity: tool descriptions, error messages, "
            "inter-agent instructions, and status reports. Ships a "
            "stdlib-only linter for the structural rules. Vendored unedited "
            "from danyuchn/asd-ste100-skill."
        ),
        "keywords": ["writing-style", "controlled-language"],
        "prompts": [
            "Rewrite this error message in Simplified Technical English.",
            "Make this tool description impossible for an agent to misread.",
        ],
    },
    {
        "name": "gaming",
        "description": (
            "Install ANR FG frame generation into PC games through "
            "OptiScaler, with GPU spoofing and per-game recipes."
        ),
        "short": "Install ANR FG into a game.",
        "long": (
            "Installs ANR FG (Apex Neural Rendering frame generation) into a "
            "PC game through OptiScaler and spoofs the GPU so the game offers "
            "the DLSS frame generation that ANR replaces. Covers Windows and "
            "Linux/Proton, keeps per-game spoof recipes with evidence labels, "
            "and looks up the OptiScaler wiki and ANR issues for games it "
            "does not know yet."
        ),
        "keywords": ["gaming", "frame-generation", "optiscaler"],
        "prompts": [
            "Install ANR frame generation into The Witcher 3.",
            "Get DLSS frame gen working on my RTX 3080 with ANR.",
        ],
    },
    {
        "name": "steer",
        "version": "1.4.2",
        "hooks": ["claude", "devin"],
        "devin_manifest": {
            "description": "Remind Devin when to ask before editing Markdown.",
        },
        "skills": False,
        "description": (
            "Harness hooks that steer agent behaviour, independent of any skill."
        ),
        "short": "Harness hooks independent of skills.",
        "long": (
            "Claude Code checks Markdown edits and requests a recap when appropriate. "
            "Devin does not provide a transcript to plugin hooks. Its "
            "UserPromptSubmit hook reminds the agent to ask before editing Markdown. "
            "It does not block edits or request a recap."
        ),
        "keywords": ["harness", "hooks"],
        "prompts": [
            "Install the steer harness hooks.",
        ],
    },
    {
        "name": "shunt",
        "version": "1.0.0",
        "marketplace_version": True,
        "hooks": ["claude", "codex", "copilot", "devin"],
        "copilot_hook_path": "hooks/copilot-hooks.json",
        "devin_manifest": {
            "description": "Delegate large reads to a small subagent.",
        },
        "skills": False,
        "description": "Delegate large reads to subagents to save main-agent context.",
        "short": "Delegate large reads to subagents.",
        "long": (
            "A vendored, patched fork of Spotify's shunt plugin from "
            "portal-ai-plugins. Hooks block full large-file reads on Claude "
            "Code, Copilot CLI, and Devin, and large Bash reads on Codex. They "
            "redirect agents to the bulk-reader skill. Small reader subagents "
            "return concise answers with line citations; chunked reads handle "
            "exact content and edits. See "
            "plugins/shunt/upstream-source.md for source and patch details."
        ),
        "keywords": ["token-optimization", "delegation"],
        "prompts": [
            "Use the bulk-reader skill to summarize this large file.",
        ],
    },
    {
        "name": "personal-instructions",
        "version": "1.0.9",
        "hooks": ["claude", "codex", "copilot"],
        "copilot_hook_path": "hooks/copilot-hooks.json",
        "devin_manifest": {
            "description": "Load personal instructions as an always-on Devin rule.",
        },
        "devin_rule_sources": ["instructions.md", "main-agent-instructions.md"],
        "skills": False,
        "description": (
            "Inject a hand-edited instructions.md at session start and, where "
            "the harness has a subagent-start hook, subagent start."
        ),
        "short": "Your personal rules in every session.",
        "long": (
            "Reads the plugin's instructions.md at session start and subagent "
            "start and adds it to context in Claude Code, Codex, and Copilot "
            "CLI. Edit that file to change your shared rules. "
            "Rules only the main agent should get go in "
            "main-agent-instructions.md, which is injected at session start "
            "only. Fresh subagents do not get it; forked subagents inherit "
            "it from the parent's history. Devin uses one always-on rule made "
            "from both files, with no separate main-agent scope. Run "
            "`python3 scripts/generate-plugin-manifests.py` after editing either file."
        ),
        "keywords": ["harness", "hooks", "instructions"],
        "prompts": [
            "Install my personal instructions into every session.",
        ],
    },
]


ALL_HARNESSES = ["claude", "codex", "copilot"]


def on_harness(plugin: dict[str, object], harness: str) -> bool:
    """A plugin is on every harness unless its entry lists `harnesses`."""
    return harness in plugin.get("harnesses", ALL_HARNESSES)


def version_of(plugin: dict[str, object]) -> str:
    return str(plugin.get("version", FIRST_RELEASE))


def claude_agent_paths(plugin: dict[str, object], root: Path = REPOSITORY_ROOT) -> list[str]:
    agents = root / "plugins" / str(plugin["name"]) / "agents" / "claude"
    return [f"./agents/claude/{path.name}" for path in sorted(agents.glob("*.md"))]


def hook_wiring_paths(plugin: dict[str, object]) -> dict[str, Path]:
    paths = HOOK_WIRING_PATHS.copy()
    if copilot_path := plugin.get("copilot_hook_path"):
        paths["copilot"] = Path(str(copilot_path))
    if "devin_manifest" not in plugin:
        return paths
    if paths["copilot"] == Path("hooks.json"):
        if "copilot" in plugin.get("hooks", []):
            raise ValueError(f"{plugin['name']}: copilot and devin hooks both use hooks.json")
        del paths["copilot"]
    paths["devin"] = Path("hooks.json")
    return paths


def core_manifest(plugin: dict[str, object]) -> dict[str, object]:
    return {
        "name": plugin["name"],
        "version": version_of(plugin),
        "description": plugin["description"],
        "author": AUTHOR,
    }


def claude_manifest(plugin: dict[str, object], root: Path = REPOSITORY_ROOT) -> dict[str, object]:
    manifest = core_manifest(plugin)
    if "claude" in plugin.get("hooks", []):
        manifest["hooks"] = "./hooks/claude-hooks.json"
    if "claude" in plugin.get("agents", []):
        manifest["agents"] = claude_agent_paths(plugin, root)
    return manifest


def codex_manifest(plugin: dict[str, object]) -> dict[str, object]:
    hook_harnesses = plugin.get("hooks", [])
    ships_skills = bool(plugin.get("skills", True))
    manifest = core_manifest(plugin)
    manifest["homepage"] = REPOSITORY_URL
    manifest["repository"] = REPOSITORY_URL
    manifest["keywords"] = [
        "codex",
        *(["skills"] if ships_skills else []),
        *plugin["keywords"],
    ]
    capabilities = []
    if ships_skills:
        manifest["skills"] = "./skills/"
        capabilities.append("Skills")
    if "codex" in hook_harnesses:
        manifest["hooks"] = "./hooks/codex-hooks.json"
        capabilities.append("Hooks")
    manifest["interface"] = {
        "displayName": plugin["name"],
        "shortDescription": plugin["short"],
        "longDescription": plugin["long"],
        "developerName": AUTHOR["name"],
        "category": "Developer Tools",
        "capabilities": capabilities,
        "defaultPrompt": plugin["prompts"],
    }
    return manifest


def claude_marketplace() -> dict[str, object]:
    return {
        "name": "Uraxii",
        "owner": {"name": AUTHOR["name"]},
        "description": MARKETPLACE_DESCRIPTION,
        "plugins": [
            {
                "name": plugin["name"],
                "source": f"./plugins/{plugin['name']}",
                **(
                    {"version": version_of(plugin)}
                    if plugin.get("marketplace_version") else {}
                ),
                "description": plugin["description"],
            }
            for plugin in PLUGINS
        ],
    }


def agents_marketplace() -> dict[str, object]:
    return {
        "name": "uraxii",
        "interface": {"displayName": "Uraxii"},
        "plugins": [
            {
                "name": plugin["name"],
                "source": {
                    "source": "url",
                    "url": f"{REPOSITORY_URL}.git",
                    "ref": "main",
                    "path": f"plugins/{plugin['name']}",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
            for plugin in PLUGINS
            if on_harness(plugin, "codex")
        ],
    }


def plugin_table() -> str:
    rows = "\n".join(
        f"| `{plugin['name']}` | {plugin['description']} |" for plugin in PLUGINS
    )
    return f"| Plugin | What it does |\n|---|---|\n{rows}"


def readme_with_plugin_table(root: Path) -> str:
    """The README as it should read, with only its plugin table restamped.

    Twelve names and descriptions copied into the README by hand is a list
    nothing re-asserts, and it drifts the first time a description here
    changes. The prose around the markers stays whatever a person wrote.
    """
    current = (root / "README.md").read_text()
    before, start, rest = current.partition(PLUGIN_TABLE_START)
    _, end, after = rest.partition(PLUGIN_TABLE_END)
    if not start or not end:
        raise SystemExit(
            f"README.md needs a {PLUGIN_TABLE_START} ... {PLUGIN_TABLE_END} block"
        )
    return f"{before}{start}\n\n{plugin_table()}\n\n{end}{after}"


def scalar(value: str) -> str:
    """Decode one YAML scalar: double-quoted, single-quoted, or plain."""
    if value[:1] == '"':
        return json.JSONDecoder().raw_decode(value)[0]
    if value[:1] == "'":
        return value[1:value.rindex("'")].replace("''", "'")
    return value.partition(" #")[0].rstrip()


def skill_frontmatter(text: str, label: object) -> dict[str, str]:
    """Read `name`, `description`, `compatibility`, and `metadata.version`.

    Plain, quoted, and folded (`>-` or `|`) values, like lint-skills.sh reads.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SystemExit(f"{label} has no frontmatter")
    fields: dict[str, list[str]] = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip():
            continue  # a blank line inside a folded block keeps the block going
        if line[:1] in (" ", "\t") and key:
            fields[key].append(line.strip())
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        fields[key] = [] if value in (">", ">-", "|", "|-") else [value]
    found = {
        k: scalar(" ".join(fields.get(k, [])).strip())
        for k in ("name", "description", "compatibility")
    }
    found["version"] = next(
        (
            scalar(entry.partition(":")[2].strip())
            for entry in fields.get("metadata", [])
            if entry.startswith("version:")
        ),
        "",
    )
    return found


def skills_of(plugin: dict[str, object], root: Path) -> list[dict[str, str]]:
    skills_root = root / "plugins" / str(plugin["name"]) / "skills"
    return [
        {"dir": skill_md.parent.name, **skill_frontmatter(skill_md.read_text(encoding="utf-8"), skill_md)}
        for skill_md in sorted(skills_root.glob("*/SKILL.md"))
    ]


def install_section(plugin: dict[str, object], *, include_devin: bool = False) -> str:
    name = plugin["name"]
    blocks = []
    if on_harness(plugin, "claude"):
        blocks.append(
            "Claude Code:\n\n```\n/plugin marketplace add Uraxii/dotai\n"
            f"/plugin install {name}@Uraxii\n```"
        )
    if on_harness(plugin, "codex"):
        blocks.append(
            "Codex CLI:\n\n```\ncodex plugin marketplace add Uraxii/dotai --ref main\n"
            f"codex plugin add {name}@uraxii\n```"
        )
    if on_harness(plugin, "copilot"):
        blocks.append(
            "Copilot CLI:\n\n```\ncopilot plugin marketplace add Uraxii/dotai\n"
            f"copilot plugin install {name}@Uraxii\n```"
        )
    if include_devin and "devin_manifest" in plugin:
        blocks.append(
            "Devin CLI:\n\n```\n"
            f"devin plugins install Uraxii/dotai#plugins/{name}\n```"
        )
    return "## Install\n\n" + "\n\n".join(blocks) + (
        "\n\nFor other harnesses, see the "
        f"[repository README]({REPOSITORY_URL}#install)."
    )


def source_section(path: str) -> str:
    return (
        "## Source\n\n"
        f"- Repository: [Uraxii/dotai]({REPOSITORY_URL})\n"
        f"- This directory: [`{path}`]({REPOSITORY_URL}/tree/main/{path})\n"
        f"- Issues: [{REPOSITORY_URL}/issues]({REPOSITORY_URL}/issues)\n"
        f"- Author: [{AUTHOR['name']}]({AUTHOR['url']})"
    )


GENERATED_NOTE = (
    "<!-- Generated by scripts/generate-plugin-manifests.py. "
    "Do not edit by hand. -->"
)


def plugin_readme(plugin: dict[str, object], root: Path) -> str:
    name = plugin["name"]
    parts = [GENERATED_NOTE, f"# {name}", str(plugin.get("long", plugin["description"]))]
    skills = skills_of(plugin, root)
    if skills:
        rows = "\n".join(
            f"| [`{s['name']}`](skills/{s['dir']}/README.md) | {s['description']} |"
            for s in skills
        )
        parts.append(f"## Skills\n\n| Skill | What it does |\n|---|---|\n{rows}")
    if plugin.get("hooks"):
        harnesses = ", ".join(f"`{h}`" for h in plugin["hooks"])
        location = "" if "devin" in plugin["hooks"] else " under `hooks/`"
        parts.append(
            f"## Hooks\n\nShips hooks{location} for {harnesses}. "
            "Plugin installation wires them."
        )
    parts += [install_section(plugin, include_devin=True), source_section(f"plugins/{name}")]
    return "\n\n".join(parts) + "\n"


def skill_readme(plugin: dict[str, object], skill: dict[str, str]) -> str:
    path = f"plugins/{plugin['name']}/skills/{skill['dir']}"
    return "\n\n".join([
        GENERATED_NOTE,
        f"# {skill['name']}",
        skill["description"],
        f"Ships in the [`{plugin['name']}`](../../README.md) plugin of "
        f"[Uraxii/dotai]({REPOSITORY_URL}). The agent reads "
        "[SKILL.md](SKILL.md); this file is for people.",
        *([f"## Requirements\n\n{skill['compatibility']}"] if skill["compatibility"] else []),
        install_section(plugin),
        source_section(path),
    ]) + "\n"


def readme_files(root: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for plugin in PLUGINS:
        plugin_root = Path("plugins") / str(plugin["name"])
        if plugin["name"] not in HAND_WRITTEN_READMES:
            files[plugin_root / "README.md"] = plugin_readme(plugin, root)
        for skill in skills_of(plugin, root):
            files[plugin_root / "skills" / skill["dir"] / "README.md"] = skill_readme(plugin, skill)
    return files


def wanted_files(root: Path) -> dict[Path, str]:
    """Map every generated path to the exact text it should hold."""
    files: dict[Path, str] = {
        Path(".claude-plugin/marketplace.json"): render(claude_marketplace()),
        Path(".agents/plugins/marketplace.json"): render(agents_marketplace()),
        Path("README.md"): readme_with_plugin_table(root),
        **readme_files(root),
    }
    for plugin in PLUGINS:
        if plugin is PSTACK:
            continue
        plugin_root = Path("plugins") / str(plugin["name"])
        copilot = core_manifest(plugin)
        if "copilot" in plugin.get("agents", []):
            copilot["agents"] = "./agents/copilot/"
        if on_harness(plugin, "copilot"):
            if copilot_path := plugin.get("copilot_hook_path"):
                copilot["hooks"] = f"./{copilot_path}"
            elif "devin" in plugin.get("hooks", []):
                copilot["hooks"] = {}
            files[plugin_root / "plugin.json"] = render(copilot)
        files[plugin_root / ".claude-plugin/plugin.json"] = render(
            claude_manifest(plugin, root)
        )
        if "mcp_servers" in plugin:
            files[plugin_root / ".mcp.json"] = render(
                {"mcpServers": plugin["mcp_servers"]}
            )
        if on_harness(plugin, "codex"):
            files[plugin_root / ".codex-plugin/plugin.json"] = render(
                codex_manifest(plugin)
            )
        if "devin_manifest" in plugin:
            files[plugin_root / ".devin-plugin/plugin.json"] = render({
                "name": plugin["name"],
                "version": version_of(plugin),
                **plugin["devin_manifest"],
            })
        if sources := plugin.get("devin_rule_sources"):
            sections = []
            for source in sources:
                try:
                    text = (root / plugin_root / source).read_text()
                except FileNotFoundError:
                    continue
                sections.append("\n".join(line.rstrip() for line in text.splitlines()).strip())
            if sections:
                files[plugin_root / "AGENTS.md"] = "\n\n".join([GENERATED_NOTE, *sections]) + "\n"
    return files


def stale_manifests(root: Path) -> list[Path]:
    """Return manifests on disk for a harness the plugin opted out of."""
    stale = []
    for plugin in PLUGINS:
        plugin_root = Path("plugins") / str(plugin["name"])
        for harness, manifest in (
            ("codex", ".codex-plugin/plugin.json"),
            ("copilot", "plugin.json"),
        ):
            if not on_harness(plugin, harness) and (root / plugin_root / manifest).is_file():
                stale.append(plugin_root / manifest)
    return stale


def stale_devin_rules(root: Path, files: dict[Path, str]) -> list[Path]:
    stale = []
    marker = GENERATED_NOTE.encode("utf-8")
    for plugin in PLUGINS:
        if not plugin.get("devin_rule_sources"):
            continue
        relative = Path("plugins") / str(plugin["name"]) / "AGENTS.md"
        rule = root / relative
        if relative in files or rule.is_symlink() or not rule.is_file():
            continue
        with rule.open("rb") as stream:
            if stream.read(len(marker)) == marker:
                stale.append(relative)
    return stale


def missing_hook_wiring(root: Path) -> list[Path]:
    """Return declared hook wiring paths that are absent from `root`."""
    missing = []
    for plugin in PLUGINS:
        plugin_root = Path("plugins") / str(plugin["name"])
        for harness in plugin.get("hooks", []):
            wiring = plugin_root / hook_wiring_paths(plugin)[str(harness)]
            if not (root / wiring).is_file():
                missing.append(wiring)
    return missing


def undeclared_hook_wiring(root: Path) -> list[Path]:
    """Return hook wiring paths on disk that their plugin does not declare."""
    undeclared = []
    for plugin in PLUGINS:
        if plugin is PSTACK:
            continue
        plugin_root = Path("plugins") / str(plugin["name"])
        declared_harnesses = plugin.get("hooks", [])
        for harness, relative_path in hook_wiring_paths(plugin).items():
            wiring = plugin_root / relative_path
            if (root / wiring).is_file() and harness not in declared_harnesses:
                undeclared.append(wiring)
    return undeclared


RELEASE_REFS = ("origin/main", "main")


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=root, capture_output=True, text=True
        )
    except FileNotFoundError:  # no git: behave as outside a repository
        return subprocess.CompletedProcess(["git"], 128, "", "")


def unversioned_skills(root: Path) -> list[str]:
    """Name each skill with no `metadata.version`, or that changed since the
    last release (the main branch) without a new one.

    Skills carry their own semver, separate from the plugin's. With no main
    branch to compare with (a copy of the tree, a shallow clone), only the
    missing-version part runs.
    """
    base = next(
        (ref for ref in RELEASE_REFS
         if git(root, "rev-parse", "--verify", "--quiet", ref).returncode == 0),
        None,
    )
    problems = []
    for skill_md in sorted((root / "plugins").glob("*/skills/*/SKILL.md")):
        relative = skill_md.relative_to(root)
        version = skill_frontmatter(skill_md.read_text(encoding="utf-8"), relative)["version"]
        if not version:
            problems.append(f"{relative}: add metadata.version (start at 1.0.0)")
            continue
        if base is None:
            continue
        released = git(root, "show", f"{base}:{relative.as_posix()}")
        if released.returncode != 0:
            continue  # new since the release
        unchanged = git(
            root, "diff", "--quiet", base, "--", str(relative.parent),
            f":(exclude){relative.parent.as_posix()}/README.md",
        )
        if unchanged.returncode == 0:
            continue
        if skill_frontmatter(released.stdout, relative)["version"] == version:
            problems.append(
                f"{relative}: changed since {base} but metadata.version is "
                f"still {version}; bump it"
            )
    return problems


def render(document: dict[str, object]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def drifted(files: dict[Path, str], root: Path) -> list[Path]:
    changed = []
    for relative, text in sorted(files.items()):
        absolute = root / relative
        if not absolute.is_file() or absolute.read_text() != text:
            changed.append(relative)
    return changed


def write(files: dict[Path, str], root: Path) -> list[Path]:
    changed = drifted(files, root)
    for relative in changed:
        absolute = root / relative
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_text(files[relative])
    return changed


def main(arguments: list[str] | None = None, root: Path = REPOSITORY_ROOT) -> int:
    """Generate into `root`, which the tests point at a copy of the tree.

    The output root used to be the module constant, so calling this script
    at all rewrote the checkout it lives in. A test exercising write mode
    then overwrote whatever the person running it had not committed yet.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 2 if regenerating would change a file, and name the files",
    )
    options = parser.parse_args(arguments)
    files = wanted_files(root)
    stale_rules = stale_devin_rules(root, files)

    if options.check:
        changed = drifted(files, root)
        missing_wiring = missing_hook_wiring(root)
        undeclared_wiring = undeclared_hook_wiring(root)
        stale = stale_manifests(root)
        versions = unversioned_skills(root)
        if not (changed or missing_wiring or undeclared_wiring or stale or stale_rules or versions):
            print(f"{len(files)} generated files are up to date.")
            return 0
        if changed:
            print("These generated files do not match generate-plugin-manifests.py:")
            for relative in changed:
                print(f"  {relative}")
            print("Edit PLUGINS in the generator and rerun it, never the file itself.")
        if missing_wiring:
            print("These declared plugin hook wiring files are missing:")
            for relative in missing_wiring:
                print(f"  {relative}")
        if undeclared_wiring:
            print("These plugin hook wiring files are undeclared:")
            for relative in undeclared_wiring:
                print(f"  {relative}")
        if stale:
            print("These manifests are for a harness the plugin opted out of; delete them:")
            for relative in stale:
                print(f"  {relative}")
        if stale_rules:
            print("These generated Devin rules have no instruction sources; regenerate to remove them:")
            for relative in stale_rules:
                print(f"  {relative}")
        if versions:
            print("These skills need a metadata.version change:")
            for problem in versions:
                print(f"  {problem}")
        return 2

    changed = write(files, root)
    for relative in changed:
        print(f"wrote {relative}")
    for relative in stale_rules:
        (root / relative).unlink()
        print(f"removed {relative}")
    print(f"{len(files)} generated files, {len(changed)} rewritten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
