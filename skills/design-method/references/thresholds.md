# Thresholds

The accessibility floors every page clears before it ships, whatever the brief
says. A page that misses one of these is wrong, not merely unfashionable.

| Thing | Floor |
|---|---|
| Body text contrast | 4.5:1 |
| Large text, control edges, icons, focus rings | 3:1 |
| Body size | 16px, and never under 14px |
| Tap target | 44 by 44px |
| Control height, inputs and the buttons beside them | one shared 44px |

24 by 24px is the WCAG 2.2 floor for a tap target. 44 is platform guidance,
not law, and it is the number to build to.

Never rely on colour alone to carry a state or a meaning.

Check contrast in OKLCH, and read how padding counts toward a tap target, in
references/color.md.
