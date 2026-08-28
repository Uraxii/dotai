---
name: clip-to-mobile
description: Convert a gameplay clip (animated WebP, AVI, or MP4) into a small, mobile-viewable video for sending to the user. Use whenever you are about to send/attach a recorded clip and the source is an animated WebP or an oversized MP4. Animated WebP and AVI do NOT render inline in mobile chat apps. Produces a small H.264 MP4 (default) or a GIF fallback with one command; no LLM-driven ffmpeg session needed.
---

Paths below are relative to this skill's directory (where this SKILL.md lives).

# clip-to-mobile

Turn a captured clip into something the user can actually watch in a mobile
chat client, cheaply and repeatably. One command, no per-send ffmpeg
reasoning.

## Format recommendation (what to send)

| Format | Inline on mobile? | Use |
|--------|-------------------|-----|
| MP4 (H.264 / yuv420p / +faststart) | Yes, universal | Default, send this |
| GIF (palette-optimized) | Yes (common image type) | Fallback if an MP4 preview fails to appear; ~9MB for 5s |
| Animated WebP | No | Never send, the format that started this |
| AVI | No | Source only (`/tmp/cap/`), never send |
| WebM / VP9 | Unreliable in chat/mobile | Avoid |

`+faststart` lets playback start before the file fully downloads. A ~20s 720p MP4 lands ~3-4MB, under the ~10MB comfort line; if a send feels heavy, trim with `--maxsec` or drop `--height`.

## Command

```bash
python3 ./convert.py <input.(webp|avi|mp4)> <output.mp4>
```

That is the whole default flow: animated-WebP (or AVI/big MP4) in, small
mobile MP4 out. It prints the output path, size, stream info, and PASS/FAIL.

### Options

- `--gif`: emit a palette-optimized GIF instead (fallback format).
- `--maxsec N`: trim to the first N seconds (long clips → smaller files).
- `--height H`: max output height in px (default 720 for MP4, 480 for GIF).
- `--crf N`: x264 quality/size knob (default 30; lower = bigger + sharper).
- `--fps N`: GIF framerate (default 15; ignored for MP4, which keeps source fps).

### Example

```bash
python3 ./convert.py capture.webp clip.mp4 --maxsec 20
```

## How it works / notes

- **Animated WebP:** ffmpeg cannot demux animated WebP, so the script extracts
  frames with PIL (inferring fps from per-frame durations, 30fps fallback) and
  re-encodes from a PNG sequence. AVI/MP4 inputs go straight through ffmpeg.
- **Validation:** MP4 output is probed with ffprobe (must be an H.264 stream);
  GIF output is opened with PIL. Size is checked against a 10MB comfort line.
  Over it still PASSes but prints a WARN suggesting `--maxsec`/`--height`/`--crf`.
- **Speed:** ~40s for a 470-frame 720p clip (frame extraction dominates); the
  encoder runs the `veryfast` x264 preset. Fully standalone, no model in the loop.
- **Dependencies:** ffmpeg + ffprobe + Pillow (all already installed).
