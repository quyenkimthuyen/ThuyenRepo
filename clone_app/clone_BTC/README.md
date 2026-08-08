# clone_BTC — EdgeMiner BTCUSD M15

Isolated BTCUSD M15 desk cloned from `EdgeMinerM15` (slot **C13**).

| Folder | Symbol | App | Bridge / Paper / Sim / Compare | Magic live | EA / bridge |
|--------|--------|-----|--------------------------------|------------|-------------|
| `EdgeMinerBTCUSDM15` | BTCUSD | **8631** | 8895 / 8896 / 9006 / 9116 | 20261013 | `ForgeBridgeM15C13` / `bridge_m15c13` |

```powershell
cd C:\Work\ThuyenRepo\clone_app\clone_BTC\EdgeMinerBTCUSDM15
.\scripts\run_app_windows.ps1 Start
.\scripts\deploy_xm_forgebridge.ps1 -Mode Live -Attach -SkipBridgeService
```

See `EdgeMinerBTCUSDM15/CLONE_IDENTITY.md`.
