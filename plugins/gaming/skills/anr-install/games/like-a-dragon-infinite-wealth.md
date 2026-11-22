# Like a Dragon: Infinite Wealth

- **Store and version:** Steam (reported, on Linux with Proton).
- **Renderer:** D3D12.
- **Exe folder:** confirm on disk. Use the folder of the largest game `.exe`.
- **Proxy:** `dxgi.dll`. Proton launch option `WINEDLLOVERRIDES="dxgi=n,b" %command%`.
- **DLSS-G in game:** yes.

## Spoof recipe

Tier 0 was enough on an RTX 3080 under Proton ([apex-compute/ANR#46](https://github.com/apex-compute/ANR/issues/46)). Use tier 1 on Windows if the option is greyed out.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|
| 2026-11 | RTX 3080 | Linux, GE-Proton11-12 | V.B15 | 0 | ANR FG 3X ran. Full system freeze (Xid 109) after 10 min to 1 h 45 min | reported | [apex-compute/ANR#46](https://github.com/apex-compute/ANR/issues/46) |

## Known problems

- System freeze with a GPU MMU fault under Proton ([apex-compute/ANR#46](https://github.com/apex-compute/ANR/issues/46), open). The log showed the `ampere` path with cooperative matrix off in vkd3d-proton.
