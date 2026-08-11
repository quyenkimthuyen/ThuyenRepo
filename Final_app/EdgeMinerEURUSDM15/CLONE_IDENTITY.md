# Clone identity `E21` — EURUSD M15 (backtest desk)

| Field | Value |
|-------|-------|
| Spec | `E21` (version `E`, offset `21`) |
| Folder | `backtest/EdgeMinerEURUSDM15` |
| Symbol | **EURUSD** M15 |
| INSTANCE_ID | `M15F1` |
| Bridge live / sim | `bridge_m15f1` / `bridge_sim_m15f1` |
| EA live / sim | `ForgeBridgeM15F1` / `ForgeBridgeM15F1Sim` |
| App port | `8711` |
| Bridge / Sim / Compare | `8975` / `9086` / `9196` |
| Legacy paper-chart port | `8976` (Paper Monitor desk đã gỡ — giữ slot để tránh đụng port cũ) |
| Magic live / sim | `20261501` / `20262501` |
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
