# Games

Status of ANR FG per game. **Verified** means the user saw generated frames. **Reported** means a linked GitHub issue or OptiScaler wiki page says so. Wiki rows describe OptiScaler with other frame generation, not ANR. They show whether the game offers DLSS-G and which spoof settings it needs. Wiki pages were read on 2026-11-22 (wiki clone dated 2026-11-18). **Title only** means the status comes from an issue title that nobody has read yet. Before you trust a title-only row, read the issue and give the game its own file.

The spoof tier column holds one of the tiers from SKILL.md step 4 (0, 1, 1V, 2), `unknown`, or `none` when no tier is known to work. Put any qualifier in the Status column.

Issue status was checked on 2026-11-22 against ANR FG V.B20. Rows go stale with each release. Before you act on a row, re-read its linked issue (state and newest comments). Then update the row and this date.

| Game | File | Status | Spoof tier | Source |
|---|---|---|---|---|
| The Witcher 3 (Steam) | [the-witcher-3.md](the-witcher-3.md) | Installed, untested | 1 | one local install |
| The Witcher 3 (Game Pass, AMD) | [the-witcher-3.md](the-witcher-3.md) | Fails: DLSS-G stays off with tiers 1 and 2 (reported) | unknown | [#15](https://github.com/apex-compute/ANR/issues/15), [#82](https://github.com/apex-compute/ANR/issues/82) |
| Final Fantasy VII Rebirth | [final-fantasy-vii-rebirth.md](final-fantasy-vii-rebirth.md) | Works on RTX 3070 (reported) | 0 | [#11](https://github.com/apex-compute/ANR/issues/11) |
| Like a Dragon: Infinite Wealth | [like-a-dragon-infinite-wealth.md](like-a-dragon-infinite-wealth.md) | Works on RTX 3080 under Proton, then freezes (reported) | 0 | [#46](https://github.com/apex-compute/ANR/issues/46) |
| Cyberpunk 2077 | [cyberpunk-2077.md](cyberpunk-2077.md) | Works, with UI jitter (reported) | unknown | [#8](https://github.com/apex-compute/ANR/issues/8), [#87](https://github.com/apex-compute/ANR/issues/87), [wiki](https://github.com/optiscaler/OptiScaler/wiki/Cyberpunk-2077) |
| Where Winds Meet | [where-winds-meet.md](where-winds-meet.md) | Fails: DLSS-G stays off (reported) | unknown | [#82](https://github.com/apex-compute/ANR/issues/82) |
| Crimson Desert | none | Runs, with HUD jitter because the game gives no HUD-less buffer. Crash before menu (closed). Frame time spikes (title only) | unknown | [#24](https://github.com/apex-compute/ANR/issues/24), [#36](https://github.com/apex-compute/ANR/issues/36), [#67](https://github.com/apex-compute/ANR/issues/67) |
| Forza Horizon 6 | none | Artifacts (title only). Page fault on Radeon 890M with forced dynamic MFG (closed) | unknown | [#94](https://github.com/apex-compute/ANR/issues/94), [#31](https://github.com/apex-compute/ANR/issues/31) |
| Microsoft Flight Simulator 2020 | none | Crash fixed in V.B19 | unknown | [#58](https://github.com/apex-compute/ANR/issues/58) |
| Microsoft Flight Simulator 2024 | none | Crash on launch or FG toggle (title only, open) | unknown | [#40](https://github.com/apex-compute/ANR/issues/40) |
| Stalker 2 | [stalker-2.md](stalker-2.md) | Ghosting (title only). Wiki: DLSSG via Streamline, Intel Arc needs `Dxgi=false` | 1 | [#17](https://github.com/apex-compute/ANR/issues/17), [wiki](https://github.com/optiscaler/OptiScaler/wiki/S.T.A.L.K.E.R.-2-Heart-of-Chornobyl) |
| Final Fantasy XVI | none | Ghosting (title only) | unknown | [#51](https://github.com/apex-compute/ANR/issues/51) |
| Wuthering Waves | none | Tearing on translucent ribbons (title only) | unknown | [#68](https://github.com/apex-compute/ANR/issues/68) |
| No Man's Sky (Vulkan) | none | Garbled image on AMD, fixed in V.B19 | unknown | [#55](https://github.com/apex-compute/ANR/issues/55) |
| DOOM: The Dark Ages | [doom-the-dark-ages.md](doom-the-dark-ages.md) | No added smoothness (title only). Wiki: spoofing cannot unlock DLSS-G on AMD/Intel (reported). 1V untested on NVIDIA | none | [#62](https://github.com/apex-compute/ANR/issues/62), [wiki](https://github.com/optiscaler/OptiScaler/wiki/Doom-The-Dark-Ages) |
| Hitman: World of Assassination | none | Not working (title only) | unknown | [#90](https://github.com/apex-compute/ANR/issues/90) |
| Horizon Forbidden West | none | Error (title only) | unknown | [#91](https://github.com/apex-compute/ANR/issues/91) |
| Elden Ring 2.7.2.0 | none | Crash at startup (title only) | unknown | [#83](https://github.com/apex-compute/ANR/issues/83) |
| 007 First Light | none | Crash at startup (title only) | unknown | [#72](https://github.com/apex-compute/ANR/issues/72), [#81](https://github.com/apex-compute/ANR/issues/81) |
| Bodycam | none | Error 0xc000007b at startup (title only) | unknown | [#73](https://github.com/apex-compute/ANR/issues/73) |
| Enshrouded (Linux) | none | Does not launch (title only) | unknown | [#75](https://github.com/apex-compute/ANR/issues/75) |
| Starfield | [starfield.md](starfield.md) | Error on opening (title only, closed). Wiki: Nukem's works | 1 | [#30](https://github.com/apex-compute/ANR/issues/30), [wiki](https://github.com/optiscaler/OptiScaler/wiki/Starfield) |
| Alan Wake II | [alan-wake-2.md](alan-wake-2.md) | No ANR reports. Wiki: DLSSG via Streamline (reported) | 1 | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Alan-Wake-II) |
| Black Myth: Wukong | [black-myth-wukong.md](black-myth-wukong.md) | No ANR reports. Wiki: spoofing corrupts textures, use OptiPatcher or `Dxgi=false` with tier 1 (reported) | 1 | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Black-Myth-Wukong) |
| Hogwarts Legacy | [hogwarts-legacy.md](hogwarts-legacy.md) | No ANR reports. Wiki: DLSSG via Streamline, OptiPatcher works (reported) | 1 | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Hogwarts-Legacy) |
| Indiana Jones and the Great Circle (Vulkan) | [indiana-jones-great-circle.md](indiana-jones-great-circle.md) | No ANR reports. Wiki: Nukem's works (reported). DLSS-G not confirmed | 1V | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Indiana-Jones-and-the-Great-Circle) |
| Monster Hunter Wilds | [monster-hunter-wilds.md](monster-hunter-wilds.md) | No ANR reports. Wiki: DLSSG via SL, motion blur off, FG 2x, needs REFramework, `Dxgi=false` on AMD/Intel (reported) | 1 | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Monster-Hunter-Wilds) |
| Marvel's Spider-Man 2 | [marvels-spider-man-2.md](marvels-spider-man-2.md) | No ANR reports. Wiki: DLSSG via SL, AMD/Intel crash with RT and spoofing (reported) | 1 | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Marvels-Spider‐Man-2) |
| Kingdom Come: Deliverance II | [kingdom-come-deliverance-2.md](kingdom-come-deliverance-2.md) | Cannot work: no DLSS frame generation in game (wiki, reported) | none | [wiki](https://github.com/optiscaler/OptiScaler/wiki/Kingdom-Come-Deliverance-II) |
