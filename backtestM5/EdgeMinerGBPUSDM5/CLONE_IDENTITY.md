# Clone identity `G33` — GBPUSD M5 (backtestM5 desk)

| Field | Value |
|-------|-------|
| Spec | `G33` (version `G`, offset `33`) |
| Folder | `backtestM5/EdgeMinerGBPUSDM5` |
| Symbol | **GBPUSD** M5 |
| INSTANCE_ID | `M5G33` |
| Bridge live / sim | `bridge_m5g33` / `bridge_sim_m5g33` |
| EA live / sim | `ForgeBridgeM5G33` / `ForgeBridgeM5G33Sim` |
| App port | `8831` |
| Magic live / sim | `20261033` / `20262033` |
| Spread / slip default | `1.5` / `0.3` |
| Data cache | `data/mt5_gbpusd_m5.parquet` |
| Cloned from | `backtest/EdgeMinerGBPUSDM15` (M15) |

## M5 hybrid retune (quality × denser book)

Same philosophy as EUR M5 desk (`EdgeMinerEURUSDM5/CLONE_IDENTITY.md`):

- **Quality:** `m5_parity` features + RR/ATR/session like researched M15
- **Capacity:** spacing ~80m, TPW **24**, max **5**/day → target ≈ **×2.4** trades vs M15
- **Hold:** default **192** (~16h); pool 96–288
- Remine KB + Grid required after retune

App: http://localhost:8831