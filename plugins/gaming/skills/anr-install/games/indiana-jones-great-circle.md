# Indiana Jones and the Great Circle

- **Store and version:** any.
- **Renderer:** Vulkan, unverified.
- **Exe folder:** the folder with the game's main `.exe`. Check on the user's install.
- **Proxy:** `winmm.dll` is the usual choice for a Vulkan game. The OptiScaler wiki also lists `dxgi.dll` and `OptiScaler.asi`. Pass the proxy name to the installer.
- **DLSS-G in game:** probably. The OptiScaler wiki lists the Nukem's path as working, but Nukem's can also run in games with only DLSS upscaling, so this is weak evidence.

## Spoof recipe

Tier 1V on non-RTX-40/50 GPUs (tier 1 plus `Vulkan=true` and `VulkanExtensionSpoofing=true`), untested with ANR. The [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Indiana-Jones-and-the-Great-Circle) (reported, RX 6950 XT, RX 9070 XT, RTX 5070 Ti, OptiScaler 0.9) notes no spoof problems.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- Stutter with Nukem's FG. The wiki fix is to set Reflex to force disabled in the OptiScaler overlay (reported).
- An older wiki entry (OptiScaler 0.7, NVIDIA) says the overlay menu was invisible and DLSS was off in the menu. Newer entries do not repeat it.
