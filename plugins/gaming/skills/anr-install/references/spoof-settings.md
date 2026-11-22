# OptiScaler spoof settings used by ANR FG

From the comments in the `OptiScaler.ini` shipped in ANR FG V.B20 (Apex OptiScaler, upstream `d6b02459`). When the package version is newer than V.B20, grep the package's `game/OptiScaler.ini` for these keys and update this file before you rely on it.

## `[Spoofing]`

| Key | Default (`auto`) | Effect |
|---|---|---|
| `Dxgi` | true on AMD/Intel, false on NVIDIA | Spoofs the GPU through DXGI for the whole game. The game sees `SpoofedGPUName` |
| `StreamlineSpoofing` | true | Spoofs the GPU for Streamline only (NVIDIA's DLSS plugin, `sl.*.dll`), even when `Dxgi` is off |
| `SpoofHAGS` | "false, unless DLSSG mod is enabled". It is not known whether ANR counts as that mod, so set it explicitly | Reports hardware-accelerated GPU scheduling as on. DLSS-G requires HAGS |
| `SpoofedVendorId` / `SpoofedDeviceId` / `SpoofedGPUName` | `0x10de` / `0x2684` / NVIDIA GeForce RTX 4090 | What the game sees |
| `Vulkan`, `VulkanExtensionSpoofing` | false | The same spoofing for Vulkan games |
| `DxgiBlacklist` | off | Skips spoofing for named callers. Does not work on Linux |
| `Registry` | see ini | Spoofs IDs and the driver version in the registry |

## `[fakenvapi]` and `[Libraries]` (tier 2, AMD and Intel only)

- `UseFakenvapi` (`[fakenvapi]`) defaults to true: "Use fakenvapi when nvapi64.dll is missing". The ini adds that it is "Sometimes also required for DLSS/DLSSG to show up".
- `NvapiPath` (`[Libraries]`) defaults to `auto` and takes "nvapi64.dll or fakenvapi.dll". Leave it at `auto` when `fakenvapi.dll` is next to OptiScaler.

## `[FrameGen]` (do not change for ANR)

- `FGInput=nvngxfg` catches the game's DLSS-G (NGX) frame generation. It is the only input this package routes to ANR. The ini also documents `FGOutput=dlssg` with the replacement (it needs Streamline DLLs in `OptiScaler/streamline`), but nobody has tested that with ANR. FSR FG and XeFG inputs are not routed to ANR in the package ([apex-compute/ANR#82](https://github.com/apex-compute/ANR/issues/82) asks for that).
- `FGOutput=auto`.
- `FGNvngxReplacement=Apex Neural Rendering FG` names the folder under `OptiScaler/custom/` that holds ANR's `dlssg/nvngx_dlssg.dll`.

## ANR's own settings

These are in `OptiScaler/custom/Apex Neural Rendering FG/dlssg/nr_fg.ini`. A reinstall keeps them.

- `path` sets the compute path (`auto`, `coopmat`, `packed`, `dp4a`, `portable`, `portable-linalg`, `portable-xmx`).
- `max_generated` sets the generated frames per real frame (5 means up to 6X).
- `scene_cut` stops interpolation across a camera cut.
- `nits_per_unit` sets the HDR10 scale.
