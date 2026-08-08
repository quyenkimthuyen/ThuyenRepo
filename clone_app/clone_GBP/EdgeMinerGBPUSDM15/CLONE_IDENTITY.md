# Clone identity `G14` — GBPUSD M15

| Field | Value |
|-------|-------|
| Spec | `G14` (version `G`, offset `14`) |
| Folder | `EdgeMinerGBPUSDM15` |
| Symbol | **GBPUSD** M15 |
| INSTANCE_ID | `M15G14` |
| Bridge live / sim | `bridge_m15g14` / `bridge_sim_m15g14` |
| EA live / sim | `ForgeBridgeM15G14` / `ForgeBridgeM15G14Sim` |
| App port | `8641` |
| Bridge / Paper / Sim / Compare | `8905` / `8906` / `9016` / `9126` |
| Magic live / sim | `20261014` / `20262014` |
| Pip | `0.0001` |
| Spread / slip default | `1.5` / `0.3` |
| Data cache | `data/mt5_gbpusd_m15.parquet` |

## Run (Windows)

```powershell
cd C:\Work\ThuyenRepo\clone_app\clone_GBP\EdgeMinerGBPUSDM15
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\scripts\run_app_windows.ps1 Start
```

App: http://localhost:8641
