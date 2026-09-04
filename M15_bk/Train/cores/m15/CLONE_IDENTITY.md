# Clone identity `E21` — EURUSD M15 (backtest desk)

| Field | Value |
|-------|-------|
| Spec | `E21` (version `E`, offset `21`) |
| Folder | `backtest/EdgeMinerEURUSDM15` |
| Symbol | **EURUSD** M15 |
| INSTANCE_ID | `LC2E21` |
| Bridge live / sim | `bridge_m15e21` / `bridge_sim_m15e21` |
| EA live / sim | `ForgeBridgeLC2E21` / `ForgeBridgeLC2E21Sim` |
| App port | `8911` |
| Bridge / Sim / Compare | `9975` / `10086` / `10196` |
| Legacy paper-chart port | `8976` (Paper Monitor desk đã gỡ — giữ slot để tránh đụng port cũ) |
| Magic live / sim | `20281021` / `20282021` |
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

App: http://localhost:8911
