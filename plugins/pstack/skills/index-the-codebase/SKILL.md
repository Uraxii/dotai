---
name: index-the-codebase
description: "Indexes a codebase or a git worktree with an available code indexer, such as codebase-memory or graphify, and queries the index before grep or file reads. Use before work in any checkout or worktree, and for 'where is X', 'who calls X', or 'what breaks if I change X'. Every agent and subagent that works in a checkout runs it first."
---

# Index the codebase

Run this skill before you work in a checkout. A git worktree is a separate checkout. A subagent that works in a checkout runs this skill too.

## Steps

1. Find a code indexer. Look for an indexer tool, skill, MCP server, or CLI in this session, for example codebase-memory (`codebase-memory-mcp`) or graphify. A read-only agent can lack the tools that an MCP server gives. If no indexer is available, say so once and use grep and file reads. Stop here.
2. Get the root of the checkout you work in (`git rev-parse --show-toplevel`). An index belongs to one root. An index of the main checkout does not cover a worktree of it.
3. Get the indexer's list of indexed roots. Compare each root with the root from step 2.
4. Index the root if one of these conditions is true:
   - No indexed root is the same as the root from step 2.
   - The indexer does not tell you when it last indexed the root.
   - HEAD moved after the last index. A pull, a branch switch, and a commit each move HEAD. `git log -g -1 --date=iso --format=%gd` shows when HEAD last moved. If it prints nothing, index the root.
   - A file that `git status --porcelain` lists changed after the last index. A deleted file counts as changed.
5. Query the index first for these questions:
   - Where is X defined or used?
   - Who calls X?
   - What breaks if X changes?

   Read a file to confirm a result from the index, or when the index has no answer. Use grep for literal strings, such as an error message, a config key, or text in a prose file.
6. After you change files, index the root again before your next index query.

The skill stays in effect until your task ends. Step 6 applies after each change.

## Subagent briefs

An agent that loads poteto-mode gets this rule from the poteto-mode trigger list. Do not add the rule to its prompt.

When you spawn an agent that does not load poteto-mode and works in a checkout, put the checkout path in the brief. Tell the agent to run the **index-the-codebase** skill on that path before any other work. If the agent is read-only, tell it to use file search and file reads when it cannot reach an indexer.
