# itch-publish skill source

Imported from the `gamedev-skills/awesome-gamedev-agent-skills` repository on 2026-09-26.

- Source: https://github.com/gamedev-skills/awesome-gamedev-agent-skills/tree/44888f28ff918357ad82c4473352c60a1c5bde5b/skills/workflows/itch-publish
- Revision: `44888f28ff918357ad82c4473352c60a1c5bde5b`
- License: Apache-2.0, retained in [LICENSE.md](LICENSE.md).
- Upstream NOTICE: "awesome-gamedev-agent-skills. Copyright 2026 Abhishek Barali and the
  awesome-gamedev-agent-skills contributors."

The upstream language and examples are retained except for these changes,
checked against the butler manual and the itchio/butler source.

`SKILL.md`:

- The description also triggers on installing butler, `butler login`,
  `BUTLER_API_KEY`, and `butler status` or `fetch`.
- "When not to use" no longer names `steam-publish`, `game-jam`, or engine
  skills, which dotai does not ship. The "Related skills" section is removed
  for the same reason.
- Install step downloads from the permanent broth URL instead of the expiring
  itch.io page link, and says to keep the API key in Proton Pass.
- Patterns add `butler fetch` and `-i`.
- Pitfalls add that a command needing auth with no key starts an interactive
  login and hangs a non-interactive agent, that `BUTLER_API_KEY` wins over the
  creds file and `-i`, and that the page must exist before a push.

`references/butler-ci.md`:

- The auth section adds the `BUTLER_API_KEY` precedence and `-i`/`--identity`,
  and says to keep a non-CI key in Proton Pass.
- The install section notes that `broth.itch.ovh` no longer resolves.
- The flag table said `--auto-wrap` wraps a single loose file. It is a
  workaround for macOS `.app` bundles (itch#2147). It and `--fix-permissions`
  are on by default, so the table lists their `--no-` forms.
- The command table adds `butler fetch` and the `:channel` filter on
  `butler status`.

Both files carry a comment saying they were modified.
