# DOOM: The Dark Ages

- **Store and version:** any.
- **Renderer:** Vulkan, unverified.
- **Exe folder:** the folder with the game's main `.exe`.
- **Proxy:** `winmm.dll` (OptiScaler wiki).
- **DLSS-G in game:** not recorded for any GPU. The wiki lists DLSS upscaling as NVIDIA-only. The [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Doom-The-Dark-Ages) (reported, RX 9070 XT, RTX 3070, OptiScaler 0.9.4) says spoofing cannot unlock DLSS-G on AMD or Intel because of extra checks, and that the Nukem's path does not work for all vendors.

## Spoof recipe

No known recipe on AMD or Intel. Tell those users that ANR will probably get no frames. On NVIDIA RTX 20/30 the result is untested. If they still want to try, use tier 1V and record the result.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|
| 2026-11 | unknown | unknown | unknown | unknown | No added smoothness | reported (issue title only) | [apex-compute/ANR#62](https://github.com/apex-compute/ANR/issues/62) |

## Known problems

- Spoofing does not unlock DLSS-G on AMD or Intel (wiki, reported). This may match [apex-compute/ANR#62](https://github.com/apex-compute/ANR/issues/62).
