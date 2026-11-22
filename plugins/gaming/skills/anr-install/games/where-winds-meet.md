# Where Winds Meet

- **Store and version:** unknown.
- **Renderer:** D3D12 (assumed, because the game offers DLSS-G).
- **Exe folder:** confirm on disk.
- **Proxy:** `dxgi.dll`.
- **DLSS-G in game:** the option exists, but the game does not turn DLSS-G on under ANR.

## Spoof recipe

None known to work. Tier 1 and tier 2 failed in the same way as The Witcher 3 Game Pass build. Tell the user before installing that it is expected to fail.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|
| 2026-11 | unknown | Windows | V.B19 | unknown | "Same issue": DLSSG state stays OFF | reported | comment on [apex-compute/ANR#82](https://github.com/apex-compute/ANR/issues/82) |

## Known problems

- ANR accepts only the game's DLSS-G input. [apex-compute/ANR#82](https://github.com/apex-compute/ANR/issues/82) asks for FSR FG input support (open).
