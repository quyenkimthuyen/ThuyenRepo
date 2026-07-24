# MT5 Bridge — App quyết định, EA execute

> **MT5** (MetaTrader 5), không phải MT4.

## Paper Trade vs Bridge

| | **Giám sát paper** | **MT5 Bridge** (trang này) |
|---|---|---|
| Lệnh | Mô phỏng trên nến | EA mở/đóng trên tài khoản |
| File | `results/paper_monitor_state.json` | `decision.json` + `trades.json` |
| Thống kê | Desk tuần (WR, R, DD, nhật ký) | Fill thật từ EA |
| `SIGNAL` | Tín hiệu mô phỏng chưa khớp | Phải gửi `BUY`/`SELL` lúc bar đóng |

Cùng Trade Model + cùng cache H1. Paper **không** thay thế Bridge.

## GUI

Trong app: sidebar **MT5 Bridge**

- Start/Stop service — mặc định **process riêng** (`scripts/mt5_bridge_service.py`)
  - Đổi tab / refresh Streamlit **không** dừng service
  - Tắt khi bấm Stop, hoặc kill PID trong `results/mt5_bridge_service.pid`
- Chọn Trade Model (mặc định Best 3m)
- Chart H1 live, heartbeat, Bid/Ask, spread và lệnh từ chính ForgeBridge EA
- Xem snapshot `connection.json` / `bars.json` / `bar.json` / `decision.json` / `fill.json`
- **Kiểm tra bridge (market ngay)** — nút BUY/SELL/CLOSE ghi `command.json` (EA v1.03+ xử lý ngay trên tick, không chờ nến đóng)
- **Nhật ký giao tiếp** `comm_log.jsonl` (EA→App bar/fill, App→EA decision)
- **Thống kê lệnh** `trades.json` (thắng/thua, R)

## Deploy / cập nhật XM Global MT5 (Windows)

Script tự tìm XM Global MT5 và Data Folder, copy + compile EA, kiểm tra
`MQL5/Files/bridge` junction, reload XM terminal và restart Bridge service:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1
```

Lần đầu cần tự gắn vào chart EURUSD H1:

```powershell
# Gắn để test, không cho đặt lệnh
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Attach

# Thay EA trên chart và bật giao dịch
powershell -ExecutionPolicy Bypass -File scripts/deploy_xm_forgebridge.ps1 -Attach -EnableTrading
```

Sau này khi sửa `mt5/Experts/ForgeBridge.mq5`, chỉ chạy lệnh đầu tiên. Script
idempotent và không thay chart nếu ForgeBridge đã được gắn.
Chỉ dùng `-NoRestartTerminal` khi muốn compile mà chưa nạp EA mới vào chart.

### Remine hàng tuần

Khi **Start service**: mỗi tuần ISO mới App tự `optimize_on_window` theo Trade Model đang chọn (train months + KB).  
**Không** cần chạy lại Grid Search mỗi tuần. Chỉ đổi Trade Model / học KB / Grid khi muốn cập nhật cấu hình model.

## Flow Live

```
MT5 ForgeBridge (Live)
  → ghi connection.json + bars.json cho chart live
  → ghi bar.json khi có nến H1 mới
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
| `bars.json` | EA (336 nến H1 cho chart) |
| `bar.json` | EA |
| `decision.json` | App |
| `fill.json` | EA (open/close + ticket/price/profit) |
| `trades.json` | App journal (lệnh + R thắng/thua) |
| `fills.jsonl` | App (raw fill history) |
| `status.json` | App |
| `comm_log.jsonl` | App (log giao tiếp) |
| `replay_decisions.json` / `replay_signals.csv` | export script |

## Thống kê lệnh

GUI **MT5 Bridge → Thống kê lệnh Bridge**: số thắng/thua, WR%, Total R, Avg R, Max DD, bảng chi tiết từng lệnh.

Cần EA `ForgeBridge` bản mới (ghi `event=open|close` trong `fill.json`).
