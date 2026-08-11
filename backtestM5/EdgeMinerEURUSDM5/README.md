> **M5 desk `E31`** — `M5E31` · app/bridge/sim/compare `8811/9075/9186/9296` · folder `bridge_m5e31` · magic `20261031` · cloned from M15 `EdgeMinerEURUSDM15`.

# ForexForge — EUR/USD M15 Self-Learning Trading System

Hệ thống backtest walk-forward + self-learning cho **EUR/USD khung M15**, dùng thống nhất dữ liệu broker từ ForgeBridge/XM MT5.

> `ForgeBest3m_Frozen.mq5` và `ForgeBest3m_WF.mq5` là EA H1 legacy, không tương thích
> với model M15 và không được dùng cho live. Live/Simulate chỉ dùng `ForgeBridgeM5E31.mq5`.

Chạy song song với `C:\Work\ThuyenRepo\EdgeMinerH1`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_dual_edgeminer.ps1 -Action Status
powershell -ExecutionPolicy Bypass -File .\scripts\run_dual_edgeminer.ps1 -Action Restart
```

Backtest desk E21: app `8711` · Bridge `8975` · Sim chart `9086` · Compare `9196`
(port `8976` = legacy Paper Monitor chart — desk đã gỡ, không dùng).
Folder `bridge_m5e31`, Magic `20261021`. H1 dùng `8502/8865/8866`, folder `bridge_h1`, Magic `20260725`.

Clone thêm instance M15 (cô lập repo + magic + port):

```bash
./scripts/clone_m15_instance.sh B4 --dry-run   # xem ma trận ID
./scripts/clone_m15_instance.sh B4             # tạo ../EdgeMinerM15B4
# Spec = <Version><Offset> → names dùng cả spec (B4); ports = default + offset*10
```

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

App mặc định mở tại `http://127.0.0.1:8711`. Có thể đổi cổng bằng `-Port 8502` (Windows) hoặc `--port 8502` (Linux).

Linux/macOS:

```bash
pip install -r requirements.txt

# Lifecycle (cùng hành vi với run_app_windows.ps1)
./scripts/run_app_linux.sh Start
./scripts/run_app_linux.sh Restart          # mặc định nếu không truyền action
./scripts/run_app_linux.sh Status
./scripts/run_app_linux.sh Stop
# ./scripts/run_app_linux.sh Restart --port 8502

# Hoặc chạy trực tiếp (foreground)
python run_gui.py
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
| 1 | **Cài đặt** | Train 3/6/9T · giai đoạn học · vòng học · OOS · **Mining preset** |
| 2 | **Học & tối ưu → Huấn luyện bộ nhớ** | Tạo/học KB theo giai đoạn |
| 3 | **Học & tối ưu → Grid Search** | Chạy theo Cài đặt (gồm mining preset) → tạo **Trade Model** |
| 4 | **Trade Models** | Tổng hợp · Sức khỏe · Rủi ro · Nhật ký · Chiến lược (**Active** = phân tích) |
| 5 | **Compare Trade** / **MT5 Bridge** | So model → Start Live/Sim theo **Bridge roster** → remine hàng tuần |

Đổi Cài đặt → Grid Search chỉ chạy **combo mới** (giữ kết quả cũ).

**Grid Search axes:** `train weeks × KB profile × epoch × mining preset` (OOS/spread/slip cố định; `grid_objective` chỉ xếp hạng). Chi tiết: [`docs/grid_search.md`](docs/grid_search.md).

**Mining search space:** lớp cấu hình *cách mine* (RR, exit, anti-chase…) — khác KB và train weeks. Mặc định app: preset **`elite_or_quality`**. Chi tiết: [`docs/mining_search_space.md`](docs/mining_search_space.md). Audit xếp hạng / loại bỏ: [`docs/mining_space_audit.md`](docs/mining_space_audit.md).

**Lưu ý:** Trade Model lưu kèm `mining_search_space`. **MT5 Bridge** remine theo roster đã chọn — **không** lấy từ Active, **không** tự ghi đè store. Model nghiên cứu nên **Archive** (giữ report); Xóa cứng chỉ khi muốn mất artifact. Chỉ KB → Grid → model mới khi đổi “bộ não”.

### 6 bước trên GUI (legacy — tham khảo)

| Bước | Trang | Việc làm |
|------|-------|----------|
| 1 | Tổng quan | **Đồng bộ MT5** qua ForgeBridge EA |
| 2 | Backtest Lab | Backtest **KB OFF**, spread 1.0 / slip 0.3, lưu Report Compare |
| 3 | KB & Giai đoạn → Học KB | Tạo profile (vd `era_2022_2023`), học 2022–2023, 3–5 epoch |
| 4 | KB & Giai đoạn → Backtest OOS | Chọn profile + OOS 2024, so sánh KB ON/OFF |
| 5 | Report Compare | So sánh metrics, equity overlay |
| 6 | Trade Models · Compare · Bridge | Hold-out / Health OOS → Compare → Live + Parity |

Chi tiết đầy đủ: mở GUI → **Hướng dẫn**.

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

## Phân biệt Train 3 tuần · KB · Epoch

| | **Train 3 tuần** | **KB** | **Epoch** |
|---|---|---|---|
| Là gì | Mine strategy **mỗi tuần** WF | Bộ nhớ kinh nghiệm dài hạn | Một **vòng học full** giai đoạn |
| Tần suất | Mỗi tuần OOS | Dùng khi KB ON; cập nhật khi học | 3–5–8 lần (thủ công) |
| Mục đích | Strategy theo data **gần** | Mine **thông minh hơn** từ quá khứ | **Cải thiện** KB qua nhiều vòng |

```
Train 3 tuần (mỗi tuần):   |-- 3 tuần --| mine → trade tuần OOS
KB:                        genomes, rules, ML — profile theo era (era_2022_2023)
Epoch:                     chạy full WF trên 2022–2023 → cập nhật KB → snapshot ep001, ep002...
```

**Quan hệ:** Epoch cập nhật KB → KB hỗ trợ mine trong mỗi tuần → mỗi tuần train lại trên 3/6/9 tuần gần nhất.

- **Train 3/6/9 tuần** — cửa sổ strategy ngắn hạn
- **KB** — bật/tắt, chọn profile + epoch snapshot  
- **Epoch** — học offline để KB tốt hơn  

Chi tiết + sơ đồ: GUI → **Usage Guide** mục **5**.

---

## Các trang GUI

| Trang | Mục đích |
|-------|----------|
| Tổng quan | KPI, quy trình live |
| **Học & tối ưu** | Cài đặt · Huấn luyện KB · Grid Search |
| **Trade Models** | Active (phân tích) · Tổng hợp (Archive/Rename) · Sức khỏe · Risk · Journal |
| **Compare Trade** | So nhiều model trên lịch sử (**không EA**; khớp lệnh = *sim fills* nội bộ) |
| **MT5 Bridge** | **Live** (lệnh MT5) + **Simulate** (HistoryFeed) · roster 1–5 model · remine khi Start |
| Hướng dẫn | Thuật ngữ · Active vs Bridge · Archive · sim fills |

**Mining search space (mặc định `elite_or_quality`):** xem [`docs/mining_search_space.md`](docs/mining_search_space.md).

**Active ≠ Bridge:** Active chỉ cho tab phân tích. Lệnh Live/Sim theo roster trên **MT5 Bridge**.  
**“Paper” trong code** (`PaperBook`, `paper_fill.py`, port `8976`) = helper khớp lệnh mô phỏng cho Compare/HistoryFeed — **không** phải desk Paper Monitor (đã gỡ). Chi tiết: GUI **Hướng dẫn** mục 6.

---

## KB Profiles (theo giai đoạn)

Mỗi profile = file KB riêng trong `learning/kb_profiles/`:

```
era_2022_2023.json   ← học 2022–2023, backtest OOS 2024
era_2022_2024.json   ← học 2022–2024, backtest OOS 2025
```

Quy tắc: `trained_to ≤ oos_from` — app kiểm tra và cảnh báo trên GUI.

**Epoch snapshot:** Mỗi epoch học lưu file riêng (`snapshots/{profile}/epNNN.json`). Chọn **Latest** hoặc **Epoch N** khi backtest/remine. CLI: `--kb-epoch 2`.

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
data/mt5_eurusd_m5.parquet  # Cache M15 chuẩn từ ForgeBridge/XM MT5
learning/kb_profiles/        # KB từng era
results/reports/             # Kho báo cáo so sánh
```

---

## Mục tiêu hệ thống

| Metric | Ngưỡng |
|--------|--------|
| Win rate (1Y) | > 60% |
| RR | > 2 |
| Profitable | Total R > 0 |

Tần suất lệnh/tuần **không** còn là điều kiện checklist / “đủ live” (preset elite cố ý ít lệnh hơn). Vẫn xem cột Tpw trên Tổng hợp để biết mật độ giao dịch.

Mặc định chi phí: spread **1.0 pip**, slippage **0.3 pip**.

---

## Trước khi live

1. KB OFF profitable trên ≥2 giai đoạn OOS
2. Hold-out 12 tháng
3. Compare Trade + Parity / Health OOS
4. Micro lot đầu tiên

*ForexForge v4 — Walk-forward strategy mining that learns from every trade.*
