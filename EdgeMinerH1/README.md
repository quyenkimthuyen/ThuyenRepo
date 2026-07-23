# ForexForge — EUR/USD H1 Self-Learning Trading System

Hệ thống backtest walk-forward + self-learning cho **EUR/USD khung H1**, dùng thống nhất dữ liệu broker từ ForgeBridge/XM MT5.

## Chạy app

Windows PowerShell:

```powershell
# Start nếu app chưa chạy
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Start

# Restart sau khi cập nhật code (mặc định nếu bỏ -Action)
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Restart

# Kiểm tra hoặc dừng app
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Status
powershell -ExecutionPolicy Bypass -File scripts/run_app_windows.ps1 -Action Stop
```

App mặc định mở tại `http://127.0.0.1:8501`. Có thể đổi cổng bằng `-Port 8502`.

Linux/macOS:

```bash
pip install -r requirements.txt
python run_gui.py          # Giao diện (khuyến nghị)
```

CLI:

```bash
python run_backtest.py     # Walk-forward backtest
python run_learning.py     # Self-learning multi-epoch
```

---

## Quy trình tối ưu kết quả (tóm tắt)

### Nguyên tắc vàng

| Mục đích | Dùng gì |
|----------|---------|
| Đánh giá strategy | **KB OFF** + spread/slippage |
| Cải thiện qua kinh nghiệm | **KB ON** + profile đúng giai đoạn |
| Tránh leakage | Học giai đoạn **A** → test OOS giai đoạn **B** |

### Quy trình mới (v5 — Settings + Trade Models)

| Bước | Trang | Việc làm |
|------|-------|----------|
| 1 | **Cài đặt** | Train 3/6/9T · giai đoạn học · vòng học · OOS 2025–2026 |
| 2 | **Học & tối ưu → Huấn luyện bộ nhớ** | Tạo/học KB theo giai đoạn |
| 3 | **Học & tối ưu → Grid Search** | Chạy theo Cài đặt → tạo **Trade Model** |
| 4 | **Phân tích** | Chọn Trade Model → Risk / Nhật ký / Chiến lược |
| 5 | **Giám sát paper** / **MT5 Bridge** | Bật service → **tự remine mỗi tuần** (không cần Grid lại) |

Đổi Cài đặt → Grid Search chỉ chạy **combo mới** (giữ kết quả cũ).

**Lưu ý:** Trade Model là cấu hình đã lưu. Paper/Bridge **dùng** cấu hình đó để remine hàng tuần — **không** tự ghi đè model trong danh sách. Chỉ chạy lại KB → Grid → chọn model khi muốn đổi “bộ não”.

### 6 bước trên GUI (legacy)

| Bước | Trang | Việc làm |
|------|-------|----------|
| 1 | Tổng quan | **Đồng bộ MT5** qua ForgeBridge EA |
| 2 | Backtest Lab | Backtest **KB OFF**, spread 1.0 / slip 0.3, lưu Report Compare |
| 3 | KB & Giai đoạn → Học KB | Tạo profile (vd `era_2022_2023`), học 2022–2023, 3–5 epoch |
| 4 | KB & Giai đoạn → Backtest OOS | Chọn profile + OOS 2024, so sánh KB ON/OFF |
| 5 | Report Compare | So sánh metrics, equity overlay |
| 6 | Backtest Lab, Journal, Risk, Paper | Hold-out 12 tháng, kiểm tra lệnh, paper 3–6 tháng |

Chi tiết đầy đủ: mở GUI → **Usage Guide**.

### CLI nhanh

```bash
# Baseline
python run_backtest.py --no-kb --oos-from 2024-01-01 --oos-to 2024-12-31 --spread 1.0 --slippage 0.3

# Học KB era
python run_learning.py --kb-profile era_2022_2023 \
  --from-date 2022-01-01 --until-date 2023-12-31 --epochs 3

# Backtest OOS với KB + epoch cụ thể
python run_backtest.py --kb-profile era_2022_2023 --kb-epoch 2 \
  --oos-from 2024-01-01 --oos-to 2024-12-31 --spread 1.0 --slippage 0.3
```

---

## Phân biệt Train 3 tháng · KB · Epoch

| | **Train 3 tháng** | **KB** | **Epoch** |
|---|---|---|---|
| Là gì | Mine strategy **mỗi tuần** WF | Bộ nhớ kinh nghiệm dài hạn | Một **vòng học full** giai đoạn |
| Tần suất | Mỗi tuần OOS | Dùng khi KB ON; cập nhật khi học | 3–5–8 lần (thủ công) |
| Mục đích | Strategy theo data **gần** | Mine **thông minh hơn** từ quá khứ | **Cải thiện** KB qua nhiều vòng |

```
Train 3 tháng (mỗi tuần):  |-- 3 tháng --| mine → trade tuần OOS
KB:                        genomes, rules, ML — profile theo era (era_2022_2023)
Epoch:                     chạy full WF trên 2022–2023 → cập nhật KB → snapshot ep001, ep002...
```

**Quan hệ:** Epoch cập nhật KB → KB hỗ trợ mine trong mỗi tuần → mỗi tuần vẫn train 3 tháng.

- **Train 3 tháng** — luôn có, strategy ngắn hạn  
- **KB** — bật/tắt, chọn profile + epoch snapshot  
- **Epoch** — học offline để KB tốt hơn  

Chi tiết + sơ đồ: GUI → **Usage Guide** mục **5**.

---

## Các trang GUI

| Trang | Mục đích |
|-------|----------|
| Tổng quan | KPI, quy trình live |
| Giám sát paper | Tín hiệu tuần trên dữ liệu MT5 · remine tự động nếu bật chu kỳ |
| **MT5 Bridge** | App quyết định · EA execute · log + thống kê lệnh · remine mỗi tuần khi Start |
| **Học & tối ưu** | Grid Search · Trade Models · so sánh · học KB (**thủ công** khi cập nhật model) |
| **Cài đặt** | Train window · giai đoạn học · kiểm chứng |
| **Phân tích** | Risk · Nhật ký lệnh · Chiến lược (theo Trade Model) |
| Hướng dẫn | Tài liệu đầy đủ (gồm mục MT5 Bridge) |

### Trang cũ (EdgeMiner1)

---

## KB Profiles (theo giai đoạn)

Mỗi profile = file KB riêng trong `learning/kb_profiles/`:

```
era_2022_2023.json   ← học 2022–2023, backtest OOS 2024
era_2022_2024.json   ← học 2022–2024, backtest OOS 2025
```

Quy tắc: `trained_to ≤ oos_from` — app kiểm tra và cảnh báo trên GUI.

**Epoch snapshot:** Mỗi epoch học lưu file riêng (`snapshots/{profile}/epNNN.json`). Chọn **Latest** hoặc **Epoch N** khi backtest/paper. CLI: `--kb-epoch 2`.

---

## Self-learning (v4)

```bash
python run_learning.py              # 5 epoch (mặc định)
python run_learning.py --epochs 10
python run_learning.py --reset      # xóa KB profile
python run_learning.py --kb-profile era_2022_2023 --from-date 2022-01-01 --until-date 2023-12-31
```

**3 lớp học:** Rule Memory · Genome Evolution · ML Experience

**Cảnh báo:** Nhiều epoch trên cùng giai đoạn → overfit. Xác nhận bằng OOS giai đoạn khác.

---

## Cấu trúc project

```
run_gui.py / gui/app.py       # GUI Streamlit
run_backtest.py              # Walk-forward backtest
run_learning.py              # Self-learning
kb_profiles.py               # Quản lý KB theo giai đoạn
strategy_miner.py            # Mine + backtest
knowledge_base.py            # Knowledge base
data/mt5_eurusd_h1.parquet   # Cache H1 chuẩn từ ForgeBridge/XM MT5
learning/kb_profiles/        # KB từng era
results/reports/             # Kho báo cáo so sánh
```

---

## Mục tiêu hệ thống

| Metric | Ngưỡng |
|--------|--------|
| Win rate (1Y) | > 60% |
| RR | > 2 |
| Tần suất | ~2 lệnh/tuần |
| Profitable | Total R > 0 |

Mặc định chi phí: spread **1.0 pip**, slippage **0.3 pip**.

---

## Trước khi live

1. KB OFF profitable trên ≥2 giai đoạn OOS
2. Hold-out 12 tháng
3. Paper Monitor 3–6 tháng
4. Micro lot đầu tiên

*ForexForge v4 — Walk-forward strategy mining that learns from every trade.*
