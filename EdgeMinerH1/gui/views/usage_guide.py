"""8. Usage Guide — hướng dẫn vận hành ForexForge."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header


def render():
  render_page_header(ALL_ITEMS["guide"], show_workspace=False)

  st.markdown("""
## 1. ForexForge là gì?

**ForexForge** là hệ thống backtest & self-learning cho **EUR/USD khung H1**, gồm:

- **Walk-forward backtest** — train 3 tháng, re-optimize hàng tuần, trade OOS (không look-ahead)
- **Strategy miner** — khai phá rule từ features + lọc ML
- **Self-learning (v4)** — tích lũy KB qua nhiều epoch (rules, genomes, ML samples)
- **MT5 Bridge** — App (Best 3m) quyết định; EA `ForgeBridge` execute trên **MetaTrader 5** (không phải MT4)

---

## 2. Cài đặt & chạy

```bash
cd /thuyen
pip install -r requirements.txt
python run_gui.py          # Giao diện (khuyến nghị)
python run_backtest.py     # CLI backtest
python run_learning.py     # CLI learning
```

**CLI backtest:**
```bash
python run_backtest.py --no-kb              # Walk-forward sạch (không KB)
python run_backtest.py --spread 1.2 --slippage 0.3
python run_backtest.py --holdout-months 12  # Tách 12 tháng cuối forward test
```

---

## 3. Luồng dữ liệu

| Bước | Mô tả |
|------|--------|
| 1 | ForgeBridge đồng bộ **EUR/USD H1** từ XM MT5 → cache `data/mt5_eurusd_h1.parquet` |
| 2 | Tính **37+ features** causal (`feature_engine.py`) |
| 3 | Mỗi tuần: train 3 tháng trước → mine/optimize strategy |
| 4 | Trade **tuần OOS** (signal close bar *i*, entry open bar *i+1*) |
| 5 | Ghi metrics, trades → `results/backtest_report.json` |

---

## 4. Walk-forward (trái tim của app)

```
Timeline:  |---- train 3 tháng ----|-- OOS tuần --|
           ^                        ^
           không trade              chỉ trade ở đây

Tuần tiếp theo: train window trượt về phía trước, lặp lại.
```

**Quan trọng:**
- Tuần OOS **không nằm** trong cửa sổ train
- Features chỉ dùng quá khứ
- **KB OFF** = đánh giá trung thực nhất (khuyến nghị trước khi live)

---

## 5. Phân biệt Train 3 tháng · KB · Epoch

Ba khái niệm này ở **các tầng khác nhau** — dễ nhầm vì đều liên quan “học”, nhưng mục đích và thời gian khác nhau.

### Tóm tắt

| | **Train 3 tháng** | **KB (Knowledge Base)** | **Epoch** |
|---|---|---|---|
| **Là gì** | Cửa sổ data để **mine strategy mỗi tuần** | **Bộ nhớ kinh nghiệm** tích lũy | **Một vòng học full** trên cả giai đoạn |
| **Tần suất** | Mỗi **tuần** OOS (walk-forward) | Dùng liên tục, cập nhật khi học | Chạy **thủ công** 3–5–8 lần |
| **Lưu gì** | Rules, RR, ML cho **tuần đó** | Genomes, rule stats, ML samples | Snapshot KB sau mỗi epoch |
| **Mục đích** | Strategy **phù hợp thị trường gần** | Mine **thông minh hơn** nhờ quá khứ | **Cải thiện dần** KB qua nhiều vòng |

### 1) Train 3 tháng — Walk-forward (lõi backtest)

**Không phải KB** — đây là cơ chế walk-forward:

```
Tuần 1 OOS:  |---- train 3 tháng trước ----| → mine strategy → trade tuần 1
Tuần 2 OOS:       |---- train 3 tháng ----| → mine lại    → trade tuần 2
```

- Mỗi tuần: lấy **3 tháng H1** ngay trước tuần OOS
- **Mine** rules + ML → strategy cho **đúng tuần đó**
- Trade OOS 1 tuần, cửa sổ train trượt về phía trước

→ Luôn chạy (KB ON hay OFF). Strategy **đổi theo tuần** theo data gần nhất.

### 2) KB — Bộ nhớ kinh nghiệm dài hạn

File JSON lưu kinh nghiệm qua nhiều tuần/tháng:

| Thành phần | Nội dung |
|------------|----------|
| Rule stats | Rule nào hay thắng/thua |
| Genomes | DNA strategy tốt (đột biến, lai) |
| ML experience | Mẫu feature → kết quả lệnh |

**Profile** (`era_2022_2023`): KB học trên **2022–2023**, dùng khi backtest **2024+**.

Khi **KB ON**: vẫn train 3 tháng mỗi tuần, nhưng mine **ưu tiên** genomes/rules/ML từ KB (lọc `as_of` = đầu tuần).

```
Train 3 tháng = "học từ data gần"
KB            = "học từ kinh nghiệm nhiều tuần/tháng trước"
```

### 3) Epoch — Một vòng học toàn giai đoạn

**1 epoch** = chạy **full walk-forward** trên giai đoạn học (vd 2022–2023), rồi **cập nhật KB**.

```
Epoch 1: WF 2022–2023 → ghi vào KB (yếu)
Epoch 2: WF lại       → KB đã có kinh nghiệm epoch 1 → tốt hơn
Epoch 3: ...
```

- Epoch **không thay** train 3 tháng — train 3 tháng vẫn chạy **bên trong** mỗi tuần
- Epoch = **lặp lại** cả giai đoạn để KB cải thiện
- Sau mỗi epoch: lưu **snapshot** (`ep001`, `ep002`, …) — chọn khi backtest/paper

### Quan hệ khi chạy app

```
EPOCH (học offline)     → cập nhật KB Profile
         ↓
KB Profile              → dùng khi KB ON
         ↓
Mỗi tuần OOS: TRAIN 3 THÁNG → mine (+ KB) → trade 1 tuần
```

### Ví dụ (backtest OOS 2024)

| Bước | Thành phần | Việc xảy ra |
|------|------------|-------------|
| Trước | Epoch 1–3 trên 2022–2023 | KB học rule/genome |
| Backtest | KB ON + profile | Mỗi tuần 2024: train 3T + mine có KB |
| So sánh | KB OFF | Cùng WF, không KB — baseline |
| Tinh chỉnh | Epoch snapshot 2 vs 5 | Chọn bản KB OOS tốt nhất |

**Nhớ nhanh:**
- **Train 3 tháng** — luôn có, mỗi tuần, strategy ngắn hạn
- **KB** — bộ nhớ dài hạn; bật/tắt + chọn profile giai đoạn
- **Epoch** — học nhiều vòng để KB tốt hơn; snapshot = chọn phiên bản KB

---

## 6. Các trang GUI (theo quy trình)

| Trang | Mục đích |
|-------|----------|
| **Tổng quan** | Tiến độ, KPI, Refresh data |
| **Học & tối ưu** | ① Cài đặt → ② Huấn luyện KB → ③ Grid Search → ④ Trade Models (Quản lý · Rủi ro · Nhật ký · Chiến lược) |
| **Giám sát paper** | Tín hiệu & lệnh tuần trên cùng dữ liệu broker MT5 |
| **MT5 Bridge** | App quyết định Best 3m · EA `ForgeBridge` execute · log giao tiếp |
| **Hướng dẫn** | Tài liệu này |

**Trade Model**: chọn trong **Học & tối ưu → Trade Models → Quản lý** — Paper, Bridge & phân tích dùng chung.

### Remine hàng tuần tự động vs cập nhật Trade Model

**Trade Model** = snapshot cấu hình đã lưu (`train_months`, KB profile/epoch, OOS, KPI từ Grid).  
App **không** tự đổi model trong danh sách mỗi tuần.

| Việc | Tự động? | Điều kiện |
|------|----------|-----------|
| **Remine strategy mỗi tuần** (mine lại trên cửa sổ train gần nhất → tín hiệu tuần mới) | Có | **Giám sát paper** bật chu kỳ *hoặc* **MT5 Bridge** Start service |
| Đồng bộ lịch sử MT5 | Có (EA chunk + bar live) | Tổng quan hoặc MT5 Bridge |
| **Huấn luyện KB** (epoch mới) | Không | Học & tối ưu → ② Huấn luyện |
| **Grid Search** xếp hạng combo mới | Không | Khi đổi Cài đặt hoặc muốn model khác |
| **Tạo / chọn Trade Model** | Không | Chỉ khi đổi combo active (vd Best 3m → model khác) |
| Export Replay / Frozen EA (MT5 Tester) | Không | Chạy script export khi cần lịch/EA mới |

**Vận hành hàng ngày / tuần:** chọn Trade Model một lần → bật Paper và/hoặc Bridge service → mỗi tuần app tự remine theo cấu hình đó.  
**Chỉ** chạy lại KB → Grid → chọn model khi muốn đổi “bộ não” (KB mới, train window / OOS khác).

### MT5 Bridge — dùng thế nào?

Đây là cầu nối **MetaTrader 5** (không phải MT4):

1. Mở **MT5 Bridge** → chọn Trade Model (Best 3m) → **Start service**
2. Service chạy **process riêng** (không phụ thuộc tab GUI) — đổi tab / refresh page **không** dừng; bấm **Stop** mới tắt
3. Trên MT5: compile/attach EA `ForgeBridge`, `InpMode = Live` (thư mục `MQL5/Files/bridge`)
4. Mỗi H1 mới: EA ghi `bar.json` → App remine/decide → `decision.json` → EA BUY/SELL hoặc FLAT
5. Xem **Nhật ký giao tiếp** trên GUI (`comm_log.jsonl`: `bar_received`, `decision_sent`, `fill_received`)
6. Xem **Thống kê lệnh Bridge** (thắng/thua, R, profit) — EA ghi `fill.json` open/close → App lưu `trades.json`

CLI tương đương GUI service: `python scripts/mt5_bridge_service.py`  
Chi tiết file: `mt5/bridge/README.md`

---

## 7. Chi phí giao dịch (spread / slippage)

Backtest mô phỏng:
- **Spread** — half vào entry, half vào exit
- **Slippage** — adverse mỗi lần fill

Mặc định: spread **1.0 pip**, slippage **0.3 pip** (chỉnh trong Backtest Lab).

Kết quả sau chi phí **thấp hơn** backtest lý tưởng — gần thực tế hơn.

---

## 8. Hold-out forward test

Khi bật **holdout 12 tháng**:
1. Walk-forward chạy trên data **trước** holdout
2. Giai đoạn holdout: mine **1 lần** tại điểm cắt, trade forward **không re-optimize**

→ Kiểm tra strategy trên data **chưa từng thấy** khi optimize WF chính.

Xem kết quả tại **Risk Dashboard** hoặc `holdout_forward` trong báo cáo JSON.

---

## 9. KB theo giai đoạn (KB Profiles)

Mỗi **profile** = một file KB riêng, gắn khoảng thời gian đã học.

```
learning/kb_profiles/
  index.json
  era_2022_2023.json    ← học chỉ trên 2022–2023
  era_2024.json         ← học chỉ trên 2024
```

### Tạo KB giai đoạn (CLI)

```bash
python run_learning.py --kb-profile era_2022_2023 --kb-name "Era 2022-23" \\
  --from-date 2022-01-01 --until-date 2023-12-31 --epochs 3
```

### Backtest với KB + mốc OOS (CLI)

```bash
python run_backtest.py --kb-profile era_2022_2023 \\
  --oos-from 2024-01-01 --oos-to 2024-12-31
```

### Quy tắc khách quan

| Bước | Việc cần làm |
|------|----------------|
| 1 | Học KB trên giai đoạn **A** (vd 2022–2023) |
| 2 | Backtest OOS giai đoạn **B** (vd 2024) chọn profile A |
| 3 | App kiểm tra `trained_to ≤ oos_from` |
| 4 | Mỗi tuần OOS: KB lọc `as_of` — chỉ kinh nghiệm **trước tuần đó** |

→ KB **không dùng** thông tin tương lai so với tuần đang backtest.

### Chọn Epoch (snapshot)

Mỗi lần **học xong 1 epoch**, app lưu snapshot KB tại:

```
learning/kb_profiles/snapshots/era_2022_2023/ep001.json
learning/kb_profiles/snapshots/era_2022_2023/ep002.json
...
```

Khi chạy backtest / paper, dropdown **KB Epoch (snapshot)**:

| Lựa chọn | Ý nghĩa |
|----------|---------|
| **Latest** | File KB chính — trạng thái sau lần học gần nhất |
| **Epoch N** | KB đúng như sau epoch N (WR/Total R hiển thị kèm label) |

CLI: `--kb-epoch 2` hoặc `--kb-epoch 8`

> Profile học **trước khi có tính năng snapshot** chỉ có bản bootstrap (1 file). Chạy học mới để có snapshot từng epoch.

GUI: **KB & Giai đoạn** · **Backtest Lab** · **Paper Monitor** — đều có chọn profile + epoch.

---

## 10. Self-learning (tóm tắt)

**3 lớp học:** Rule Memory · Genome Evolution · ML Experience

**Cảnh báo:** Nhiều epoch trên cùng giai đoạn → overfit. Xác nhận bằng backtest OOS giai đoạn **khác** hoặc hold-out.

---

## 11. Mục tiêu & constraints

| Mục tiêu | Ngưỡng |
|----------|--------|
| Win rate | > 60% (1 năm gần nhất) |
| RR | > 2 |
| Profitable | Total R > 0 |
| Tần suất | ~2 lệnh/tuần |

Checklist hiển thị ở **Tổng quan** và **Trade Models → Rủi ro**.

---

## 12. Quy trình tối ưu kết quả (GUI)

### Nguyên tắc vàng

| Mục đích | Dùng gì |
|----------|---------|
| **Đánh giá strategy** | Grid Search + so sánh combo theo Cài đặt |
| **Cải thiện qua kinh nghiệm** | Huấn luyện KB theo giai đoạn → rồi mới Grid |
| **Chống leakage** | Học giai đoạn **A** → kiểm chứng OOS giai đoạn **B** |

### 5 bước trên GUI

| Bước | Trang | Việc làm |
|------|-------|----------|
| 1 | **Học & tối ưu → ① Cài đặt** | Train 3/6/9T · giai đoạn học · vòng học · OOS |
| 2 | **Học & tối ưu → ② Huấn luyện bộ nhớ** | Học KB đủ theo Cài đặt |
| 3 | **Học & tối ưu → ③ Grid Search** | Chạy combo → xếp hạng |
| 4 | **Học & tối ưu → ④ Trade Models** | Tạo & chọn model · xem Rủi ro / Nhật ký / Chiến lược |
| 5 | **Giám sát paper** + **MT5 Bridge** | Bật chu kỳ / Start service → **tự remine mỗi tuần** |

Chỉ live **micro lot** khi paper/bridge khớp kỳ vọng backtest.

**Không cần Grid lại mỗi tuần** — Paper/Bridge tự remine theo Trade Model đang chọn. Grid/KB chỉ khi muốn cập nhật model.

### Mẹo tối ưu

1. **Luôn bật spread/slippage** trong Cài đặt.
2. **Đủ KB trước Grid** — thiếu giai đoạn/vòng học → Grid ra 0 combo.
3. **3–5 vòng học** thường đủ; nhiều hơn dễ overfit.
4. **Một Trade Model = một combo** — đổi Cài đặt rồi Grid lại chỉ bổ sung combo mới.

### CLI nhanh

```bash
# Baseline
python run_backtest.py --no-kb --oos-from 2024-01-01 --oos-to 2024-12-31 --spread 1.0 --slippage 0.3

# Học KB
python run_learning.py --kb-profile era_2022_2023 --from-date 2022-01-01 --until-date 2023-12-31 --epochs 3

# Test OOS với KB
python run_backtest.py --kb-profile era_2022_2023 --kb-epoch 2 \
  --oos-from 2024-01-01 --oos-to 2024-12-31 --spread 1.0 --slippage 0.3
```

---

## 13. File quan trọng

```
run_gui.py / gui/app.py     # GUI
run_backtest.py             # Walk-forward
run_learning.py             # Self-learning
strategy_miner.py           # Mine + backtest
feature_engine.py           # Features
knowledge_base.py           # KB
data/mt5_eurusd_h1.parquet  # Cache H1 chuẩn từ ForgeBridge/XM MT5
mt5_bridge/                 # Bridge App ↔ MT5 EA
mt5/Experts/ForgeBridge.mq5 # EA execute (Live / Replay)
mt5/bridge/                 # bar/decision/fill/comm_log/replay
scripts/mt5_bridge_service.py
scripts/export_bridge_replay.py
results/backtest_report.json
results/learning_report.json
results/reports/              # Kho báo cáo Report Compare
kb_profiles.py              # Quản lý profile KB
learning/kb_profiles/       # KB từng giai đoạn
```

---

## 14. Hạn chế đã biết

- Một pair / một timeframe (EUR/USD H1)
- Paper Monitor dùng cùng dữ liệu nến H1 từ broker với Grid và MT5 Bridge
- MT5 Bridge cần EA + service App chạy đồng thời; Wine/SSL login broker vẫn có thể fail trên Linux Docker
- Intrabar SL/TP — thứ tự chạm có thể khác live
- RoR là ước lượng, không phải Monte Carlo đầy đủ
- Không dùng nguồn giá ngoài; lịch sử và bar live đều đến từ ForgeBridge/XM MT5

---

## 15. FAQ

**Q: Kết quả 60% WR có vào live được không?**  
A: Chỉ sau paper + hold-out + spread. KB OFF phải vẫn profitable.

**Q: KB ON hay OFF?**  
A: **OFF** để đánh giá. **ON** khi muốn tận dụng kinh nghiệm đã học (có rủi ro overfit).

**Q: Tại sao nhiều lệnh LONG?**  
A: Miner có thể bias theo regime. Kiểm tra Trade Journal → Direction bias.

**Q: Backtest chậm?**  
A: ~2 phút cho 4 năm / 224 tuần. Dùng cache data, tránh refresh liên tục.

**Q: Quy trình nào nên làm trước?**  
A: KB OFF baseline → học KB era → OOS với profile → Report Compare → hold-out → paper.

**Q: App có tự optimize mỗi tuần không?**  
A: **Có remine strategy mỗi tuần** khi Paper (chu kỳ) hoặc MT5 Bridge service đang chạy. **Không** tự chạy lại Grid / tạo Trade Model mới — phải làm tay khi muốn đổi model.

**Q: MT5 Bridge khác Paper Monitor thế nào?**  
A: Paper và Bridge dùng chung nến từ **MT5 broker**. Paper mô phỏng lệnh; Bridge gửi quyết định cho EA mở lệnh thật/demo.

**Q: Có hỗ trợ MT4 không?**  
A: Không — chỉ **MT5** (`ForgeBridge.mq5`).

**Q: Xem log giao tiếp App ↔ EA ở đâu?**  
A: GUI **MT5 Bridge** → Nhật ký giao tiếp, hoặc file `mt5/bridge/comm_log.jsonl`.

**Q: Khác nhau Train 3 tháng, KB và Epoch?**  
A: **Train 3 tháng** = mine strategy mỗi tuần WF (luôn chạy). **KB** = bộ nhớ dài hạn (rules/genomes/ML). **Epoch** = một vòng học full giai đoạn để cải thiện KB. Xem mục **5** trong Usage Guide.

---

## 16. Kiến trúc

```
Data → Features → Miner (+ML) → Walk-forward → Metrics
                      ↑
              KB / Evolution (optional)
```

*ForexForge v4 — Walk-forward strategy mining that learns from every trade.*
  """)

  with st.expander("Sơ đồ Train 3 tháng · KB · Epoch (mermaid)"):
    st.code("""
graph TD
  E[Epoch: học offline full giai đoạn] --> KB[KB Profile]
  KB --> WF[Mỗi tuần OOS]
  WF --> T[Train 3 tháng]
  T --> M[Mine strategy]
  KB -.->|KB ON| M
  M --> TR[Trade 1 tuần]
    """, language="text")

  with st.expander("Sơ đồ quy trình tối ưu (mermaid)"):
    st.code("""
graph TD
  A[Refresh Data] --> B[Backtest KB OFF + chi phí]
  B --> C{Lợi nhuận > 0?}
  C -->|Không| D[Journal / điều chỉnh / dừng]
  C -->|Có| E[Học KB giai đoạn TRƯỚC OOS]
  E --> F[Backtest OOS + KB profile]
  F --> G[Report Compare]
  G --> H{OOS tốt hơn baseline?}
  H -->|Không| I[Giảm epoch / profile khác]
  H -->|Có| J[Hold-out + Paper Monitor]
  J --> K[Live micro lot]
    """, language="text")

  with st.expander("Sơ đồ walk-forward (mermaid)"):
    st.code("""
graph LR
  A[XM MT5 H1] --> B[Features]
  B --> C[Train 3 tháng]
  C --> D[Mine Strategy]
  D --> E[Trade OOS tuần]
  E --> F[Metrics / KB]
  F --> C
    """, language="text")
