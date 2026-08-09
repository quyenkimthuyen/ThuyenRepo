# Clone identity `E21` — EURUSD M15 (backtest desk)

| Field | Value |
|-------|-------|
| Spec | `E21` (version `E`, offset `21`) |
| Folder | `backtest/EdgeMinerEURUSDM15` |
| Symbol | **EURUSD** M15 |
| INSTANCE_ID | `M15E21` |
| Bridge live / sim | `bridge_m15e21` / `bridge_sim_m15e21` |
| EA live / sim | `ForgeBridgeM15E21` / `ForgeBridgeM15E21Sim` |
| App port | `8711` |
| Bridge / Paper / Sim / Compare | `8975` / `8976` / `9086` / `9196` |
| Magic live / sim | `20261021` / `20262021` |
| Pip | `0.0001` |
| Spread / slip default | `1.0` / `0.3` |
| Data cache | `data/mt5_eurusd_m15.parquet` |

Isolated from stock `EdgeMinerM15` (8501 / magic 20260724 / `bridge`).

## Run

```powershell
cd C:\Work\ThuyenRepo\backtest\EdgeMinerEURUSDM15
.\scripts\run_app_windows.ps1 Start
.\scripts\deploy_xm_forgebridge.ps1 -Mode Live -Attach
```

App: http://localhost:8711
