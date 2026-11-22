# Marvel's Spider-Man 2

- **Store and version:** any.
- **Renderer:** D3D12.
- **Exe folder:** the folder with the game's main `.exe`.
- **Proxy:** `dxgi.dll` (OptiScaler wiki).
- **DLSS-G in game:** yes. The OptiScaler wiki lists "DLSSG via SL" inputs. Turn DLSS frame generation on in the game's options, or the game sends no HUD-less image.

## Spoof recipe

Tier 1 on NVIDIA. On AMD and Intel, the [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Marvels-Spider‐Man-2) (reported, RX 9070 XT, OptiScaler 0.9) says ray tracing plus spoofing crashes the game at start. Turn off ray tracing, or use `Dxgi=false`. The wiki says OptiScaler 0.9 and later turns off `Dxgi` spoofing for this game by itself, so `Dxgi=true` in the ini may have no effect.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- AMD/Intel crash at start with ray tracing and spoofing (wiki, reported).
