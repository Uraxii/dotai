# Monster Hunter Wilds

- **Store and version:** any.
- **Renderer:** D3D12.
- **Exe folder:** the folder with `MonsterHunterWilds.exe`.
- **Proxy:** `dxgi.dll`. The OptiScaler wiki says OptiScaler needs REFramework (its `dinput8.dll`) to work in this game, and gives a special layout when SpecialK is also installed. Read the wiki page before you install. Ask before you download REFramework.
- **DLSS-G in game:** yes. The OptiScaler wiki lists "DLSSG via SL" inputs.
- **Overlay key:** REFramework and OptiScaler both use **Insert**. The wiki says to change REFramework's menu key (for example to Delete) so step 5's overlay check works.

## Spoof recipe

Tier 1 on NVIDIA. On AMD and Intel, use `Dxgi=false` with `StreamlineSpoofing=true` and `SpoofHAGS=true`, because the wiki says Streamline spoofing already unlocks DLSS there (OptiScaler 0.9 does this by itself). The [OptiScaler wiki page](https://github.com/optiscaler/OptiScaler/wiki/Monster-Hunter-Wilds) (reported, RX 6700 XT, RX 9070 XT, OptiScaler 0.9) also says:
- Turn off motion blur. It causes artifacts with DLSSG inputs.
- Set the game's DLSS frame generation to 2x, not Auto. Auto is crash-prone.

## Results

| Date | GPU | OS | ANR | Tier | Outcome | Label | Source |
|---|---|---|---|---|---|---|---|

No ANR runs yet.

## Known problems

- Crash on boot with some vendors when DLSSG inputs go to XeFG (wiki, reported). It is not known whether ANR is affected.
