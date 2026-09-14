---
name: prototype
description: Build a throwaway prototype to answer one design question. Use when the user wants to sanity-check whether a state model or logic feels right, to explore what a UI should look like, or when about to ask the user a "which approach" question that running code could answer instead.
---

# Prototype

Throwaway code that answers ONE question. The question decides the shape.
Several competing candidates compared side by side is
`principle-exhaust-the-design-space` instead.

Pick the branch from the prompt, the surrounding code, or by asking; getting it
wrong wastes the whole prototype. Ambiguous and the user is away -> default by
surroundings (backend module -> logic, page -> UI) and say so at the top.

## Rules for both branches

1. **Throwaway from day one, and marked as such.** Put it next to the module or
   page it prototypes for, named so a casual reader sees it is not production.
   Follow the project's existing routing and task-runner conventions; invent no
   new top-level structure.
2. **One command to run.** Add it to the project's existing task runner. The
   user must start it without thinking.
3. **No persistence.** State lives in memory. Persistence is what the prototype
   is checking, not what it depends on. Question is specifically about
   persistence -> scratch DB or a file named "PROTOTYPE: wipe me".
4. **Skip the polish.** No tests, no abstractions, no error handling beyond
   what makes it runnable. No "what if we want X later".
5. **Surface the state.** After every action, or on every variant switch, show
   the full relevant state so the user sees what changed.
6. **Capture the answer, then delete the prototype.** The answer is the only
   thing worth keeping: record the verdict and the question it settled in an
   ADR, issue, or commit message, outside the prototype. A notes file beside it
   does not count, it keeps the prototype alive on main. Fold the validated
   decision into real code, commit the prototype to a throwaway branch off
   main, leave a pointer to that branch on the issue.

## Logic branch: "does this state model feel right?"

A tiny interactive terminal app the user drives by hand, for questions about
business logic, state transitions, or data shape: the kind of thing that looks
reasonable on paper and only feels wrong once pushed through real cases. Write
the state model and the question down first, at the top of the file.

**Isolate the logic in a portable module.** The bit answering the question sits
behind a small pure interface that could be lifted into the real codebase
later: a reducer `(state, action) => state`, an explicit state machine when
"which actions are even legal now" is part of the question, a set of pure
functions over a plain data type, or a module owning genuine internal state.
Pick by the question, not by what wires most easily to a TUI. Keep it pure: no
I/O, no terminal code, no logging for control flow. The TUI imports it; nothing
flows the other way. The TUI shell gets deleted, the module gets lifted.

**Build the smallest TUI that exposes the state.** Every tick, clear the screen
and re-render the whole frame, so the user sees one stable view instead of
growing scrollback. Each frame: current state one field per line (bold names,
dim derived values, native ANSI escapes are fine), then the keyboard shortcuts.
Read one keystroke, dispatch, re-render, loop until quit. Frame fits one
screen. Hand it over with the run command; the interesting moments are "wait,
that should not be possible", which are bugs in the idea.

## UI branch: "what should this look like?"

Several radically different variants on a single route, switchable from a
floating bottom bar. The user flips between them, picks one or steals bits from
each, and throws the rest away.

**Prefer variants inside an existing page.** Render them on the same route,
gated by a `?variant=` search param, keeping the existing data fetching, params
and auth so only the rendering swaps. Something with no page yet that would
naturally live inside one still goes here. Create a throwaway route only when
there is genuinely no page to live in: an empty route hides design problems a
populated one would expose.

**Default to 3 variants, cap at 5.** Beyond that they stop being radically
different. Variants must differ in layout, information hierarchy, and primary
affordance, not colour or copy. Two drafts coming out similar -> redo one with
an explicit "do not use a card grid" constraint. Share a `<Header>` if you
like, never a `<Layout>`; each variant must be free to throw the layout out.

**The switcher** is one shared component: left arrow, current variant key and
name, right arrow, all wrapping. Arrows update the URL search param through the
project's router so the variant is shareable and reload-stable. Left and right
keys cycle too, except while an input, textarea, or contenteditable has focus.
Visually distinct from the page, and gated off in production builds.

Wire variants to stubs, never to real mutations. When one wins, delete the
losers and the switcher, then rewrite the winner properly as you fold it in;
the variant code was written under prototype constraints.
