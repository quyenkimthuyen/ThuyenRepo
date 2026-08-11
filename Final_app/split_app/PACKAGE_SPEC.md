# Trade Model Package Spec v1

Extension: `.tmpkg` (zip). Layout inside:

```text
manifest.json          # required
model.json             # required — Trade Model fields for live remine
metrics.json           # optional — OOS KPI snapshot (display only)
kb_pin.json            # required if use_kb
schedule.json          # optional — frozen weekly strategies from lab WF
SHA256SUMS             # required
```

## manifest.json

```json
{
  "package_version": 1,
  "format": "edgeminer.trade_model_package",
  "created_at": "ISO-8601",
  "lab": {
    "desk": "EdgeMinerEURUSDM5",
    "instance": "M5F3",
    "repo_relative": "Final_app/EdgeMinerEURUSDM5"
  },
  "model_id": "tm_...",
  "label": "BestQuality",
  "symbol": "EURUSD",
  "timeframe": "M5",
  "oos_from": "2026-01-01",
  "oos_to": "2026-08-07",
  "feature_profile": "m5_parity",
  "use_kb": true,
  "kb_fingerprint": "abcd...",
  "files": ["manifest.json", "model.json", "kb_pin.json", "metrics.json"]
}
```

## model.json (minimum for weekly remine)

- `id`, `label`
- `mining_search_space` (dict)
- `train_weeks`, `use_kb`, `kb_profile`, `kb_snapshot` (snapshot informational; pin is source of truth)
- `spread_pips`, `slippage_pips`, `max_trades_per_day`, `feature_profile`
- `oos_from`, `oos_to`
- KPI fields optional: `total_r`, `profit_factor`, …

Live **does not** require lab `results/` paths.

## Compatibility

- Live rejects `package_version` > supported max.
- Symbol/TF on chart must match manifest (`chart_validate` before Start; mismatch blocks Start when require EA online).
- Magic numbers are **assigned by Live**, not taken from lab.
- Enabled roster must be homogeneous symbol+TF (one ForgeBridgeLive chart).
- `model.json` should include `data_source=mt5_ea`, `data_timeframe`, `feature_schema≥3` (export adds these; materialize backfills).
