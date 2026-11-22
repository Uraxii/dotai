# Cyberpunk 2077

- **Store and version:** any. The issues do not name a store.
- **Renderer:** D3D12.
- **Exe folder:** usually `bin/x64` (`Cyberpunk2077.exe`). Unverified, so confirm it on disk.
- **Proxy:** `dxgi.dll`, or `wininet.dll` (both listed by the OptiScaler wiki). Check for ReShade or other mods that use `dxgi.dll` first.
- **DLSS-G in game:** yes (OptiScaler wiki). The menu location is unverified.

## Spoof recipe

The ANR issues name no GPU or spoof settings. The OptiScaler wiki page ([Cyberpunk 2077](https://github.com/optiscaler/OptiScaler/wiki/Cyberpunk-2077), reported, RX 9070 XT, OptiScaler 0.9.3) lists "DLSSG via Streamline" inputs, so the game offers DLSS-G. Use tier 1 on non-RTX-40/50 GPUs and record the result.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|
| 2026-11 | unknown | unknown | beta | unknown | FG ran, with a black rectangle artifact and UI jitter on fast camera moves | reported | [apex-compute/ANR#8](https://github.com/apex-compute/ANR/issues/8) (closed) |
| 2026-11 | unknown | unknown | beta | unknown | FG ran, with severe UI jitter | reported | [apex-compute/ANR#87](https://github.com/apex-compute/ANR/issues/87) (open) |

## Known problems

- UI and HUD jitter. [apex-compute/ANR#87](https://github.com/apex-compute/ANR/issues/87) asks for an option to turn off UI composition (open).
