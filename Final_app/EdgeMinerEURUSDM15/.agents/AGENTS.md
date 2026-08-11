# Project Rules & Customizations

- **Sim fills ≠ MT5 orders**: Trạng thái `SIGNAL` / `FILLED` từ Compare Trade / HistoryFeed (`PaperBook` / `paper_fill`) **KHÔNG** đồng nghĩa lệnh đã vào MT5. Chỉ xác nhận lệnh MT5 qua **Thống kê lệnh Bridge** hoặc `trades.json` / positions của Bridge Live.
- **Paper Monitor retired**: Không còn desk Giám sát paper trên nav. Code/module tên `paper_*` còn lại là helper nội bộ hoặc stub redirect.
- **Active ≠ Bridge**: Active = phân tích; Bridge roster = runtime Live/Sim. Archive/xóa phải prune `model_ids`.
