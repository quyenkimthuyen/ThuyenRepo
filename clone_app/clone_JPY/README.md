# clone_JPY — EdgeMiner USDJPY M15

Isolated USDJPY M15 desk cloned from `EdgeMinerM15` (slot **J9**).

| Folder | Symbol | App | Bridge / Paper / Sim / Compare | Magic live | EA / bridge |
|--------|--------|-----|--------------------------------|------------|-------------|
| `EdgeMinerUSDJPYM15` | USDJPY | **8591** | 8855 / 8856 / 8966 / 9076 | 20261009 | `ForgeBridgeM15J9` / `bridge_m15j9` |

```powershell
cd C:\Work\ThuyenRepo\clone_app\clone_JPY\EdgeMinerUSDJPYM15
.\scripts\run_app_windows.ps1 Start
.\scripts\deploy_xm_forgebridge.ps1 -Mode Live -Attach -SkipBridgeService
```

See `EdgeMinerUSDJPYM15/CLONE_IDENTITY.md`.
