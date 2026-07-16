"""8. Usage Guide — hướng dẫn vận hành ForexForge."""
from __future__ import annotations

import streamlit as st


def render():
  st.header("📖 Usage Guide — ForexForge")
  st.caption("Hướng dẫn đầy đủ cách app hoạt động và quy trình sử dụng")

  st.markdown("""
## 1. ForexForge là gì?

**ForexForge** là hệ thống backtest & self-learning cho **EUR/USD khung H1**, gồm:

- **Walk-forward backtest** — train 3 tháng, re-optimize hàng tuần, trade OOS (không look-ahead)
- **Strategy miner** — khai phá rule từ features + lọc ML
- **Self-learning (v4)** — tích lũy KB qua nhiều epoch (rules, genomes, ML samples)

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
| 1 | Tải **EUR/USD H1** từ Dukascopy (2022+) → cache `data/eurusd_h1.parquet` |
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

## 5. Các trang GUI

| Trang | Mục đích |
|-------|----------|
| **Command Center** | KPI tổng quan, quick actions |
| **Backtest Lab** | Chạy WF, biểu đồ equity/DD, log tuần |
| **Trade Journal** | Xem từng lệnh, filter, mini chart |
| **Strategy Inspector** | Rules, genomes, DNA strategy |
| **Learning Center** | Multi-epoch, KB, cảnh báo overfit |
| **Risk Dashboard** | DD, streaks, risk of ruin, weekly limit |
| **Paper Monitor** | Tín hiệu & lệnh tuần hiện tại |
| **Usage Guide** | Tài liệu này |

---

## 6. Chi phí giao dịch (spread / slippage)

Backtest mô phỏng:
- **Spread** — half vào entry, half vào exit
- **Slippage** — adverse mỗi lần fill

Mặc định: spread **1.0 pip**, slippage **0.3 pip** (chỉnh trong Backtest Lab).

Kết quả sau chi phí **thấp hơn** backtest lý tưởng — gần thực tế hơn.

---

## 7. Hold-out forward test

Khi bật **holdout 12 tháng**:
1. Walk-forward chạy trên data **trước** holdout
2. Giai đoạn holdout: mine **1 lần** tại điểm cắt, trade forward **không re-optimize**

→ Kiểm tra strategy trên data **chưa từng thấy** khi optimize WF chính.

Xem kết quả tại **Risk Dashboard** hoặc `holdout_forward` trong báo cáo JSON.

---

## 8. Self-learning & Knowledge Base

**3 lớp học** (`learning/knowledge.json`):

| Lớp | Nội dung |
|-----|----------|
| Rule Memory | Rule thắng nhiều → weight cao hơn |
| Genome Evolution | Đột biến/lai ghép strategy tốt |
| ML Experience | Feature → outcome cho Logistic Regression |

**Chạy learning:**
```bash
python run_learning.py --epochs 5
python run_learning.py --reset   # xóa KB
```

**Cảnh báo:** Nhiều epoch trên **cùng dataset** → WR có thể tăng do overfit meta.
Luôn xác nhận bằng backtest **KB OFF** + hold-out.

**KB causal (v4.1):** Khi optimize tuần X, KB chỉ dùng kinh nghiệm **trước** tuần X.

---

## 9. Mục tiêu & constraints

| Mục tiêu | Ngưỡng |
|----------|--------|
| Win rate | > 60% (1 năm gần nhất) |
| RR | > 2 |
| Profitable | Total R > 0 |
| Tần suất | ~2 lệnh/tuần |

Checklist hiển thị ở Command Center & Backtest Lab.

---

## 10. Quy trình khuyến nghị (trước live)

1. **Refresh data** — cập nhật Dukascopy
2. **Backtest KB OFF** + spread/slippage thực tế
3. **Hold-out 12 tháng** — xem `holdout_forward`
4. **Trade Journal** — xem 20–30 lệnh mẫu, kiểm tra LONG bias
5. **Learning 2–5 epoch** (tùy chọn) → backtest lại KB OFF
6. **Paper Monitor** 3–6 tháng — so sánh với backtest
7. Chỉ live **micro lot** khi paper khớp

---

## 11. File quan trọng

```
run_gui.py / gui/app.py     # GUI
run_backtest.py             # Walk-forward
run_learning.py             # Self-learning
strategy_miner.py           # Mine + backtest
feature_engine.py           # Features
knowledge_base.py           # KB
data/eurusd_h1.parquet      # Cache giá
results/backtest_report.json
results/learning_report.json
learning/knowledge.json
```

---

## 12. Hạn chế đã biết

- Một pair / một timeframe (EUR/USD H1)
- Chưa kết nối broker API
- Intrabar SL/TP — thứ tự chạm có thể khác live
- RoR là ước lượng, không phải Monte Carlo đầy đủ
- Yahoo không dùng cho H1 lịch sử — dùng Dukascopy

---

## 13. FAQ

**Q: Kết quả 60% WR có vào live được không?**  
A: Chỉ sau paper + hold-out + spread. KB OFF phải vẫn profitable.

**Q: KB ON hay OFF?**  
A: **OFF** để đánh giá. **ON** khi muốn tận dụng kinh nghiệm đã học (có rủi ro overfit).

**Q: Tại sao nhiều lệnh LONG?**  
A: Miner có thể bias theo regime. Kiểm tra Trade Journal → Direction bias.

**Q: Backtest chậm?**  
A: ~2 phút cho 4 năm / 224 tuần. Dùng cache data, tránh refresh liên tục.

---

## 14. Liên hệ kiến trúc

```
Data → Features → Miner (+ML) → Walk-forward → Metrics
                      ↑
              KB / Evolution (optional)
```

*ForexForge v4 — Walk-forward strategy mining that learns from every trade.*
  """)

  with st.expander("Sơ đồ walk-forward (mermaid)"):
    st.code("""
graph LR
  A[Dukascopy H1] --> B[Features]
  B --> C[Train 3 tháng]
  C --> D[Mine Strategy]
  D --> E[Trade OOS tuần]
  E --> F[Metrics / KB]
  F --> C
    """, language="text")
