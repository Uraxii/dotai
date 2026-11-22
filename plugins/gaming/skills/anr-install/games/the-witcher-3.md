# The Witcher 3: Wild Hunt (Complete / next-gen)

- **Store and version:** Steam (installed, untested), GOG (no reports), Xbox/Game Pass (fails on AMD, below).
- **Renderer:** D3D12 for DLSS-G. Start the game in DirectX 12 mode (OptiScaler wiki).
- **Exe folder:** `bin/x64_dx12` (`witcher3.exe`), seen on one Steam install (2026-11-22). The game ships its own Streamline (`sl.interposer.dll`, `sl.dlss_g.dll`) and `nvngx_dlssg.dll` there, seen on the same install. Leave them alone.
- **Proxy:** `dxgi.dll`. That Steam install had no `dxgi.dll` there before ANR.
- **DLSS-G in game:** yes. The menu location is unverified.

## Spoof recipe

The OptiScaler wiki page ([The Witcher 3](https://github.com/optiscaler/OptiScaler/wiki/The-Witcher-3-Wild-Hunt), reported, AMD) says to run in DirectX 12 and install in `bin/x64_dx12`. The game still uses Streamline 1, so "DLSSG via SL" inputs are not supported. The page lists "FSR FG via Nukems" as working. ANR plugs into the same OptiScaler DLSS-G replacement setting as Nukem's, so this suggests ANR can work here too. That is an inference, not a test.

Tier 1 (`Dxgi=true`, `StreamlineSpoofing=true`, `SpoofHAGS=true`). Do not turn on real HAGS. On AMD it crashed the game with 0xc0000005 ([apex-compute/ANR#15](https://github.com/apex-compute/ANR/issues/15)).

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|
| 2026-11-22 | NVIDIA RTX 30 series | Windows | V.B20 | 1 | Installed and spoofed. Not yet started | untested | one local install |
| 2026-11 | RX 6750 XT | Windows | V.B17, V.B19 | 2 (fakenvapi 1.4.1) | FG selectable, DLSSG state off, no generated frames | reported | [apex-compute/ANR#15](https://github.com/apex-compute/ANR/issues/15) (Game Pass build) |
| 2026-11 | AMD | Windows | V.B19 | 1, with and without `Dxgi` | FG on in game, overlay says to select DLSS FG, DLSSG state off | reported | [apex-compute/ANR#82](https://github.com/apex-compute/ANR/issues/82) (Game Pass build) |

## Known problems

- Game Pass build on AMD: DLSS-G never turns on, so ANR gets no frames. The issue is open with no fix ([apex-compute/ANR#15](https://github.com/apex-compute/ANR/issues/15)). It is not known whether Steam or GOG on AMD behaves the same.
- Crash when changing regions ([apex-compute/ANR#86](https://github.com/apex-compute/ANR/issues/86), open). Known from the issue title only.
- "Witcher 3 Remastered crashes" ([apex-compute/ANR#33](https://github.com/apex-compute/ANR/issues/33), closed). Known from the issue title only.
