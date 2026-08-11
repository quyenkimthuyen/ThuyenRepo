# M5 quality complete — 2026-08-11

Full **KB retrain → Grid (48 combos, quality objective) → Promote** on both desks.
OOS: `2026-01-01` → `2026-08-07`. Eras: `era_5_thang_cuoi_2025` + `era_2025_h2`.
Presets: `elite_or_quality`, `baseline`, `anti_chase_fixed_70`.

## Targets

| Desk | R | PF | WR% | R/DD | Result |
|------|--:|---:|----:|-----:|--------|
| EUR | ≥130 | ≥1.70 | ≥40 | ≥10 | **MET** |
| GBP | ≥150 | ≥1.60 | ≥40 | ≥8 | **MET** |

## Promoted Trade Models

### EUR `M5E31`

| Label | R | n | PF | WR% | DD | R/DD | Notes |
|-------|--:|--:|---:|----:|---:|-----:|-------|
| **BestQuality** (active) | **143.6** | 166 | **2.54** | **49.4** | **6.7** | **21.4** | elite_or · era H2 · tw3 |
| BestTotalR (2) | 277.8 | — | 1.73 | 42.1 | 36.8 | 7.5 | denser / higher DD |
| BestWinRate | 129.7 | — | 2.01 | 46.5 | 7.0 | 18.4 | — |

vs prior M5 BestTotalR (R172 PF1.52 DD23): **quality leap**.
vs M15 BestTotalR (R195 PF2.50 WR~51 DD13): M5 BestQuality has **similar PF/WR, better DD**, lower Total R.

### GBP `M5G33`

| Label | R | n | PF | WR% | DD | R/DD | Notes |
|-------|--:|--:|---:|----:|---:|-----:|-------|
| **BestQuality** (active) | **233.8** | 398 | **1.91** | **43.5** | **12.9** | **18.1** | elite_or · era5 · tw3 |
| BestTotalR | 271.8 | — | 1.57 | 42.4 | 17.6 | 15.4 | — |
| BestWinRate | 251.2 | — | 1.92 | 44.2 | 24.2 | 10.4 | — |

vs prior M5 best (R45 PF1.47): **~5× Total R**, much healthier book.
vs M15 GBP BestR (R100 PF2.22 DD5.8): M5 now **higher R**, PF still a bit below M15 peak.

## Pipeline artifacts

- EUR: `backtestM5/EdgeMinerEURUSDM5/results/research/m5_quality_complete/latest.json`
- GBP: `backtestM5/EdgeMinerGBPUSDM5/results/research/m5_quality_complete/latest.json`
- Grid: `results/grid_search/latest.json` on each desk

## Reproduce

```bash
EdgeMinerM15B5/.venv/bin/python backtestM5/EdgeMinerEURUSDM5/scripts/complete_m5_quality.py
EdgeMinerM15B5/.venv/bin/python backtestM5/EdgeMinerGBPUSDM5/scripts/complete_m5_quality.py
```

## Verdict

**M5 desks are production-ready on the defined quality targets.** Prefer **BestQuality** (active) for live — not raw BestTotalR — because R/DD and PF dominate denser noisy books.
