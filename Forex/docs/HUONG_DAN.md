# Hướng dẫn sử dụng PARL

**Price Action Research Lab** — nền tảng nghiên cứu Price Action chạy hoàn toàn trên trình duyệt.

> Đây **không phải** bot giao dịch. PARL giúp trader PA trả lời: *setup nào, cặp/khung nào, tham số nào có edge thật sau spread* — trước khi risk tiền thật.

## PARL giải quyết vấn đề gì?

| Vấn đề | Cách app hỗ trợ |
|--------|-----------------|
| Không biết setup nào có edge | Strategies scan + Simulation backtest |
| Dễ tự lừa khi xem chart | Replay bar-by-bar; kiểm chứng signal trên Chart |
| Quá nhiều signal | AI Signals chấm điểm, lọc Min score |
| Tối ưu tham số thiếu kiểm định | Optimizer: walk-forward, Monte Carlo |
| Công cụ rời rạc | Data, chart, backtest, báo cáo trong một app local |

**PARL không** kết nối broker, không đặt lệnh live, không thay journal hay quản lý tâm lý.

Chi tiết từng màn hình: trong app bấm **Ctrl+9** hoặc **F1**, hoặc nút 📖 trên từng view.

## Cài đặt & chạy

```bash
cd Forex
python3 -m http.server 8080
```

Mở trình duyệt: **http://localhost:8080**

Lần đầu: vào **Data Manager (Ctrl+2)** → Reload Default Data hoặc Import CSV.

---

## Quy trình nghiên cứu khuyến nghị

| Bước | Thao tác | Phím tắt |
|------|----------|----------|
| 1 | Import / tạo dữ liệu nến | Ctrl+2 |
| 2 | Chạy scan chiến lược | Ctrl+3 |
| 3 | Backtest với trade engine | Ctrl+4 |
| 4 | Xem thống kê hiệu suất | Ctrl+5 |
| 5 | Dashboard, heatmap, export | Ctrl+6 |
| 6 | Tối ưu tham số / walk-forward / Monte Carlo | Ctrl+7 |
| 7 | Xem điểm AI từng signal | Ctrl+8 |

---

## Từng module

### Data Manager (Ctrl+2)

- Import file CSV, JSON hoặc `.gz`
- Export dữ liệu để backup
- Cập nhật / Xóa theo Symbol + TF đã chọn
- Dữ liệu lưu trong **IndexedDB** (local, không gửi server)

**Định dạng CSV:**
```
timestamp,datetime,open,high,low,close,volume
```

### Chart (Ctrl+1)

- Biểu đồ nến + EMA 20/50
- **Replay** từng nến — không bao giờ lộ nến tương lai
- Dataset lớn: chart hiển thị tối đa 50.000 nến gần nhất

**Phím replay (khi đang ở Chart):**

| Phím | Chức năng |
|------|-----------|
| Space | Play / Pause |
| → | Nến tiếp theo |
| ← | Nến trước |
| Home | Reset replay |
| End | Xem toàn bộ (live) |

### Strategies (Ctrl+3)

Ba setup Price Action (chi tiết trong `docs/STRATEGY_SPECIFICATION.md`):

| ID | Tên |
|----|-----|
| `break-retest` | Break & Retest |
| `ema-pullback` | EMA Pullback |
| `liquidity-grab` | Liquidity Grab |

- Chỉnh tham số từng strategy
- **Run Selected** — scan một strategy
- **Run All Enabled** — scan tất cả strategy đang bật

### Simulation (Ctrl+4)

Backtest Mode 1: một setup, một cặp, một timeframe.

Cấu hình: spread, slippage, lot size, trailing stop, break-even, partial close.

Kết quả tự cập nhật Statistics và Reports.

### Statistics (Ctrl+5)

Expectancy, profit factor, max drawdown, Sharpe, streaks, equity curve, drawdown chart.

### Reports (Ctrl+6)

- **Dashboard:** tóm tắt + equity curve
- **Heatmaps:** theo tháng, ngày, giờ, session, strategy, pair, timeframe
- **Export:** CSV, JSON, PNG, Print/PDF

### Optimizer (Ctrl+7)

**Mục đích:** tìm cài đặt tốt (Grid Search), tránh “học vẹt” quá khứ (Walk Forward), xem chuỗi thua có thể làm tài khoản tệ cỡ nào (Monte Carlo).

Chi tiết từng tab và **từ điển thuật ngữ** (Overfit, Iterations, Ruin Rate…): trong app **Ctrl+9** → mục **Optimizer** hoặc **Từ điển thuật ngữ**, hoặc nút 📖 khi đang ở Optimizer.

| Tab | Làm gì (nói đơn giản) | Cần trước |
|-----|------------------------|-----------|
| Grid Search | Thử nhiều combo cài đặt, xếp hạng theo lãi/lệnh, PF… | Data + Symbol/TF |
| Walk Forward | Lãi đoạn cũ có còn ở đoạn mới ngay sau không | Save Parameters sau Grid |
| Monte Carlo | Xáo thứ tự lệnh — xem kịch bản xấu (P5) và % gần cháy (Ruin Rate) | Simulation (Ctrl+4) |

Grid/Walk Forward dùng spread & lot từ **Simulation**. Tối đa **500** combo mỗi lần Grid Search.

### AI Signals (Ctrl+8)

Mỗi signal được chấm **0–100** sau khi scan.

8 yếu tố: trend, momentum, location, volatility, PA quality, RR, session, spread.

Lọc signal bằng thanh trượt **Min score**.

---

## Phím tắt

| Phím | Chức năng |
|------|-----------|
| Ctrl+B | Ẩn/hiện sidebar |
| Ctrl+1 → Ctrl+8 | Chuyển view |
| Ctrl+9 / F1 | Tài liệu hướng dẫn |

---

## Lưu trữ dữ liệu

| Nơi lưu | Nội dung |
|---------|----------|
| IndexedDB | Nến OHLCV |
| LocalStorage | Cài đặt, tham số strategy, kết quả simulation |

Xóa dữ liệu site trong trình duyệt = reset toàn bộ. Nên export kết quả trước khi xóa.

---

## Xử lý sự cố

| Vấn đề | Cách xử lý |
|--------|------------|
| Chart trống | Reload Default Data hoặc Import ở Data Manager |
| Statistics trống | Chạy Simulation (Ctrl+4) trước |
| Monte Carlo lỗi | Cần có kết quả Simulation |
| Grid search chậm | Giảm số tổ hợp tham số |
| Lỗi `#log` / private field khi boot | Copy lại code mới nhất. Dùng Chrome/Edge/Firefox mới. Chạy qua `http://` không mở `file://` |

---

## Tài liệu thêm

- `docs/USAGE.md` — English usage guide
- `docs/STRATEGY_SPECIFICATION.md` — đặc tả chiến lược
- Trong app: **Ctrl+9** hoặc **F1**
