---
name: anr-install
description: Installs ANR FG (Apex Neural Rendering frame generation, github.com/apex-compute/ANR) into a PC game with OptiScaler, and spoofs the GPU so the game offers DLSS frame generation for ANR to replace. Keeps per-game spoof recipes and results. Use when the user asks to install, set up, update, spoof, troubleshoot or uninstall ANR FG in a game, or asks how to get DLSS frame gen on an RTX 20/30, GTX 16, AMD or Intel card for ANR.
metadata:
  version: 1.0.0
---

# Install ANR FG into a game

ANR FG replaces NVIDIA DLSS-G. OptiScaler loads into the game as `dxgi.dll` (or `winmm.dll` in Vulkan-only games) and sends the game's DLSS frame generation calls to ANR's `nvngx_dlssg.dll`. ANR runs only when the game itself turns DLSS frame generation on. On any GPU that is not an RTX 40 or 50, the game hides that option, so the GPU must be spoofed.

Per-game notes live in `games/`. Read `games/index.md` first. Read `references/spoof-settings.md` before you change a key that step 4 does not name, or before tier 2.

If the game has no file, read its OptiScaler wiki page (`https://github.com/optiscaler/OptiScaler/wiki/<Game-Title-With-Dashes>`, or clone `https://github.com/optiscaler/OptiScaler.wiki.git` and search it), search `https://github.com/apex-compute/ANR/issues?q=<game>`, and write a `games/` file before you install. A page that lists "DLSSG via Streamline" (or "via SL") means the game offers the DLSS-G that ANR needs. "Nukems" alone is weaker evidence, because Nukem's can also run in games that have only DLSS upscaling. A game with no DLSS frame generation cannot run ANR. Label what you copy from these pages **reported**, with the link.

**Done when** all of these are true: the installer printed `installed in <folder>`, step 5's checks pass, the user has been told how to confirm the result in the game, and the game's file in `games/` records this run.

## 1. Get the package

1. Find the newest FG release. List `https://api.github.com/repos/apex-compute/ANR/releases` and take the first tag that matches `FG-V.B*`. Other release kinds can be newer.
2. Ask the user where they keep ANR packages, and check there for an extracted `<tag>` package. If it is missing, ask before you download. Then download `anr-fg-<ver>-full.zip` and `SHA256SUMS.txt` into a new empty folder named `<tag>` in that place.
3. Compare the zip's SHA-256 with `SHA256SUMS.txt`. Stop if they differ.
4. Extract the zip next to it. Use `-addon.zip` only if the game already has an OptiScaler that the user installed.

## 2. Find the game folder

The target is the folder of the game's real `.exe`, not the launcher's. If you find more than one copy (two stores, or DX11 and DX12 exes), ask the user which one they play. Check the game's file in `games/` for the folder. Otherwise, look in Steam libraries (`steamapps/libraryfolders.vdf`), `GOG Games`, `XboxGames` and `Epic Games`. On Linux, the Steam root is `~/.steam/steam/`, `~/.local/share/Steam/` or, for Flatpak Steam, `~/.var/app/com.valvesoftware.Steam/.local/share/Steam/`. Heroic and Lutris keep games in the folders their settings name. For Unreal Engine games, the folder is usually `<Game>/Binaries/Win64`, on every OS.

Before you install, check these:
- The game is not running.
- Record any `dxgi.dll`, `winmm.dll`, `version.dll`, `OptiScaler.ini` or `OptiScaler/` that is already there. The installer backs up only the file with the proxy name it uses, and `OptiScaler.ini`. It refuses an `OptiScaler/` folder that it did not install, so use the addon package for that case.
- If a ReShade `dxgi.dll` is there, tell the user before you install. The installer replaces it without asking. It backs the file up and the uninstaller restores it, but ReShade is off while ANR is installed ([apex-compute/ANR#38](https://github.com/apex-compute/ANR/issues/38)).
- Find the GPU. On Windows, use `Get-CimInstance Win32_VideoController`. On Linux, use `lspci | grep -iE 'vga|3d'`.

## 3. Install

Use the installer for the OS the game runs on. A Proton game on Linux uses `install.sh`.

Windows. Pass the full path to `install.ps1`. Do not `cd` into the package.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<package>/install.ps1" "<game exe folder>"
```

Add a second argument (`dxgi.dll`, `winmm.dll` or `version.dll`) only if the game's file in `games/` says to. The installer warns if the Visual C++ 2015-2022 x64 runtime is missing. Without it, OptiScaler does not load.

Linux and Steam Deck: `sh install.sh "<folder>"`. Then set the Steam launch option it prints, `WINEDLLOVERRIDES="<proxy>=n,b" %command%`, where `<proxy>` is the proxy name without `.dll`. For Heroic or Lutris, set the same `WINEDLLOVERRIDES` value as an environment variable in the game's settings there. Do not set it on Windows. There is no macOS installer.

### Every install resets the spoof

Each installer run, including an update to a newer package, copies the package's `OptiScaler.ini` over the game's copy. Only `nr_fg.ini` is kept. After every install or update, re-apply the game's spoof tier (step 4).

## 4. Spoof

Edit `OptiScaler.ini` in the game folder. Apply the tier that the game's file names. If there is no file, start at tier 1 on any non-RTX-40/50 GPU.

| Tier | Settings | When |
|---|---|---|
| 0 | Package defaults (`StreamlineSpoofing` on, `Dxgi` off on NVIDIA, `SpoofHAGS` unclear for ANR, see references) | RTX 40/50, or a game whose file says the defaults work |
| 1 | `Dxgi=true`, `StreamlineSpoofing=true`, `SpoofHAGS=true` | Every other GPU. This is the default |
| 1V | Tier 1 plus `Vulkan=true` and `VulkanExtensionSpoofing=true` | Vulkan games (proxy usually `winmm.dll`). The package defaults both to false. Untested with ANR |
| 2 | Tier 1 plus fakenvapi | AMD or Intel only, when tier 1 does not show the option or the overlay's DLSSG state stays off. Never on NVIDIA |

The game's file and its OptiScaler wiki page override this table. Some games break with `Dxgi=true` (texture corruption, crashes). For those, set `Dxgi=false`, or use OptiPatcher to unlock DLSS-G without spoofing. Nobody has tested OptiPatcher with ANR, so tell the user that. OptiPatcher steps:
1. Ask before you download. Get `OptiPatcher.asi` from `https://github.com/optiscaler/OptiPatcher` releases.
2. Put it in `OptiScaler/plugins/` in the game exe folder, and set `LoadAsiPlugins=true` in `OptiScaler.ini`. Each reinstall resets that key, like the spoof keys.
3. Record it in the game's file. The uninstaller deletes the whole `OptiScaler/` folder, so it removes OptiPatcher too.

On Linux, spoofing can also need `dxvk.conf` changes (`https://github.com/optiscaler/OptiScaler/blob/master/Spoofing.md#linux`).

Tier 2 steps. The OptiScaler wiki says fakenvapi is only for AMD and Intel and must not be used on NVIDIA. Nobody has confirmed that tier 2 works with ANR, so tell the user that.
1. Ask before you download. fakenvapi is not in the package. Get the latest release from `https://github.com/FakeMichau/fakenvapi/releases/latest`. Check its checksum if the release has one.
2. Copy only `fakenvapi.dll` and `fakenvapi.ini` into the game exe folder, next to OptiScaler. `UseFakenvapi` already defaults to on.
3. Write the file names, fakenvapi version and folder in the game's file in `games/`. The uninstaller does not remove them, so delete them yourself when you uninstall.

Leave `[FrameGen]` alone. It must keep `FGInput=nvngxfg` and `FGNvngxReplacement=Apex Neural Rendering FG`. Leave `SpoofedDeviceId` at `auto` (RTX 4090).

Never turn on Windows hardware-accelerated GPU scheduling for the user. It is a system setting. `SpoofHAGS=true` covers it, and real HAGS crashed The Witcher 3 in [apex-compute/ANR#15](https://github.com/apex-compute/ANR/issues/15).

The file uses LF line endings and has no BOM. Edit only whole `key=value` lines, and keep the encoding. Linux shell:

```sh
sed -i -E 's/^Dxgi=.*/Dxgi=true/; s/^StreamlineSpoofing=.*/StreamlineSpoofing=true/; s/^SpoofHAGS=.*/SpoofHAGS=true/' "<game exe folder>/OptiScaler.ini"
```

Windows PowerShell:

```powershell
$p = "<game exe folder>/OptiScaler.ini"
$t = [IO.File]::ReadAllText($p)
foreach ($kv in "Dxgi=true", "StreamlineSpoofing=true", "SpoofHAGS=true") {
  $k = $kv.Split("=")[0]
  $t = [regex]::Replace($t, "(?m)^" + $k + "=[^\r\n]*", $kv)
}
[IO.File]::WriteAllText($p, $t)
```

## 5. Verify

1. Compare the game's `OptiScaler.ini` with the package's `game/OptiScaler.ini`. Only the spoof lines may differ.
2. Check that the proxy DLL exists in the game folder, as well as `OptiScaler/custom/Apex Neural Rendering FG/dlssg/nvngx_dlssg.dll` and `OptiScaler/nr_fg_install.json`.
3. Only the user can confirm that frames are generated. Ask them to start the game (DX12 if it has a choice), turn on DLSS frame generation, and press **Insert** for OptiScaler's overlay.
4. If it fails, read the newest `nr_fg-*.log` in `OptiScaler/custom/Apex Neural Rendering FG/dlssg/`:
   - No log means OptiScaler did not load. Check the proxy name, the VC++ runtime and the Proton launch option.
   - `NVIDIA DLSS-G not used (user build): NVIDIA's NGX is left to the game` is a build note that every run prints. If the log ends at that line with no feature creation after it, the game never turned DLSS-G on. Move up a spoof tier.
   - A feature was created but there are no extra frames. Check the overlay's DLSSG state (it shows as `Current DLSSG state:`, match without case) and the game's frame limiter.

## 6. Record the result

After each run, create or update `games/<slug>.md` from `games/_template.md` and its row in `games/index.md`. Record the store, renderer, folder, GPU, ANR version, tier and outcome. Label each outcome as **verified** (the user saw generated frames), **reported** (from a GitHub issue, linked) or **untested**. Never upgrade a label without evidence.

## Uninstall

Close the game. Run `uninstall.ps1` (or `sh uninstall.sh`) from the same package with the same folder. It restores the backed-up files.

- It deletes the whole `OptiScaler/` folder, including the user's `nr_fg.ini` changes and the ANR logs. Copy anything the user wants to keep first.
- It does not remove `fakenvapi.dll` or `fakenvapi.ini` from tier 2. Delete them yourself, using the game's file in `games/`.
- On Linux, tell the user to remove `WINEDLLOVERRIDES` from the game's launch options.
