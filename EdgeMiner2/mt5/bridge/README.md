# MT5 Bridge — App quyết định, EA execute

> **MT5** (MetaTrader 5), không phải MT4.

## GUI

Trong app: sidebar **MT5 Bridge**

- Start/Stop service — mặc định **process riêng** (`scripts/mt5_bridge_service.py`)
  - Đổi tab / refresh Streamlit **không** dừng service
  - Tắt khi bấm Stop, hoặc kill PID trong `results/mt5_bridge_service.pid`
- Chọn Trade Model (mặc định Best 3m)
- Xem snapshot `bar.json` / `decision.json` / `fill.json`
- **Nhật ký giao tiếp** `comm_log.jsonl` (EA→App bar/fill, App→EA decision)
- **Thống kê lệnh** `trades.json` (thắng/thua, R)

### Remine hàng tuần

Khi **Start service**: mỗi tuần ISO mới App tự `optimize_on_window` theo Trade Model đang chọn (train months + KB).  
**Không** cần chạy lại Grid Search mỗi tuần. Chỉ đổi Trade Model / học KB / Grid khi muốn cập nhật cấu hình model.

## Flow Live

```
MT5 ForgeBridge (Live)
  → ghi MQL5/Files/bridge/bar.json
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
