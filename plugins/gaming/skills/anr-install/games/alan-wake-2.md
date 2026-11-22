# Alan Wake II

- **Store and version:** any. The wiki's Epic overlay note applies to the Epic build.
- **Renderer:** D3D12.
- **Exe folder:** the folder with `AlanWake2.exe`. Check on the user's install.
- **Proxy:** `dxgi.dll` (OptiScaler wiki).
- **DLSS-G in game:** yes. The OptiScaler wiki lists "DLSSG via Streamline" inputs.

## Spoof recipe

Tier 1 on non-RTX-40/50 GPUs. The [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Alan-Wake-II) (reported, RX 9070 XT, OptiScaler 0.9) notes no spoof problems.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- The OptiScaler wiki says the Epic overlay can interfere. Use its first fix, `DisableOverlays=true` in `OptiScaler.ini` (reported). Each reinstall resets that key. Its other fix renames `EOSOverlayRenderer-Win64-Shipping.exe` and `EOSOverlayRenderer-Win32-Shipping.exe` in the Epic launcher's `Overlay` folder. Ask the user before you rename anything outside the game folder.
- The wiki says turning off lens distortion (`"m_bLensDistortion": false` in the game's `renderer.ini`) reduces ghosting.
