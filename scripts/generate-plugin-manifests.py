#!/usr/bin/env python3
"""Generate every plugin manifest and both marketplace files from one list.

Every plugin in the repository needs a `plugin.json`, a
`.claude-plugin/plugin.json`, and a `.codex-plugin/plugin.json`, and each
must appear in `.claude-plugin/marketplace.json`, in
`.agents/plugins/marketplace.json`, and in the plugin table in `README.md`.
That is three manifests, two marketplace entries, and one table row per
plugin, whose names, versions, and descriptions all have to agree.

Edit PLUGINS below and rerun this script. Never hand-edit a generated
file: `--check` exits 2 when one has drifted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/Uraxii/dotai"
AUTHOR = {"name": "Uraxii", "url": "https://github.com/Uraxii"}
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MARKETPLACE_DESCRIPTION = (
    "Skills and thin named agents for software development work."
)

# The version a plugin gets when its entry below carries no explicit one.
FIRST_RELEASE = "1.0.0"

PLUGIN_TABLE_START = "<!-- dotai:plugins:start -->"
PLUGIN_TABLE_END = "<!-- dotai:plugins:end -->"
HOOK_WIRING_PATHS = {
    "claude": Path("hooks/hooks.json"),
    "codex": Path("hooks/codex-hooks.json"),
    "copilot": Path("hooks.json"),
}

PLUGINS: list[dict[str, object]] = [
    {
        "name": "pstack",
        "version": "1.1.1",
        "hooks": ["claude", "codex", "copilot"],
        "description": (
            "Skills and thin named agents: poteto-mode, principles, "
            "playbooks, tools."
        ),
        "short": "Reusable skills for software development work.",
        "long": (
            "A collection of reusable workflows, principles, playbooks, and "
            "tools for Codex and other coding agents."
        ),
        "keywords": ["software-development"],
        "prompts": [
            "Show me which pstack skills can help with this task.",
            "Use poteto-mode to work through this task.",
            "Set up pstack for this Codex environment.",
        ],
    },
    {
        "name": "artifact",
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
        "name": "mpocock",
        "version": "1.1.0",
        "description": (
            "Compact a conversation into a handoff document another agent "
            "can pick the work up from."
        ),
        "short": "Session handoff documents.",
        "long": (
            "Writes down what a session established, what it decided, and "
            "what is still open, in a form a fresh agent reads instead of "
            "the transcript. Use it before context runs out, before handing "
            "a long pipeline to a successor, or when another session "
            "continues the work."
        ),
        "keywords": ["handoff", "context"],
        "prompts": [
            "Write a handoff document for this session.",
            "Compact what we have done so another agent can continue.",
        ],
    },
    {
        "name": "skills",
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
        "name": "bd",
        "description": (
            "Track, create, claim, and close repo issues with the bd (beads) "
            "tool, including dependency links."
        ),
        "short": "Issue tracking with bd (beads).",
        "long": (
            "Runs the bd command line issue tracker against a repository: "
            "list what is ready to pick up, create and claim and close "
            "issues, and record which issue blocks which. Use it to answer "
            "what to work on next from the repository's own issue graph."
        ),
        "keywords": ["issue-tracking", "beads"],
        "prompts": [
            "What can I pick up next?",
            "Create a bd issue for this and block it on the current one.",
        ],
    },
    {
        "name": "cbm",
        "version": "1.0.1",
        "description": (
            "Query the codebase-memory code graph from a shell: callers, "
            "dependencies, impact, dead code, and ADRs."
        ),
        "short": "Shell queries over the codebase-memory code graph.",
        "long": (
            "Runs codebase-memory-mcp cli against an indexed repository with "
            "no MCP server involved, so a shell script or an agent without "
            "the MCP tools can still ask structural questions: who calls a "
            "function, how a change propagates, which modules cluster "
            "together, which functions have no callers, and what a symbol's "
            "source says."
        ),
        "keywords": ["code-intelligence", "static-analysis"],
        "prompts": [
            "Who calls this function?",
            "What breaks if I change this symbol?",
        ],
    },
    {
        "name": "caveman",
        "version": "1.0.0",
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
        "name": "steer",
        "version": "1.2.0",
        "hooks": ["claude"],
        "skills": False,
        "description": (
            "Harness hooks that steer agent behaviour, independent of any skill."
        ),
        "short": "Harness hooks independent of skills.",
        "long": (
            "Installs harness hooks that steer agent behaviour without being "
            "coupled to a skill."
        ),
        "keywords": ["harness", "hooks"],
        "prompts": [
            "Install the steer harness hooks.",
        ],
    },
]


def version_of(plugin: dict[str, object]) -> str:
    return str(plugin.get("version", FIRST_RELEASE))


def core_manifest(plugin: dict[str, object]) -> dict[str, object]:
    return {
        "name": plugin["name"],
        "version": version_of(plugin),
        "description": plugin["description"],
        "author": AUTHOR,
    }


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


def wanted_files(root: Path) -> dict[Path, str]:
    """Map every generated path to the exact text it should hold."""
    files: dict[Path, str] = {
        Path(".claude-plugin/marketplace.json"): render(claude_marketplace()),
        Path(".agents/plugins/marketplace.json"): render(agents_marketplace()),
        Path("README.md"): readme_with_plugin_table(root),
    }
    for plugin in PLUGINS:
        plugin_root = Path("plugins") / str(plugin["name"])
        files[plugin_root / "plugin.json"] = render(
            {"$schema": PLUGIN_SCHEMA, **core_manifest(plugin)}
        )
        files[plugin_root / ".claude-plugin/plugin.json"] = render(
            core_manifest(plugin)
        )
        files[plugin_root / ".codex-plugin/plugin.json"] = render(
            codex_manifest(plugin)
        )
    return files


def missing_hook_wiring(root: Path) -> list[Path]:
    """Return declared hook wiring paths that are absent from `root`."""
    missing = []
    for plugin in PLUGINS:
        plugin_root = Path("plugins") / str(plugin["name"])
        for harness in plugin.get("hooks", []):
            wiring = plugin_root / HOOK_WIRING_PATHS[str(harness)]
            if not (root / wiring).is_file():
                missing.append(wiring)
    return missing


def undeclared_hook_wiring(root: Path) -> list[Path]:
    """Return hook wiring paths on disk that their plugin does not declare."""
    undeclared = []
    for plugin in PLUGINS:
        plugin_root = Path("plugins") / str(plugin["name"])
        declared_harnesses = plugin.get("hooks", [])
        for harness, relative_path in HOOK_WIRING_PATHS.items():
            wiring = plugin_root / relative_path
            if (root / wiring).is_file() and harness not in declared_harnesses:
                undeclared.append(wiring)
    return undeclared


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

    if options.check:
        changed = drifted(files, root)
        missing_wiring = missing_hook_wiring(root)
        undeclared_wiring = undeclared_hook_wiring(root)
        if not changed and not missing_wiring and not undeclared_wiring:
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
        return 2

    changed = write(files, root)
    for relative in changed:
        print(f"wrote {relative}")
    print(f"{len(files)} generated files, {len(changed)} rewritten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
