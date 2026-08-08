# clone_GBP — EdgeMiner GBPUSD M15

Isolated GBPUSD M15 desk cloned from `EdgeMinerM15` (slot **G14**).

| Folder | Symbol | App | Bridge / Paper / Sim / Compare | Magic live | EA / bridge |
|--------|--------|-----|--------------------------------|------------|-------------|
| `EdgeMinerGBPUSDM15` | GBPUSD | **8641** | 8905 / 8906 / 9016 / 9126 | 20261014 | `ForgeBridgeM15G14` / `bridge_m15g14` |

```powershell
cd C:\Work\ThuyenRepo\clone_app\clone_GBP\EdgeMinerGBPUSDM15
.\scripts\run_app_windows.ps1 Start
.\scripts\deploy_xm_forgebridge.ps1 -Mode Live -Attach -SkipBridgeService
```

See `EdgeMinerGBPUSDM15/CLONE_IDENTITY.md`.
