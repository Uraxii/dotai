# Hogwarts Legacy

- **Store and version:** any.
- **Renderer:** D3D12, unverified.
- **Exe folder:** usually `Phoenix/Binaries/Win64`. This comes from the engine layout, so confirm it on disk.
- **Proxy:** `dxgi.dll` (OptiScaler wiki).
- **DLSS-G in game:** yes. The OptiScaler wiki lists "DLSSG via Streamline" inputs.

## Spoof recipe

Tier 1 on non-RTX-40/50 GPUs. The [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Hogwarts-Legacy) (reported, RX 7900 XT, OptiScaler 0.9) says OptiPatcher unlocks DLSS-G without spoofing (steps in SKILL.md step 4, untested with ANR). Try it if tier 1 fails.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- Crash at startup. The wiki fix is `DisableOverlays=true` in `OptiScaler.ini`, which blocks the Epic overlay (reported). Each reinstall resets that key.
