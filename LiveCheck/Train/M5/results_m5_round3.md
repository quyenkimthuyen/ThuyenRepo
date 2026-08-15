# M5 Round 3 — Ensemble + monthly walk-forward stability

OOS window: ~2026-01 → 2026-08 (8 calendar months).  
Script: `*/scripts/round3_ensemble_monthly.py` · runner: `./run_round3.sh`

## Manage apps (Linux)

```bash
cd /home/thuyenng/work/ThuyenRepo/backtestM5
./manage_clones.sh status|start|stop|restart [E31|G33|EUR|GBP|all]
```

| Desk | Port | INSTANCE |
|------|------|----------|
| EdgeMinerEURUSDM5 | 8811 | M5E31 |
| EdgeMinerGBPUSDM5 | 8831 | M5G33 |

## EUR — BestQuality + BestBalance

| Book | Total R | PF | WR% | MaxDD R | +months | Worst month R | Monthly Sharpe |
|------|---------|-----|-----|---------|---------|---------------|----------------|
| BestQuality | 143.6 | 2.54 | 49.4 | 6.7 | **100%** | 6.3 | 2.24 |
| BestBalance | 193.0 | 1.94 | 42.6 | 7.7 | **100%** | 1.9 | 1.93 |
| **capital_split 50/50** ★ | **168.3** | — | — | — | **100%** | **4.1** | **2.27** |
| union_dedupe | 273.1 | — | — | — | 100% | 9.5 | 2.16 |
| agree_month | 168.3 | — | — | — | 100% | 4.1 | 2.27 |

Monthly R (BestQuality): 25.4, 32.0, 17.7, 11.6, 13.5, 12.8, 24.3, 6.3  
Monthly R (BestBalance): 29.8, 31.5, 20.9, 7.7, 40.8, 26.0, 34.5, 1.9

**Verdict EUR:** Both legs green every month. Prefer **capital_split_50_50** (best monthly Sharpe, softens worst month vs either single; union is higher R but heavier month-end DD path).

## GBP — BestQuality + BestPF

(No BestBalance on this desk.)

| Book | Total R | PF | WR% | MaxDD R | +months | Worst month R | Monthly Sharpe |
|------|---------|-----|-----|---------|---------|---------------|----------------|
| BestQuality | 233.8 | 1.91 | 43.5 | 12.9 | 87.5% | **-2.9** | 1.65 |
| BestPF | 172.6 | 2.25 | 42.4 | 15.2 | **100%** | 1.4 | 1.28 |
| capital_split 50/50 | 203.2 | — | — | — | 87.5% | -0.8 | 1.53 |
| **union_dedupe** ★ | **238.0** | — | — | — | **100%** | **1.2** | 1.47 |
| agree_month | 204.0 | — | — | — | 87.5% | 0.0 | 1.55 |

Monthly R (BestQuality): 39.3, 36.8, 46.5, 45.3, 40.8, 23.4, 4.8, **-2.9**  
Monthly R (BestPF): 21.7, 23.6, 30.5, 52.8, 35.0, 3.9, 3.6, 1.4

**Verdict GBP:** BestQuality alone has one red month (Aug). Ensemble **union_dedupe** keeps all months ≥0 and recovers most of BestQuality’s R. For risk-first live, **agree_month** or 50/50 also cuts the Aug loss.

## Recommendation

1. **EUR live:** Bridge roster = BestQuality + BestBalance at **0.5R each** (capital split).  
2. **GBP live:** Prefer BestQuality+BestPF via **union** roster (or 50/50 if you want softer Aug).  
3. Re-run after new OOS weeks: `./run_round3.sh` (add `--reuse` to skip WF if reports cached).

Artifacts: `EdgeMiner*/results/research/m5_round3_ensemble/latest.json`
