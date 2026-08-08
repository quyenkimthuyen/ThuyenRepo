# Clone identity `C13` — BTCUSD M15

| Field | Value |
|-------|-------|
| Spec | `C13` (version `C`, offset `13`) |
| Folder | `EdgeMinerBTCUSDM15` |
| Symbol | **BTCUSD** M15 |
| INSTANCE_ID | `M15C13` |
| Bridge live / sim | `bridge_m15c13` / `bridge_sim_m15c13` |
| EA live / sim | `ForgeBridgeM15C13` / `ForgeBridgeM15C13Sim` |
| App port | `8631` |
| Bridge / Paper / Sim / Compare | `8895` / `8896` / `9006` / `9116` |
| Magic live / sim | `20261013` / `20262013` |
| Pip | `1.0` (1 pip ≈ $1) |
| Data cache | `data/mt5_btcusd_m15.parquet` |

## Run (Windows)

```powershell
cd C:\Work\ThuyenRepo\clone_app\clone_BTC\EdgeMinerBTCUSDM15
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\scripts\run_app_windows.ps1 Start
```

App: http://localhost:8631
