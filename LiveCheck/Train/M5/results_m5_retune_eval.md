# M5 retune eval — 2026-08-11

OOS window: `2026-01-01` → `2026-08-07`, feature `m5_parity`.
Method: remine walk-forward on **existing KB** (no KB retrain). Isolates fitness/preset/genome retune.

Artifacts:
- EUR: `backtestM5/EdgeMinerEURUSDM5/results/research/m5_retune_eval/`
- GBP: `backtestM5/EdgeMinerGBPUSDM5/results/research/m5_retune_eval/`

## EURUSD

| Run | R | n | PF | WR% | DD | tpw | R/trade | R/DD |
|-----|--:|--:|---:|----:|---:|----:|--------:|-----:|
| OLD BestTotalR (baseline tpw24) | **172.7** | 592 | 1.52 | 39.2 | 23.4 | ~19 | 0.29 | 7.4 |
| NEW baseline tw3 era5 | 152.7 | 565 | 1.51 | 39.3 | 27.4 | 18.2 | 0.27 | 5.6 |
| OLD elite_or (tpw8) | 136.4 | 310 | **1.69** | 40.3 | 15.1 | ~10 | 0.44 | 9.0 |
| NEW elite_or tpw14 tw3 | 129.0 | 301 | 1.68 | 39.9 | **10.0** | 9.7 | **0.43** | **12.8** |
| NEW elite @ tpw8 (control) | 113.7 | 291 | 1.61 | 38.8 | 19.3 | 9.4 | 0.39 | 5.9 |
| NEW elite tw3 era3 | -74.2 | 123 | 0.39 | 17.9 | 77.4 | 4.0 | -0.60 | -1.0 |

Read:
- Fitness/preset retune **improved elite risk** (DD↓, R/DD↑) but did **not** beat BestTotalR Total R.
- New elite TPW14 > legacy TPW8 under same new fitness.
- `era_3_thang_cuoi_2025` is a bad KB for this OOS.

## GBPUSD

### Fair (same KB as old models: `era_2025_2026_6thang`)

| Run | R | n | PF | WR% | DD | tpw | R/DD |
|-----|--:|--:|---:|----:|---:|----:|-----:|
| OLD best | 45.4 | 146 | 1.47 | 39.0 | 10.2 | ~5 | 4.5 |
| NEW baseline tw3 | **125.4** | 507 | 1.34 | 37.3 | 20.8 | 16.4 | **6.0** |
| NEW baseline tw6 | 98.8 | 508 | 1.19 | 35.8 | 20.8 | 16.4 | 4.7 |
| NEW elite_or tw6 | 39.8 | 71 | 1.58 | 40.9 | 10.0 | 2.3 | 4.0 |

### Bonus (better KB: `era_5_thang_cuoi_2025`)

| Run | R | n | PF | WR% | DD | tpw | R/DD |
|-----|--:|--:|---:|----:|---:|----:|-----:|
| NEW baseline tw6 era5 | **275.3** | 738 | 1.54 | 40.4 | 18.1 | 23.8 | **15.2** |
| NEW elite_or tw6 era5 | 185.8 | 311 | **1.81** | **42.8** | 21.5 | 10.0 | 8.6 |

## Verdict

1. **Retune is real but partial.** Elite EUR is healthier on drawdown; GBP remine on correct M5 capacity crushes prior leftover-sparse models.
2. **Not yet M15-competitive on EUR quality** (PF still ~1.5–1.7 vs M15 ~2.2–2.5).
3. **Next lever:** full KB retrain + grid with new presets (especially GBP `era_5` / multi-era), then promote best risk-adjusted books — not Total-R-only denser tape.

## Reproduce

```bash
EdgeMinerM15B5/.venv/bin/python backtestM5/EdgeMinerEURUSDM5/scripts/eval_m5_retune.py --workers 6
EdgeMinerM15B5/.venv/bin/python backtestM5/EdgeMinerGBPUSDM5/scripts/eval_m5_retune.py --workers 6
```
