# Project Rules & Customizations

- **Paper Execution vs. MT5 Real Orders**: Trạng thái `SIGNAL` / `FILLED` trong Paper Trading/Monitor **KHÔNG** đồng nghĩa với việc lệnh đã được đặt thành công trên MT5. Chỉ xác nhận lệnh đã vào MT5 dựa trên **Thống kê lệnh Bridge** hoặc file `trades.json` / `positions` trực tiếp của Bridge.
