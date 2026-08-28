---
name: excalidraw-diagrams
description: House standard for drawing diagrams through the claude.ai Excalidraw MCP connector, 4:3 camera sizes, font and element sizing, spacing, color palette, contrast, drawing order, dark mode. ALSO covers embedding diagrams in an Obsidian vault (.excalidraw.md), which has extra hard constraints (8-char ids, static geometry, headless verify). Use when creating or editing an Excalidraw diagram, or when asked for a flowchart, architecture diagram, sequence diagram, state chart, or any visual drawn via create_view or embedded in Obsidian. Load before drawing so the output follows the sizing/spacing/color conventions.
---

# Excalidraw diagrams

Diagrams draw via the Excalidraw MCP connector, rendered inline at ~700px wide. Design for that constraint.

## First steps

1. Call `mcp__claude_ai_Excalidraw__read_me` once per conversation, source of truth for the element JSON shape (rectangles, arrows, labels, camera, delete, checkpoints, animation).
2. Draw with `mcp__claude_ai_Excalidraw__create_view` following the house standards below. A project's own documented diagram standard wins over these.

## Obsidian-embedded diagrams (.excalidraw.md)

The MCP connector is a LIVE renderer; the Obsidian plugin is STATIC. These rules apply only when the diagram must live in an Obsidian vault; breaking any of them corrupts the file.

- Element ids MUST be exactly 8 alphanumeric chars, use `sha1(name)[:8]`. Obsidian's `## Text Elements` parser only matches 8-char anchors (`/\s\^(.{8})[\n]+/`) and regenerates any other length; a mismatch means the next open+autosave dumps the raw `## Text Elements` block into the shapes and duplicates entries. Never open a non-conforming file in Obsidian to "check" it, that open+autosave is what corrupts it; verify headlessly instead (below).
- Bake FINAL static geometry. MCP snaps arrows to edges and auto-fits text live; Obsidian draws stored points verbatim and never recomputes (`read_checkpoint` returns raw authored points, not snapped ones). Arrow endpoints must physically terminate on target box edges; boxes must already fit their text.
- `## Text Elements` must be symmetric with the JSON: every text element has one `^id` anchor, anchor-set == text-id-set, no duplicates. Bound labels are separate text elements with `containerId` plus the container's `boundElements` back-ref. Collapse `\n{2,}` to `\n` inside labels.
- Prefer a generator that emits static geometry over the MCP-to-plugin round trip, which copies non-static geometry and corrupts easily. Author with code that computes edge-accurate arrows, text-fit boxes, and 8-char ids.
- Verify headless, never on the user's screen. Extract the json Drawing block to `scene.excalidraw`, run `npx excalidraw-brute-export-cli -i scene.excalidraw -o out.png -f png -b true -s 2` (headless Chromium, same engine/font as Obsidian), then Read the PNG. No node/Chromium on the host: run it in a container (distrobox/toolbox). Drive the user's live Obsidian GUI only with explicit consent, never by default (`obsidian://` / `notesmd-cli open` autosave corrupts a non-conforming file).

Layout: decision trees fan OUT with generous gaps, branches diverge outward. Branch arrows land on the box TOP (arrowhead into top-center). Edge condition labels (YES/NO) are bound arrow labels on the line, not floating text.

## Camera (4:3 only)

Emit `cameraUpdate` as the first element, before the content it frames. Non-4:3 distorts, never use another ratio. Leave padding, don't match camera size to content size. Use several cameras to pan/zoom and guide attention.

| Cam | Size | Use | Min font |
|-----|------|-----|----------|
| S | 400x300 | close-up, 2-3 elements | 16 |
| M | 600x450 | one section | 16 |
| L | 800x600 | standard full diagram (default) | 16 |
| XL | 1200x900 | large overview | 18 |
| XXL | 1600x1200 | panorama / final overview | 21 |

## Fonts and sizing

Body/labels min fontSize 16, titles/headings min 20, secondary annotations min 14 (honor the per-camera minimums above). Min shape size 120x60 for labeled rectangles/ellipses, min 20-30px gaps between elements. Prefer fewer, larger elements, and labeled shapes (`"label": {"text": ...}`) over separate text elements (auto-centers, auto-resizes, saves tokens). Check y-coordinates so boxes, labels, and text don't overlap.

## Colors

### Primary (strokes, data series)
| Name | Hex | Use |
|------|-----|-----|
| Blue | `#4a9eed` | Primary actions, links, series 1 |
| Amber | `#f59e0b` | Warnings, highlights, series 2 |
| Green | `#22c55e` | Success, positive, series 3 |
| Red | `#ef4444` | Errors, negative, series 4 |
| Purple | `#8b5cf6` | Accents, special, series 5 |
| Pink | `#ec4899` | Decorative, series 6 |
| Cyan | `#06b6d4` | Info, secondary, series 7 |
| Lime | `#84cc16` | Extra, series 8 |

### Pastel fills (shape backgrounds)
| Color | Hex | Good for |
|-------|-----|----------|
| Light Blue | `#a5d8ff` | Input, sources, primary nodes |
| Light Green | `#b2f2bb` | Success, output, completed |
| Light Orange | `#ffd8a8` | Warning, pending, external |
| Light Purple | `#d0bfff` | Processing, middleware, special |
| Light Red | `#ffc9c9` | Error, critical, alerts |
| Light Yellow | `#fff3bf` | Notes, decisions, planning |
| Light Teal | `#c3fae8` | Storage, data, memory |
| Light Pink | `#eebefa` | Analytics, metrics |

### Background zones (use `opacity: 30`)
| Color | Hex | Good for |
|-------|-----|----------|
| Blue zone | `#dbe4ff` | UI / frontend layer |
| Purple zone | `#e5dbff` | Logic / agent layer |
| Green zone | `#d3f9d8` | Data / tool layer |

## Contrast (critical)

- Text on white: never light gray, minimum text color `#757575`. White text needs a dark background.
- Colored text on light fills: use dark variants (`#15803d` not `#22c55e`, `#2563eb` not `#4a9eed`).
- No emoji in text, they don't render in Excalidraw's font.

## Drawing order

Array order is z-order (first = back, last = front). Emit progressively: background zone -> shape -> its label -> its arrows -> next shape, not all-shapes-then-all-text. Draw decorative art/icons LAST.

## Dark mode (only if asked)

First element (before `cameraUpdate`) is a huge dark bg rectangle (~10x camera, e.g. 10000x7500) at `#1e1e2e`. Then: text `#e5e5e5` primary / `#a0a0a0` muted; fills `#1e3a5f` blue, `#1a4d2e` green, `#2d1b69` purple, `#5c3d1a` orange, `#5c1a1a` red, `#1a4d4d` teal; primary palette colors for strokes/arrows.
