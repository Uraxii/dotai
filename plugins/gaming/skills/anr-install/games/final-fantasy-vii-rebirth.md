# Final Fantasy VII Rebirth

- **Store and version:** Epic (reported). Steam is untested.
- **Renderer:** D3D12 (Unreal Engine).
- **Exe folder:** usually `End/Binaries/Win64`. This comes from the engine layout, so confirm it on disk.
- **Proxy:** `dxgi.dll`.
- **DLSS-G in game:** yes.

## Spoof recipe

Tier 0 was enough on an RTX 3070: "DLSS FG enabled in game" with the default package ([apex-compute/ANR#11](https://github.com/apex-compute/ANR/issues/11)). Use tier 1 if the option is greyed out.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|
| 2026-11 | RTX 3070 8 GB | Windows | V.B14 | 0 | FG ran. VRAM leak on FG re-creation at 4K, then about 4 fps and a crash | reported | [apex-compute/ANR#11](https://github.com/apex-compute/ANR/issues/11) |

## Known problems

- VRAM leak when the game re-creates frame generation (resolution changes). A maintainer released a fix and closed [apex-compute/ANR#11](https://github.com/apex-compute/ANR/issues/11). Use V.B15 or newer.
- 8 GB cards at 4K are tight. The package ships only `model_size = large`.
