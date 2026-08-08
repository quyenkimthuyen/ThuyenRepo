# Clone identity `J9` — USDJPY M15

| Field | Value |
|-------|-------|
| Spec | `J9` (version `J`, offset `9`) |
| Folder | `EdgeMinerUSDJPYM15` (cloned from EdgeMinerM15) |
| Symbol | **USDJPY** M15 |
| INSTANCE_ID | `M15J9` |
| Bridge live / sim | `bridge_m15j9` / `bridge_sim_m15j9` |
| EA live / sim | `ForgeBridgeM15J9` / `ForgeBridgeM15J9Sim` |
| App port | `8591` (= 8501 + 9*10) |
| Bridge monitor | `8855` (= 8765 + 9*10) |
| Paper monitor | `8856` (= 8766 + 9*10) |
| Sim monitor | `8966` (= 8876 + 9*10) |
| Compare monitor | `9076` (= 8986 + 9*10) |
| Magic live / sim | `20261009` / `20262009` |
| Pip | `0.01` |
| Data cache | `data/mt5_usdjpy_m15.parquet` |

## Run (Windows)

```powershell
cd C:\Work\ThuyenRepo\clone_app\clone_JPY\EdgeMinerUSDJPYM15
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\scripts\run_app_windows.ps1 Start
```

App: http://localhost:8591

Offset must stay unique vs other clones (ports derive only from offset).
