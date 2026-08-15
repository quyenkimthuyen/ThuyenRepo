# M5 stretch refine — 2026-08-11 (pass 2)

Continued in the same direction: expand search (3 eras × 4 presets × latest KB),
add `elite_m5_balanced`, raise stretch targets closer to M15 parity.

## Stretch targets

| Desk | R | PF | WR% | R/DD | Met? |
|------|--:|---:|----:|-----:|------|
| EUR | ≥160 | ≥2.0 | ≥45 | ≥15 | **Partial** (R+R/DD yes; PF/WR on denser book no) |
| GBP | ≥200 | ≥2.0 | ≥45 | ≥15 | **Not all-at-once** (got PF≥2.0 book separately) |

## What improved

### EUR Pareto catalog (use case split)

| Model | R | PF | WR% | DD | R/DD | Use |
|-------|--:|---:|----:|---:|-----:|-----|
| **BestQuality** (active) | 143.6 | **2.54** | **49.4** | **6.7** | 21.4 | Max quality / live conservative |
| **BestBalance** | **193.0** | 1.94 | 42.6 | **7.7** | **24.9** | More R, still excellent risk |
| BestWinRate | 129.7 | 2.01 | 46.5 | 7.0 | 18.4 | WR tilt |
| BestTotalR (2) | 277.8 | 1.73 | 42.1 | 36.8 | 7.5 | Max R only (noisy) |

BestQuality still beats denser books on composite PF×WR; BestBalance is the
sweet spot discovered this pass (≈ M15 Total R with **better** R/DD than M15 BestTotalR).

### GBP catalog

| Model | R | PF | WR% | DD | R/DD | Use |
|-------|--:|---:|----:|---:|-----:|-----|
| **BestQuality** (active) | **233.8** | 1.91 | 43.5 | 12.9 | **18.1** | Best overall |
| **BestPF** (new) | 172.6 | **2.25** | 42.4 | 15.2 | 11.4 | Push PF toward M15 |
| BestTotalR | 271.8 | 1.57 | 42.4 | 17.6 | 15.4 | Max R |
| BestWinRate | 251.2 | 1.92 | 44.2 | 24.2 | 10.4 | WR tilt |

`elite_55_4` delivered the PF breakthrough; `elite_m5_balanced` mid-pack.

## Honest ceiling

Cannot (yet) maximize **all** of R + PF + WR + R/DD in one genome on M5:
- High PF/WR books stay selective (EUR BestQuality tpw~5).
- High R denser books give back PF/WR (EUR BestBalance tpw~11).
- GBP BestQuality already strong on R/R/DD; PF 2.2+ costs Total R.

This is expected market microstructure, not a failed search.

## Code / ops added

- Preset `elite_m5_balanced` (TPW 16, RSI≥60, RR 3–4)
- `scripts/refine_m5_stretch.py` (keep KB, latest-epoch grid)
- Quality score ignores n_trades < 40 (stops sparse PF gaming)
- Grid objective `quality` same floor

## Live recommendation

- **EUR live:** `BestQuality` default; switch to `BestBalance` if you want ~+50R with DD still ~8.
- **GBP live:** keep `BestQuality`; trial `BestPF` on sim if PF priority.

## Reproduce

```bash
EdgeMinerM15B5/.venv/bin/python backtestM5/EdgeMinerEURUSDM5/scripts/refine_m5_stretch.py
EdgeMinerM15B5/.venv/bin/python backtestM5/EdgeMinerGBPUSDM5/scripts/refine_m5_stretch.py
```
