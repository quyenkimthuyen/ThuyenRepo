# Live Trade App

Import `.tmpkg` từ lab → roster → **1 EA chung** `ForgeBridgeLive` → remine tuần tại chỗ (KB pin trong package).

## UI (trader desk)

Mở app → nav **Replay | Live | Models | Setup**:
- **Replay / Live** — desk giao dịch (cockpit + History)
- **Models** — import / delete / roster
- **Setup** — runtime, risk, autostart, reset

Auto-refresh trong sidebar.

Modules: `gui/app.py`, `gui/theme.py`, `desk_snapshot.py`.

Magic / port: base **`20283001`**, UI **`8801`**, monitor **`9801`**.

## Linux Simulate / Replay (no MT5)

**Mặc định (khuyến nghị): schedule-parity** — replay genome đóng băng từng tuần
bằng `backtest_mined` (cùng path lab Health/OOS). Kết quả R/WR khớp lab khi
package có `schedule.json`.

```bash
cd /home/thuyenng/work/ThuyenRepo/Final_app/split_app
# UI Start OOS replay → parity; hoặc:
../../EdgeMinerM15B5/.venv/bin/python live/scripts/run_parity_oos_batch.py
# Kết quả: live/results/parity_oos_batch.json · parity_<sym>_<tf>.json
```

**Paper path (EA protocol smoke)** — bar → decision → paper fill:

```bash
LIVE_REPLAY_MODE=paper ../../EdgeMinerM15B5/.venv/bin/python live/scripts/run_oos_replay_batch.py
```

Multi symbol/TF: roster bật nhiều model → mỗi book (symbol+TF) chạy worker/bridge
riêng; nhiều model cùng book dùng magic riêng (`20283001+` live / `20284001+` sim).

**Bắt buộc cho parity / Live:** `.tmpkg` phải kèm `schedule.json` (weekly genomes).
Thiếu schedule → **export FAIL**, **import REJECT**, roster **không cho On**.

```bash
# Lab: freeze schedule rồi đóng gói
cd Final_app/EdgeMinerEURUSDM15
../../EdgeMinerM15B5/.venv/bin/python scripts/export_model_schedule.py --model-id tm_...
cd ../split_app
../../EdgeMinerM15B5/.venv/bin/python lab/export_trade_package.py --desk EdgeMinerEURUSDM15 --model-id tm_...
# hoặc một lệnh (auto-freeze nếu thiếu):
../../EdgeMinerM15B5/.venv/bin/python lab/export_trade_package.py --desk EdgeMinerEURUSDM15 --model-id tm_... --ensure-schedule

# Live: audit installed
../../EdgeMinerM15B5/.venv/bin/python live/import_trade_package.py --audit

# Backfill schedules for desks / sync into packages:
../../EdgeMinerM15B5/.venv/bin/python Final_app/ensure_live_schedules.py --from-live-roster
# chỉ sync schedule lab → installed packages:
../../EdgeMinerM15B5/.venv/bin/python Final_app/ensure_live_schedules.py --from-live-roster --sync-packages-only
```

Live/Sim luôn **recompute train window** theo `week_start` (không dùng
`train_*_idx` cũ trong schedule — index tuyệt đối lệch khi parquet đổi).

## Reset data

UI **Setup → Reset data** (gõ `RESET`) hoặc CLI:

```bash
cd /home/thuyenng/work/ThuyenRepo/Final_app/split_app/live
# full wipe incl. packages + roster:
../../EdgeMinerM15B5/.venv/bin/python scripts/reset_live_data.py --yes
# giữ packages/roster, wipe journal/sim/cache rồi re-seed OHLC:
../../EdgeMinerM15B5/.venv/bin/python scripts/reset_live_data.py --yes --keep-packages
```

Windows + MT5 thật vẫn dùng EA `ForgeBridgeLive` / `ForgeBridgeLiveSim` như cũ.

**EA Simulate (Replay tab):** App ghi `sim_control.json` (OOS from/to) → `ForgeBridgeLiveSim` HistoryFeed báo nến → worker `--sim` quyết định cùng Live → EA paper fill. Không `OrderSend`, không đụng `bridge_live_*`.

**EA chart Comment (v1.10+):** mỗi nến đóng hiện sync status trên chart + Experts log
(`SYNC OK` / `TIMEOUT`) và ghi `ea_sync.json` để Live **Pipeline health** đối chiếu.
Tắt: input `InpShowComment=false`. Cần re-deploy/compile EA trên Windows.

**Windows autostart (mặc định theo Start/Stop trading):**
- **Start trading** → gắn Scheduled Task (reboot: MT5 + Live app + bridge)
- **Stop / Kill** → gỡ task

```powershell
# Task được Start/Stop quản lý; kiểm tra thủ công:
.\live\scripts\install_autostart_windows.ps1 -Action Status
.\live\scripts\boot_autostart_windows.ps1 -DelaySec 2
```

Tắt gắn/gỡ tự động: `LIVE_SKIP_AUTOSTART=1`.

```powershell
.\live\scripts\deploy_live_ea.ps1 -FromRoster -SkipBridgeService
.\live\scripts\deploy_live_ea.ps1 -Symbol EURUSD -Timeframe M5
```

## Commands

```bash
cd /home/thuyenng/work/ThuyenRepo/Final_app/split_app

# Import
python live/import_trade_package.py packages_out/some.tmpkg
python live/import_trade_package.py --list
python live/import_trade_package.py --delete M15_EURUSD_tm_example

# Roster → models.json
python live/sync_bridge_roster.py

# Smoke (no MT5 required for most checks)
../../EdgeMinerM15B5/.venv/bin/python live/scripts/smoke_live.py

# Windows Live E2E (app HTTP + desk + safety + deploy PARSE)
# From split_app on Windows:
.\live\scripts\test_live_windows.ps1
.\live\scripts\test_live_windows.ps1 -WithDeploy          # optional: deploy -NoAttach
.\live\scripts\test_live_windows.ps1 -WithBridgeOnce      # optional: service --once
# Or:
python live/scripts/test_live_windows.py

# Bridge service
../../EdgeMinerM15B5/.venv/bin/python -c "import bridge_control; print(bridge_control.start_bridge())"
# stop:
../../EdgeMinerM15B5/.venv/bin/python -c "import bridge_control; bridge_control.stop_bridge(flatten=True)"

# UI
./live/scripts/run_app_linux.sh Start
# http://127.0.0.1:8801
```

Windows:

```powershell
.\live\scripts\run_app_windows.ps1 -Action Start
.\live\scripts\deploy_live_ea.ps1 -FromRoster   # all enabled books; also auto on Live Start
.\live\scripts\deploy_live_ea.ps1 -Symbol EURUSD -Timeframe M5 -Mode Both
```

## Remine

Package mang **recipe** (search space + KB pin). Mỗi tuần service gọi `optimize_on_window` trên data broker — **không** cần re-export từ lab.

Enabled roster phải **cùng symbol+TF** (một chart / một EA). Mixed books → chart/EA riêng.

## Không có trong Live

KB learning, Grid, promote, unify OOS — chỉ ở `Final_app/EdgeMiner*`.
