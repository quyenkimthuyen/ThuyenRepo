# Live roster WR optimize

OOS `2026-01-01` → `2026-08-07` · 2026-08-14T11:11:26+05:30

**Parity:** Models OK **12/12** · batch ok=True
**Portfolio TotalR:** 1950.816 → 2043.604 (Δ +92.788)
**Replaces:** 5/12

| Book | Role | Action | Before R | Before WR | After R | After WR | ΔR | ΔWR | Parity |
|------|------|--------|----------|-----------|---------|----------|----|-----|--------|
| EURUSD M15 | WR | `keep` | 63.366 | 47.42 | 63.366 | 47.42 | +0.000 | +0.00 | OK |
| EURUSD M15 | R | `keep` | 124.119 | 39.93 | 124.119 | 39.93 | +0.000 | +0.00 | OK |
| EURUSD M15 | Balance | `keep` | 69.535 | 46.46 | 69.535 | 46.46 | +0.000 | +0.00 | OK |
| EURUSD M5 | WR | `keep` | 138.042 | 47.78 | 138.042 | 47.78 | +0.000 | +0.00 | OK |
| EURUSD M5 | R | `replace` | 285.037 | 42.26 | 286.717 | 43.47 | +1.680 | +1.21 | OK |
| EURUSD M5 | Balance | `replace` | 127.555 | 47.19 | 138.042 | 47.78 | +10.487 | +0.59 | OK |
| GBPUSD M15 | WR | `replace` | 131.547 | 52.68 | 134.06 | 53.4 | +2.513 | +0.72 | OK |
| GBPUSD M15 | R | `keep` | 134.06 | 53.4 | 134.06 | 53.4 | +0.000 | +0.00 | OK |
| GBPUSD M15 | Balance | `replace` | 90.828 | 46.01 | 134.06 | 53.4 | +43.232 | +7.39 | OK |
| GBPUSD M5 | WR | `keep` | 272.588 | 42.5 | 272.588 | 42.5 | +0.000 | +0.00 | OK |
| GBPUSD M5 | R | `keep` | 276.427 | 42.48 | 276.427 | 42.48 | +0.000 | +0.00 | OK |
| GBPUSD M5 | Balance | `replace` | 237.712 | 41.89 | 272.588 | 42.5 | +34.876 | +0.61 | OK |

## Notes
- Gate: WR↑ strict, TotalR≥, PF≥1.3, n≥40.
- GBPUSD M15 WR/R/Balance share StretchR_2 after promote (role diversity collapsed by gate).
- EURUSD M5 WR/Balance and GBPUSD M5 WR/Balance share BestWinRate.
- Schedules frozen + packages imported; all 12 roster slots On + ready.
