# Hướng dẫn sử dụng PARL

**Price Action Research Lab** — nền tảng nghiên cứu Price Action chạy hoàn toàn trên trình duyệt.

> Đây **không phải** bot giao dịch. PARL giúp trader PA trả lời: *setup nào, cặp/khung nào, tham số nào có edge thật sau spread* — trước khi risk tiền thật.

## PARL giải quyết vấn đề gì?

| Vấn đề | Cách app hỗ trợ |
|--------|-----------------|
| Không biết setup nào có edge | Strategies scan + **Compare** + Simulation backtest |
| Dễ tự lừa khi xem chart | Replay bar-by-bar; kiểm chứng signal trên Chart |
| Quá nhiều signal | AI Signals chấm điểm; Simulation lọc theo Min score |
| Tối ưu tham số thiếu kiểm định | Optimizer: grid + **auto walk-forward**, Monte Carlo |
| Công cụ rời rạc | Data, chart, backtest, báo cáo trong một app local |

**PARL không** kết nối broker, không đặt lệnh live, không thay journal hay quản lý tâm lý.

Chi tiết từng màn hình: trong app bấm **Ctrl+0** hoặc **F1**, hoặc nút 📖 trên từng view.

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
| 3 | So sánh nhiều setup cùng cặp/TF | Ctrl+4 |
| 4 | Backtest với trade engine (+ lọc AI tuỳ chọn) | Ctrl+5 |
| 5 | Xem thống kê hiệu suất | Ctrl+6 |
| 6 | Dashboard, heatmap, export | Ctrl+7 |
| 7 | Tối ưu tham số / walk-forward / Monte Carlo | Ctrl+8 |
| 8 | Xem điểm AI từng signal | Ctrl+9 |

---

## Từng module

### Data Manager (Ctrl+2)

- Import file CSV, JSON hoặc `.gz`
- Export dữ liệu để backup
- Cập nhật / Xóa theo Symbol + TF đã chọn
- Dữ liệu nến lưu trong **IndexedDB** (local, không gửi server)

**Định dạng CSV:**
```
timestamp,datetime,open,high,low,close,volume
```

### Chart (Ctrl+1)

- Biểu đồ nến + EMA 20/50
- **Replay** từng nến — không bao giờ lộ nến tương lai
- **Jump to date** — ô ngày giờ theo **UTC** (khớp timestamp nến)
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

Tám setup Price Action (chi tiết trong `docs/STRATEGY_SPECIFICATION.md` và **Ctrl+0 → Strategies**):

| ID | Tên |
|----|-----|
| `break-retest` | Break & Retest |
| `ema-pullback` | EMA Pullback |
| `liquidity-grab` | Liquidity Grab |
| `session-liquidity-sweep` | Session Liquidity Sweep (Asian range, London/overlap) |
| `inside-bar-breakout` | Inside Bar Breakout |
| `pin-bar-rejection` | Pin Bar Rejection |
| `wyckoff-spring-utad` | Wyckoff Spring / UTAD |
| `wyckoff-range-test` | Wyckoff Range Test |

- Chỉnh tham số từng strategy → **Save Parameters**
- **Run Selected** / **Run All Enabled**

#### Session Liquidity Sweep (`session-liquidity-sweep`) — tóm tắt

Chiến lược session cho **EURUSD H1** (chạy được symbol/TF khác):

1. **Pha sweep** — quét Asian high/low, London morning, hoặc swing; close quay lại trong vùng; râu rejection.
2. **Pha confirm** — 1–2 nến sau: nến xác nhận fade, không phá đỉnh/đáy sweep → entry.
3. **Lọc** — chỉ 06–20 UTC; `minVolatilityRatio` (mặc định 0.95); tùy chọn prev Asian range.

| Param chính | Mặc định |
|-------------|----------|
| grabPips | 5 |
| wickRatio | 0.65 |
| confirmMaxBars | 2 |
| rr | 1.5 |
| session | 06–20 UTC |

Khác **Liquidity Grab**: entry 2 pha, nhiều nguồn level, lọc phiên/vol. Chi tiết đầy đủ: `STRATEGY_SPECIFICATION.md` §10.

### Compare (Ctrl+4)

Chạy nhiều strategy trên **cùng Symbol + TF**, xếp hạng theo **expectancy**.

- Tick bỏ strategy không muốn so
- Bấm **Compare** — mỗi setup được scan + mô phỏng lệnh (dùng spread/lot từ Simulation)
- Hàng tốt nhất được highlight

Dùng trước khi chọn một setup “chính” hoặc trước khi tối ưu tham số sâu.

### Simulation (Ctrl+5)

**Run Simulation** = quét lại strategy + mô phỏng lệnh (spread, slippage, trailing…).

**Lọc AI (tuỳ chọn):**
- Bật **AI score filter**, đặt **Min score** (mặc định 65)
- Chỉ mô phỏng signal có điểm ≥ ngưỡng
- **Compare vs all signals** — so sánh song song: toàn bộ signal vs đã lọc (WR, Net, Exp)
- Bảng lệnh chính dùng bộ **đã lọc** khi bật filter

Cấu hình: spread, slippage, lot size, trailing stop, break-even, partial close.

Kết quả tự cập nhật Statistics và Reports.

### Statistics (Ctrl+6)

Expectancy, profit factor, max drawdown, Sharpe, streaks, equity curve, drawdown chart.

### Reports (Ctrl+7)

- **Dashboard:** tóm tắt + equity curve
- **Heatmaps:** theo tháng, ngày, giờ, session, strategy, pair, timeframe
- **Export:** CSV, JSON, PNG, Print/PDF

### Optimizer (Ctrl+8)

| Tab | Làm gì | Ghi chú |
|-----|--------|---------|
| **Grid Search** | Thử nhiều combo, xếp hạng | **Suggest from data**, **Restore defaults**, giữ input khi đổi tab |
| **Sensitivity** | Biểu đồ WR / Exp / Net theo từng param | Chỉ param đã tick trong grid lần chạy gần nhất |
| Walk Forward | IS vs OOS theo từng fold | Dùng tham số đang Save trong Strategies |
| Monte Carlo | Xáo thứ tự lệnh | Cần Simulation trước |

Tối đa **500** combo mỗi lần Grid Search. Kết quả lưu IndexedDB — không còn lỗi quota localStorage.

#### Grid Search — thao tác mới

| Nút / tính năng | Mô tả |
|-----------------|--------|
| **Suggest from data** | Đọc nến hiện tại (avg range 14 nến + khung thời gian) → gợi ý lưới giá trị và tick sẵn 2–3 param quan trọng + `rr` |
| **Restore defaults** | Khôi phục lưới mặc định (default ± 1 bước), chỉ tick `rr`, rank = expectancy |
| **Apply best to Strategy** | Sau khi chạy grid — lưu combo #1 vào Strategies (Ctrl+3) |
| **Giữ form khi đổi tab** | Tick param, ô giá trị, Rank by, Auto WF được nhớ theo từng strategy trong phiên (reload trang thì mất) |

Grid Search chạy **song song** trên Web Workers (4 luồng) khi ≥ 4 combo và workers khả dụng — header kết quả hiện `(parallel)`.

#### Tab Sensitivity

- Mở sau **Run Grid Search** — dữ liệu lấy từ kết quả grid (lưu `optimizedParamKeys` + `paramGrid`).
- Dropdown **Parameter**: chỉ các param đã đưa vào lưới grid.
- Checkbox **WR / Exp / Net**: bật/tắt từng đường trên biểu đồ.
- Trục trái: Win Rate % · Trục phải: $ (Expectancy và/hoặc Net Profit).
- **Net Profit** phụ thuộc số lệnh — so sánh cùng cột Trades trong Top Results.
- Ẩn điểm có trung bình &lt; 5 lệnh/combo.

#### Quy trình khuyến nghị

1. Grid Search → (tuỳ chọn) Suggest from data → Run  
2. Tab **Sensitivity** → xem param nào ổn  
3. **Apply best to Strategy** hoặc copy từ Top Results  
4. Walk Forward / Simulation / Monte Carlo như trước

#### Cập nhật Optimizer (28/06/2025)

- Tab **Sensitivity** tách riêng khỏi Top Results  
- **Suggest from data**, **Restore defaults**, **Apply best to Strategy**  
- Grid search **parallel** (worker pool, ≥4 combo)  
- Form grid **không mất** khi chuyển tab (theo strategy, trong phiên)  
- Sensitivity gắn đúng **param đã chạy grid** (`optimizedParamKeys`) + metric **Net Profit**  
- Toggle **WR / Exp / Net** trên biểu đồ; dropdown param chỉ trong toolbar chart  

### AI Signals (Ctrl+9)

Chấm **0–100** sau mỗi scan — **theo quy tắc**, không phải AI dự đoán thắng/thua.

**Grade:** A ≥80 · B ≥65 · C ≥50 · D ≥35 · F &lt;35

- Thanh **Min score** — lọc danh sách xem trên màn này
- Muốn **backtest chỉ signal điểm cao** → bật **AI score filter** ở Simulation (Ctrl+5)

---

## Phím tắt

| Phím | Chức năng |
|------|-----------|
| Ctrl+B | Ẩn/hiện sidebar |
| Ctrl+1 | Chart |
| Ctrl+2 | Data Manager |
| Ctrl+3 | Strategies |
| Ctrl+4 | Compare |
| Ctrl+5 | Simulation |
| Ctrl+6 | Statistics |
| Ctrl+7 | Reports |
| Ctrl+8 | Optimizer |
| Ctrl+9 | AI Signals |
| Ctrl+0 / F1 | Tài liệu hướng dẫn |

---

## Lưu trữ dữ liệu

| Nơi lưu | Nội dung |
|---------|----------|
| IndexedDB | Nến OHLCV **+** kết quả lớn (simulation, statistics, reports, optimizer, AI scores, compare) |
| LocalStorage | Cài đặt UI, tham số strategy, kích thước panel |

Dữ liệu cũ trong LocalStorage được tự chuyển sang IndexedDB khi mở app.

**Reset app** (Data Manager): xóa IndexedDB + mọi key `parl_*`. Export trước nếu cần giữ kết quả.

---

## Xử lý sự cố

| Vấn đề | Cách xử lý |
|--------|------------|
| Chart trống | Reload Default Data hoặc Import ở Data Manager |
| Statistics trống | Chạy Simulation (Ctrl+5) trước |
| Monte Carlo lỗi | Cần có kết quả Simulation |
| Grid search lỗi quota | Reload app — kết quả đã lưu IndexedDB |
| Jump sai ngày | Ô Jump dùng UTC — khớp dòng thời gian trên replay bar |
| Grid search chậm | Giảm combo; grid ≥4 combo dùng workers song song (4 luồng) khi trình duyệt hỗ trợ |
| Mất input khi đổi tab Optimizer | Bản mới giữ form Grid Search trong phiên — reload trang thì reset |
| Sensitivity trống | Chạy Grid Search trước; cần ≥2 giá trị khác nhau cho ít nhất một param đã tick |

---

## Tài liệu thêm

- `docs/USAGE.md` — English usage guide
- `docs/STRATEGY_SPECIFICATION.md` — đặc tả chiến lược
- Trong app: **Ctrl+0** hoặc **F1**
