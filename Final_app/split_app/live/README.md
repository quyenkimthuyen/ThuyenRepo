# Live Trade App

Import `.tmpkg` từ lab → roster → **1 EA chung** `ForgeBridgeLive` → remine tuần tại chỗ (KB pin trong package).

## Tính năng (v1)

| Phần | Module |
|------|--------|
| Import / list packages | `import_trade_package.py` |
| Roster on/off + risk% + magic | `package_store.py`, `magic_allocator.py` |
| Materialize → BridgeEngine store | `materialize_models.py` |
| Remine host (Final_app desk code) | `runtime_host.py`, `runtime_bootstrap.py` |
| Bridge Start/Stop | `bridge_control.py`, `scripts/mt5_bridge_service_live.py` |
| Chart symbol/TF check | `chart_validate.py` |
| Flatten / kill-switch / loss-guard | `safety.py` (+ desk loss_guard in service) |
| Journal | `journal_view.py` |
| Windows DeployEA | `scripts/deploy_live_ea.ps1` |

Magic / port: base **`20263001`**, UI **`8601`**, monitor **`9601`**.

## Commands

```bash
cd /home/thuyenng/work/ThuyenRepo/Final_app/split_app

# Import
python live/import_trade_package.py packages_out/some.tmpkg
python live/import_trade_package.py --list

# Roster → models.json
python live/sync_bridge_roster.py

# Smoke (no MT5 required for most checks)
../../EdgeMinerM15B5/.venv/bin/python live/scripts/smoke_live.py

# Bridge service
../../EdgeMinerM15B5/.venv/bin/python -c "import bridge_control; print(bridge_control.start_bridge())"
# stop:
../../EdgeMinerM15B5/.venv/bin/python -c "import bridge_control; bridge_control.stop_bridge(flatten=True)"

# UI
./live/scripts/run_app_linux.sh Start
# http://127.0.0.1:8601
```

Windows:

```powershell
.\live\scripts\run_app_windows.ps1 -Action Start
.\live\scripts\deploy_live_ea.ps1   # Attach + EnableTrading default
.\live\scripts\deploy_live_ea.ps1 -Symbol EURUSD -Timeframe M5 -Mode Both
```

## Remine

Package mang **recipe** (search space + KB pin). Mỗi tuần service gọi `optimize_on_window` trên data broker — **không** cần re-export từ lab.

Enabled roster phải **cùng symbol+TF** (một chart / một EA). Mixed books → chart/EA riêng.

## Không có trong Live

KB learning, Grid, promote, unify OOS — chỉ ở `Final_app/EdgeMiner*`.
