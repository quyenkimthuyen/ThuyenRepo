# backtestM5 — EURUSD / GBPUSD on M5

Cloned from `backtest/` M15 desks to compare pipeline effectiveness on M5.

| Desk | Folder | App | INSTANCE |
|------|--------|-----|----------|
| E31 EUR | `EdgeMinerEURUSDM5` | http://127.0.0.1:8811 | `M5E31` |
| G33 GBP | `EdgeMinerGBPUSDM5` | http://127.0.0.1:8831 | `M5G33` |

**Linux (start / stop / restart / status):**

```bash
cd /home/thuyenng/work/ThuyenRepo/backtestM5
./manage_clones.sh status          # both desks
./manage_clones.sh start           # E31 :8811 + G33 :8831
./manage_clones.sh restart EUR     # only EUR
./manage_clones.sh stop all
```

**Windows:**

```powershell
cd C:\Work\ThuyenRepo\backtestM5
.\manage_clones.ps1 Start
# Then Deploy EA M5 (compile ForgeBridgeM5E31 / M5G33) and Sync history on each desk.
```

**Hybrid retune (post-clone):** fitness TPW bands scale with target 24; elite presets
target ~10–16 tpw with hold=192 / spacing=16; grid risk-adjusted accepts ~12–30 tpw;
`max_trades_per_day` defaults to 5.

**Round 3** (ensemble BestQuality+BestBalance / BestPF + monthly WF stability):

```bash
./run_round3.sh
# or per desk:
# EdgeMinerM15B5/.venv/bin/python EdgeMinerEURUSDM5/scripts/round3_ensemble_monthly.py
```

Outputs: `*/results/research/m5_round3_ensemble/` and `results_m5_round3.md`.

After pulling these changes: **Remine KB + Grid** on each desk (old genomes may still
carry M15 bar semantics). Do not reuse M15 Trade Models.
**Magic Live/Sim (parallel-safe):** E31 `20261061`/`20262061` · G33 `20261081`/`20262081`
(see repo `results_magic_isolation.md`). Recompile EAs after pull.

**Canonical OOS (Trade Model compare):** `2026-01-01` → `2026-08-07` only.

```bash
./run_unify_oos.sh --reuse
```

See `results_m5_oos_unified.md`.
