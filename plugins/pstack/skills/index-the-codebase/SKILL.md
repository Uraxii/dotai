---
name: index-the-codebase
description: "Index the code with the codebase-memory plugin before you work with it, then query the index before you grep or read files. Use before any question about where code lives, who calls what, or what a change breaks, and when you start work in a new checkout or worktree."
---

# Index the codebase

Before you work with code, index it with the codebase-memory plugin, through its `codebase-memory:cbm` skill. Then answer code questions from the index.

1. When you start work in a checkout or a worktree, make sure that the index for that directory exists and is current. Each worktree is a different directory and needs its own index.
2. Query the index before you grep or read files: where code lives, who calls what, what a change breaks, how modules connect, and dead code.
3. Use grep only for literal strings, such as an error message or a config key.
4. After you change many files, index again before you query the changed code.

The `codebase-memory:cbm` skill tells how to index and how to query. When the plugin is not installed, use another code indexer that the session has, for example `graphify`. When there is no indexer, search the files directly.
