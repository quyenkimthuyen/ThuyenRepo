# Magic isolation — 4 desks Live/Sim parallel-safe

Updated: 2026-08-11

Each desk gets a **base magic spaced by 20** (room for `InpMaxModels=5` → +0..+4).
Sim = Live with `20261` → `20262` (same low digits).

| Desk | INSTANCE | Live base | Live range | Sim base | Sim range | Bridge |
|------|----------|-----------|------------|----------|-----------|--------|
| EUR M15 | M15E21 | **20261021** | 21–25 | **20262021** | 21–25 | `bridge_m15e21` / `bridge_sim_m15e21` |
| GBP M15 | M15G23 | **20261041** | 41–45 | **20262041** | 41–45 | `bridge_m15g23` / `bridge_sim_m15g23` |
| EUR M5 | M5E31 | **20261061** | 61–65 | **20262061** | 61–65 | `bridge_m5e31` / `bridge_sim_m5e31` |
| GBP M5 | M5G33 | **20261081** | 81–85 | **20262081** | 81–85 | `bridge_m5g33` / `bridge_sim_m5g33` |

40 unique magics across 8 Live/Sim channels — **no overlap**.

## Code fixes included

1. `protocol.py` — `DEFAULT_MAGIC` / `DEFAULT_SIM_MAGIC`
2. EA `InpMagic` — Live + Sim `.mq5`
3. `models.json` — reassigned sequential magics from new base (Live **and** Sim)
4. `gui/trade_model.py` — rewriting roster for `BRIDGE_SIM_DIR` now uses `DEFAULT_SIM_MAGIC` (was wrongly using live base)
5. Deploy scripts / README / CLONE_IDENTITY / contracts tests

## After pull — MT5 side

Recompile / re-attach (or refresh inputs) the instance EAs so `InpMagic` matches the table.
Old open positions still carry previous magics — close or manage manually before relying on new roster.
