# Clone identity `G23` — GBPUSD M15 (backtest desk)

| Field | Value |
|-------|-------|
| Spec | `G23` (version `G`, offset `23`) |
| Folder | `backtest/EdgeMinerGBPUSDM15` |
| Symbol | **GBPUSD** M15 |
| INSTANCE_ID | `M15G23` |
| Bridge live / sim | `bridge_m15g23` / `bridge_sim_m15g23` |
| EA live / sim | `ForgeBridgeM15G23` / `ForgeBridgeM15G23Sim` |
| App port | `8731` |
| Bridge / Sim / Compare | `8995` / `9106` / `9216` |
| Legacy paper-chart port | `8996` (Paper Monitor desk đã gỡ — giữ slot để tránh đụng port cũ) |
| Magic live / sim | `20261023` / `20262023` |
| Pip | `0.0001` |
| Spread / slip default | `1.5` / `0.3` |
| Data cache | `data/mt5_gbpusd_m15.parquet` |

Isolated from `clone_app/clone_GBP` G14 (8641 / magic 20261014 / `bridge_m15g14`).

## Run

```powershell
cd C:\Work\ThuyenRepo\backtest\EdgeMinerGBPUSDM15
.\scripts\run_app_windows.ps1 Start
.\scripts\deploy_xm_forgebridge.ps1 -Mode Live -Attach
```

App: http://localhost:8731
