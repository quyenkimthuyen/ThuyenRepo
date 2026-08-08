# MT5 Bridge — App quyết định, EA execute

> **MT5** (MetaTrader 5), không phải MT4.

## Paper Trade vs Bridge

| | **Giám sát paper** | **MT5 Bridge** (trang này) |
|---|---|---|
| Lệnh | Mô phỏng trên nến | EA mở/đóng trên tài khoản |
| File | `results/paper_monitor_state.json` | `decision.json` + `trades.json` |
| Thống kê | Desk tuần (WR, R, DD, nhật ký) | Fill thật từ EA |
| `SIGNAL` | Tín hiệu mô phỏng chưa khớp | Phải gửi `BUY`/`SELL` lúc bar đóng |

Cùng Trade Model + cùng cache M15. Paper **không** thay thế Bridge — dùng để kiểm tra trước/live song song.

## GUI

Trong app: sidebar **MT5 Bridge** — switch **Live | Simulate** (cùng desk/chart/thống kê/sức khỏe; khác `bridge/` vs `bridge_sim/`)

- Start/Stop service — mặc định **process riêng** (`scripts/mt5_bridge_service.py`)
  - Đổi tab / refresh Streamlit **không** dừng service
  - Tắt khi bấm Stop, hoặc kill PID trong `results/mt5_bridge_service.pid`
- Chọn Trade Model (mặc định Best 3m)
- Chart M15 live, heartbeat, Bid/Ask, spread và lệnh từ chính ForgeBridge EA
- Xem snapshot `connection.json` / `bars.json` / `bar.json` / `decision.json` / `fill.json`
- **Kiểm tra bridge (market ngay)** — nút BUY/SELL/CLOSE ghi `command.json` (EA v1.03+ xử lý ngay trên tick, không chờ nến đóng)
- **Nhật ký giao tiếp** `comm_log.jsonl` (EA→App bar/fill, App→EA decision)
- **Thống kê lệnh** `trades.json` (thắng/thua, R)
- **Mode Auto vs Lệnh sửa** — EA v1.04 đồng bộ sửa/đóng tay (`modify`/`manual_close`); thống kê tách để review chiến lược công bằng (R theo SL kế hoạch)
- **Simulate EA (History Feed)** — ForgeBridge **v1.05** `InpMode = HISTORY_FEED`, `InpBridgeSubdir = bridge_sim`; App ghi `sim_control.json` (from/to/delay); EA `CopyRates` gửi bar/fill như live

## Deploy / cập nhật XM Global MT5 (Windows)

Script tự tìm XM Global MT5 và Data Folder, copy + compile EA, kiểm tra
`MQL5/Files/bridge` junction, reload XM terminal và restart Bridge service:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1
```

Lần đầu cần tự gắn vào chart BTCUSD M15:

```powershell
# Gắn để test, không cho đặt lệnh
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Attach

# Thay EA trên chart và bật giao dịch
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Attach -EnableTrading

# Simulate (HISTORY_FEED + bridge_sim, chart riêng)
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Mode HistoryFeed -Attach
```

Sau này khi sửa `mt5/Experts/ForgeBridgeM15.mq5`, chỉ chạy lệnh đầu tiên. Script
idempotent và không thay chart nếu ForgeBridge đã được gắn.
Chỉ dùng `-NoRestartTerminal` khi muốn compile mà chưa nạp EA mới vào chart.

### Remine hàng tuần

Khi **Start service**: mỗi tuần ISO mới App tự `optimize_on_window` theo Trade Model đang chọn (train months + KB).  
**Không** cần chạy lại Grid Search mỗi tuần. Chỉ đổi Trade Model / học KB / Grid khi muốn cập nhật cấu hình model.

## Flow Live

```
MT5 ForgeBridge (Live)
  → ghi connection.json + bars.json cho chart live
  → ghi bar.json khi có nến M15 mới
App service
  → remine Best 3m / quyết định
  → ghi decision.json (+ comm_log)
EA
  → BUY/SELL hoặc FLAT/HOLD
  → ghi fill.json
```

Mount Docker: `mt5/bridge` ↔ `/mt5_bridge` ↔ `MQL5/Files/bridge` (`./mt5/run_mt5.sh start`).

## CLI (không cần GUI)

```bash
python scripts/mt5_bridge_service.py
# hoặc một lần:
python scripts/mt5_bridge_service.py --once
```

## Replay / so sánh Strategy Tester

Giữ song song:

| EA | Nguồn quyết định |
|----|------------------|
| `ForgeBest3m_Frozen` | Rules tĩnh |
| `ForgeBest3m_WF` | Lịch WF nhúng |
| `ForgeBridge` Replay | `replay_signals.csv` từ App |

```bash
python scripts/export_bridge_replay.py
./mt5/run_mt5.sh sync_bridge
# Tester: ForgeBridge · InpMode = Replay
```

## Files

| File | Writer |
|------|--------|
| `connection.json` | EA (heartbeat, tick, nến hiện tại, trạng thái trading) |
| `bars.json` | EA (1344 nến M15 cho chart) |
| `bar.json` | EA |
| `decision.json` | App (primary model mirror) |
| `models.json` | App → EA roster (`model_id`↔magic, shared `risk_pct`) |
| `decisions/<model_id>.json` | App (một file quyết định / model) |
| `fill.json` | EA (open/close + ticket/price/profit + `model_id`/`magic`) |
| `trades.json` | App journal (lệnh + R thắng/thua) |
| `fills.jsonl` | App (raw fill history) |
| `status.json` | App |
| `comm_log.jsonl` | App (log giao tiếp) |
| `sim_control.json` | App→EA HistoryFeed (`enabled`/`from`/`to`/`delay_ms`); EA cập nhật `ea_status`/`bars_*` |
| `replay_decisions.json` / `replay_signals.csv` | export script |

## Multi-model (Live + Simulate)

- App chọn 1–5 Trade Model; **Risk % / lệnh chung** (tổng rủi ro ≈ N× nếu mở đồng thời).
- Mỗi model một magic (`base + index`); tối đa **1 lệnh mở / magic**.
- Cần tài khoản **hedging**. Compile lại `ForgeBridgeM15` / `ForgeBridgeM15Sim` sau khi kéo code mới.
- Live Trade dashboard: KPI tổng + bảng từng model.

## History Feed (Simulate EA)

1. Biên dịch lại ForgeBridge **1.05**, gắn BTCUSD M15 (demo khuyến nghị).
2. Inputs: `InpMode = HISTORY_FEED`, `InpBridgeSubdir = bridge_sim` (junction/Files giống live).
3. App **MT5 Bridge → Simulate EA**: chọn from/to + delay → Start feed.
4. Service quyết định chạy trên `mt5/bridge_sim/` (không đụng `bridge/` live).

## Thống kê lệnh

GUI **MT5 Bridge → Thống kê lệnh Bridge**: số thắng/thua, WR%, Total R, Avg R, Max DD, bảng chi tiết từng lệnh.

Cần EA `ForgeBridge` bản mới (ghi `event=open|close` trong `fill.json`).
