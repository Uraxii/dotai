# S.T.A.L.K.E.R. 2: Heart of Chornobyl

- **Store and version:** any.
- **Renderer:** D3D12, unverified.
- **Exe folder:** usually `Stalker2/Binaries/Win64`. This comes from the engine layout, so confirm it on disk.
- **Proxy:** `dxgi.dll` or `winmm.dll` (OptiScaler wiki).
- **DLSS-G in game:** yes. The OptiScaler wiki lists "DLSSG via Streamline" inputs.

## Spoof recipe

Tier 1 on NVIDIA and AMD. The wiki tested AMD only, so NVIDIA is untested. On Intel Arc, the [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/S.T.A.L.K.E.R.-2-Heart-of-Chornobyl) (reported, OptiScaler 0.9) says spoofing gives rainbow color artifacts. Use `Dxgi=false` there.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- Ghosting ([apex-compute/ANR#17](https://github.com/apex-compute/ANR/issues/17)). Known from the issue title only.
