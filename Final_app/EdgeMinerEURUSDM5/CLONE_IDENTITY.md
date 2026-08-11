# Clone identity `E31` — EURUSD M5 (backtestM5 desk)

| Field | Value |
|-------|-------|
| Spec | `E31` (version `E`, offset `31`) |
| Folder | `backtestM5/EdgeMinerEURUSDM5` |
| Symbol | **EURUSD** M5 |
| INSTANCE_ID | `M5F3` |
| Bridge live / sim | `bridge_m5f3` / `bridge_sim_m5f3` |
| EA live / sim | `ForgeBridgeM5F3` / `ForgeBridgeM5F3Sim` |
| App port | `8811` |
| Bridge / Sim / Compare | `9075` / `9186` / `9296` |
| Legacy paper-chart port | `9076` |
| Magic live / sim | `20261541` / `20262541` |
| Pip | `0.0001` |
| Spread / slip default | `1.0` / `0.3` |
| Data cache | `data/mt5_eurusd_m5.parquet` |
| Cloned from | `backtest/EdgeMinerEURUSDM15` (M15) |

## M5 hybrid retune (quality × denser book)

M5 has ~3× bars per calendar week vs M15. Pure wall-clock ×3 on **spacing** would keep the same trade count — wasting the denser tape. Pure bar-clone (hold=96≈8h, spacing=12≈1h) keeps frequency but can dilute signal quality.

**Split the knobs:**

| Layer | Choice | Why |
|-------|--------|-----|
| Features (`m5_parity`) | lookbacks ≈ M15 wall-clock (RSI/ATR 42, …) | Same “noise horizon” as researched M15 → comparable edge quality |
| RR / ATR / session hours | keep M15 ladder | Risk geometry is R-based, not bar-based |
| Hold | default **192** (~16h); pool 96–288 | Room to finish swings; not locked to 24h so capital recycles |
| Spacing | default **16** (~80m); pool 8–24 | ~2–3× denser than M15’s 3h spacing |
| Capacity | **TPW 24**, **max 5/day** | Target ≈ **×2.4** trades vs M15’s 10/week & 2/day |
| `MIN_TRAIN_BARS` | **1500** | Gate scales with M5 density |

Remine KB + Grid after this retune — old genomes still carry M15 bar semantics.

## Run

```powershell
cd C:\Work\ThuyenRepo\backtestM5\EdgeMinerEURUSDM5
.\scripts\run_app_windows.ps1 Start
.\scripts\deploy_xm_forgebridge.ps1 -Mode Live -Attach
```

App: http://localhost:8811
