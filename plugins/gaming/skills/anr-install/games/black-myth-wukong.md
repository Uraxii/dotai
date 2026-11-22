# Black Myth: Wukong

- **Store and version:** any.
- **Renderer:** D3D12, unverified.
- **Exe folder:** usually `b1/Binaries/Win64`. This comes from the engine layout, so confirm it on disk.
- **Proxy:** `dxgi.dll` or `winmm.dll` (OptiScaler wiki).
- **DLSS-G in game:** yes. The OptiScaler wiki lists "DLSSG via Streamline" inputs.

## Spoof recipe

Do not use tier 1 as written. The [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Black-Myth-Wukong) (reported, RX 9070 XT, OptiScaler 0.9) says spoofing causes blue texture corruption. It recommends OptiPatcher to unlock DLSS-G without spoofing (steps in SKILL.md step 4, untested with ANR). The other choice is `Dxgi=false` with `StreamlineSpoofing=true` and `SpoofHAGS=true`. On Linux, spoofing may need `dxvk.conf` changes (`https://github.com/optiscaler/OptiScaler/blob/master/Spoofing.md#linux`).

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- Blue texture corruption with `Dxgi=true` (OptiScaler wiki, reported).
