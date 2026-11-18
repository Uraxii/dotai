---
description: 'Sign in to OX Security - VibeSec again (one-time OAuth login in your browser)'
allowed-tools: Bash("${CLAUDE_PLUGIN_ROOT}/hooks/ox" --login-oauth), Bash("${CLAUDE_PLUGIN_ROOT}/hooks/ox" --login-oauth --force)
---

If the user typed anything after the command, do not run anything. Reply that OX never reads a token from the chat, and that an OX API token is set by re-running the VibeSec installer with --token. Then stop.

Otherwise use the Bash tool to run this command with a 10 minute timeout, and show its output verbatim:

"${CLAUDE_PLUGIN_ROOT}/hooks/ox" --login-oauth

If the output says the user is already signed in, ask whether to sign in again anyway (for example to switch organization or user). Only if the user says yes, use the Bash tool to run this command with a 10 minute timeout, and show its output verbatim:

"${CLAUDE_PLUGIN_ROOT}/hooks/ox" --login-oauth --force
