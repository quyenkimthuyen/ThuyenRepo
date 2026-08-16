# MT5 Bridge — App quyết định, EA execute

> **MT5** (MetaTrader 5), không phải MT4.

## So sánh kênh (đừng nhầm tên “paper”)

| | **Compare Trade** | **Simulate** (HistoryFeed) | **Live** (trang này) |
|---|---|---|---|
| Lệnh | *Sim fills* Python (`PaperBook`) trên cache M15 | App↔EA replay nến lịch sử | EA mở/đóng trên tài khoản |
| File | `results/compare_runs/…` | `bridge_sim/trades.json` | `decision.json` + `trades.json` |
| EA | Không | Có (`HISTORY_FEED`) | Có (`Live`) |
| Tiền | Không | Không | Demo/live trên MT5 |

Desk **Paper Monitor** (GUI cũ, `paper_monitor_state.json`, port chart `8976`) đã **gỡ**.  
Module/code còn tên `paper_*` / `PaperBook` chỉ là helper khớp lệnh mô phỏng cho Compare/HistoryFeed — **không** phải trang Giám sát paper.

**Active ≠ Bridge:** dropdown Trade Models = phân tích. Roster Live/Sim chọn trên tab **Trade Models · Bridge** trong GUI.

## GUI

Trong app: sidebar **MT5 Bridge** — switch **Live | Simulate** (cùng desk/chart/thống kê/sức khỏe; khác `bridge_m5e31/` vs `bridge_sim_m5e31/`)

- Start/Stop service — mặc định **process riêng** (`scripts/mt5_bridge_service.py`)
  - Đổi tab / refresh Streamlit **không** dừng service
  - Tắt khi bấm Stop, hoặc kill PID trong `results/mt5_bridge_service.pid`
- Chọn **1–5 Trade Model** (roster Bridge; không gồm model Archived)
- Chart M15 live, heartbeat, Bid/Ask, spread và lệnh từ chính ForgeBridge EA
- Cảnh báo **id ma** nếu roster còn id đã Archive/xóa → nút **Dọn roster**
- Xem snapshot `connection.json` / `bars.json` / `bar.json` / `decision.json` / `fill.json`
- **Kiểm tra bridge (market ngay)** — nút BUY/SELL/CLOSE ghi `command.json` (EA v1.03+ xử lý ngay trên tick, không chờ nến đóng)
- **Nhật ký giao tiếp** `comm_log.jsonl` (EA→App bar/fill, App→EA decision)
- **Thống kê lệnh** `trades.json` (thắng/thua, R)
- **Mode Auto vs Lệnh sửa** — EA v1.04 đồng bộ sửa/đóng tay (`modify`/`manual_close`); thống kê tách để review chiến lược công bằng (R theo SL kế hoạch)
- **Simulate EA (History Feed)** — ForgeBridge **v1.05** `InpMode = HISTORY_FEED`, `InpBridgeSubdir = bridge_sim_m5e31`; App ghi `sim_control.json` (from/to/delay); EA `CopyRates` gửi bar/fill như live

## Deploy / cập nhật XM Global MT5 (Windows)

Script tự tìm XM Global MT5 và Data Folder, copy + compile EA, kiểm tra
`MQL5/Files/bridge` junction, reload XM terminal và restart Bridge service:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1
```

Lần đầu cần tự gắn vào chart EURUSD M5:

```powershell
# Gắn để test, không cho đặt lệnh
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Attach

# Thay EA trên chart và bật giao dịch
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Attach -EnableTrading

# Simulate (HISTORY_FEED + bridge_sim, chart riêng)
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Mode HistoryFeed -Attach
```

Sau này khi sửa `mt5/Experts/ForgeBridgeM5E31.mq5`, chỉ chạy lệnh đầu tiên. Script
idempotent và không thay chart nếu ForgeBridge đã được gắn.
Chỉ dùng `-NoRestartTerminal` khi muốn compile mà chưa nạp EA mới vào chart.

### Remine hàng tuần

Khi **Start service**: mỗi tuần ISO mới App tự `optimize_on_window` theo **từng model trong Bridge roster** (train weeks + KB pin).  
**Không** cần Grid mỗi tuần. Chỉ Archive/đổi roster / học KB / Grid khi muốn cập nhật “bộ não”.

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
- Cần tài khoản **hedging**. Compile lại `ForgeBridgeM5E31` / `ForgeBridgeM5E31Sim` sau khi kéo code mới.
- Live Trade dashboard: KPI tổng + bảng từng model.

## History Feed (Simulate EA)

1. Biên dịch lại ForgeBridge **1.05**, gắn EURUSD M5 (demo khuyến nghị).
2. Inputs: `InpMode = HISTORY_FEED`, `InpBridgeSubdir = bridge_sim_m5e31` (junction/Files giống live).
3. App **MT5 Bridge → Simulate EA**: chọn from/to + delay → Start feed.
4. Service quyết định chạy trên `mt5/bridge_sim_m5e31/` (không đụng `bridge_m5e31/` live).

## Thống kê lệnh

GUI **MT5 Bridge → Thống kê lệnh Bridge**: số thắng/thua, WR%, Total R, Avg R, Max DD, bảng chi tiết từng lệnh.

Cần EA `ForgeBridge` bản mới (ghi `event=open|close` trong `fill.json`).
