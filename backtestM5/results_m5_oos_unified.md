# M5 — Unified OOS window for Trade Model compare

**Canonical OOS only:** `2026-01-01` → `2026-08-07`

All live Trade Model KPIs on both desks were re-scored on this window.
App settings, active workspace, and UI compare dates are locked to the same range.

```bash
cd /home/thuyenng/work/ThuyenRepo/backtestM5
./run_unify_oos.sh          # full re-score both desks
./run_unify_oos.sh --reuse  # reuse cached OOS reports when window matches
```

Artifacts: `EdgeMiner*/results/research/m5_oos_unified/{latest.json,compare.md}`

## EUR (EdgeMinerEURUSDM5) — live models

| Rank | Label | Total R | PF | WR% | MaxDD R | Trades | TPW |
|------|-------|---------|-----|-----|---------|--------|-----|
| 1 | BestTotalR (2) | 277.8 | 1.73 | 42.1 | 36.8 | 701 | 22.6 |
| 2 | BestTotalR | 229.1 | 1.65 | 41.4 | 17.6 | 671 | 21.7 |
| 3 | Balance | 206.9 | 1.99 | 43.4 | 8.7 | 350 | 11.3 |
| 4 | BestBalanceLegacy | 193.1 | 1.96 | 42.9 | 8.0 | 345 | 11.1 |
| 5 | BestBalance | 193.0 | 1.94 | 42.6 | 7.7 | 350 | 11.3 |
| 6 | EliteLegacy | 186.8 | 1.96 | 42.5 | 9.6 | 341 | 11.0 |
| 7 | BestQuality | 143.6 | **2.54** | **49.4** | **6.7** | 166 | 5.4 |
| 8 | BestWinRate | 129.7 | 2.01 | 46.5 | 7.0 | 183 | 5.9 |

Active: **BestQuality** · Compare UI: BestQuality / BestBalance / …

## GBP (EdgeMinerGBPUSDM5) — live models

| Rank | Label | Total R | PF | WR% | MaxDD R | Trades | TPW |
|------|-------|---------|-----|-----|---------|--------|-----|
| 1 | BestTotalR | 271.8 | 1.57 | 42.4 | 17.6 | 661 | 21.3 |
| 2 | BestWinRate | 251.2 | 1.92 | 44.2 | 24.2 | 396 | 12.8 |
| 3 | BestQuality | 233.8 | 1.91 | 43.5 | 12.9 | 398 | 12.8 |
| 4 | BestPF | 172.6 | **2.25** | 42.4 | 15.2 | 205 | 6.6 |

Active: **BestQuality** · 3 auto “Học 6 tuần…” models (ex Apr–Aug window) archived after full-window rescore.

## Notes

- Do not compare models across different OOS ranges.
- Round-3 ensemble docs remain valid on this same window.
- Re-run `./run_unify_oos.sh` after promoting new models so registry KPIs stay aligned.
