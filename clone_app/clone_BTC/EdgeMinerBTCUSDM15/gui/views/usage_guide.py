"""8. Usage Guide — hướng dẫn vận hành ForexForge."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header

_DOCS = Path(__file__).resolve().parents[2] / "docs"
_MINING_DOC = _DOCS / "mining_search_space.md"
_GRID_DOC = _DOCS / "grid_search.md"


def _render_doc_expander(title: str, path: Path, fallback: str) -> None:
  with st.expander(title, expanded=False):
    if path.exists():
      st.markdown(path.read_text(encoding="utf-8"))
    else:
      st.warning(f"Không tìm thấy `{path.name}`. {fallback}")


def _render_mining_search_space_doc() -> None:
  """Show full Mining search space doc inside the Usage Guide."""
  _render_doc_expander(
    "Mining search space — tài liệu đầy đủ",
    _MINING_DOC,
    "Mở file `docs/mining_search_space.md` trong repo.",
  )


def _render_grid_search_doc() -> None:
  """Show Grid Search parameter doc inside the Usage Guide."""
  _render_doc_expander(
    "Grid Search — tham số & combo (tài liệu đầy đủ)",
    _GRID_DOC,
    "Mở file `docs/grid_search.md` trong repo.",
  )


def render():
  render_page_header(ALL_ITEMS["guide"], show_workspace=False)

  from gui.glossary import render_glossary_guide
  render_glossary_guide()
  st.divider()

  st.markdown("""
## 1. ForexForge là gì?

**ForexForge** là hệ thống backtest & self-learning cho **BTC/USD khung M15**, gồm:

- **Walk-forward backtest** — train 3/6/9 tuần, re-optimize hàng tuần, trade OOS (không look-ahead)
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
| 1 | ForgeBridge đồng bộ **BTC/USD M15** từ XM MT5 → cache `data/mt5_btcusd_m15.parquet` |
| 2 | Tính **37+ features** causal (`feature_engine.py`) |
| 3 | Mỗi tuần: train 3/6/9 tuần trước → mine/optimize strategy |
| 4 | Trade **tuần OOS** (signal close bar *i*, entry open bar *i+1*) |
| 5 | Ghi metrics, trades → `results/backtest_report.json` |

---

## 4. Walk-forward (trái tim của app)

```
Timeline:  |---- train 3/6/9 tuần ----|-- OOS tuần --|
           ^                        ^
           không trade              chỉ trade ở đây

Tuần tiếp theo: train window trượt về phía trước, lặp lại.
```

**Quan trọng:**
- Tuần OOS **không nằm** trong cửa sổ train
- Features chỉ dùng quá khứ
- **KB OFF** = đánh giá trung thực nhất (khuyến nghị trước khi live)

---

## 5. Phân biệt Train theo tuần · KB · Epoch

Ba khái niệm này ở **các tầng khác nhau** — dễ nhầm vì đều liên quan “học”, nhưng mục đích và thời gian khác nhau.

### Tóm tắt

| | **Train 3/6/9 tuần** | **KB (Knowledge Base)** | **Epoch** |
|---|---|---|---|
| **Là gì** | Cửa sổ data để **mine strategy mỗi tuần** | **Bộ nhớ kinh nghiệm** tích lũy | **Một vòng học full** trên cả giai đoạn |
| **Tần suất** | Mỗi **tuần** OOS (walk-forward) | Dùng liên tục, cập nhật khi học | Chạy **thủ công** 3–5–8 lần |
| **Lưu gì** | Rules, RR, ML cho **tuần đó** | Genomes, rule stats, ML samples | Snapshot KB sau mỗi epoch |
| **Mục đích** | Strategy **phù hợp thị trường gần** | Mine **thông minh hơn** nhờ quá khứ | **Cải thiện dần** KB qua nhiều vòng |

### 1) Train 3/6/9 tuần — Walk-forward (lõi backtest)

**Không phải KB** — đây là cơ chế walk-forward:

```
Tuần 1 OOS:  |---- train N tuần trước ----| → mine strategy → trade tuần 1
Tuần 2 OOS:       |---- train N tuần ----| → mine lại    → trade tuần 2
```

- Mỗi tuần: lấy **3/6/9 tuần M15** ngay trước tuần OOS
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

Khi **KB ON**: vẫn train theo tuần, nhưng mine **ưu tiên** genomes/rules/ML từ KB (lọc `as_of` = đầu tuần).

```
Train 3/6/9 tuần = "học từ data gần"
KB            = "học từ kinh nghiệm nhiều tuần/tháng trước"
```

### 3) Epoch — Một vòng học toàn giai đoạn

**1 epoch** = chạy **full walk-forward** trên giai đoạn học (vd 2022–2023), rồi **cập nhật KB**.

```
Epoch 1: WF 2022–2023 → ghi vào KB (yếu)
Epoch 2: WF lại       → KB đã có kinh nghiệm epoch 1 → tốt hơn
Epoch 3: ...
```

- Epoch **không thay** train theo tuần — cửa sổ 3/6/9 tuần vẫn chạy **bên trong** mỗi tuần
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
- **Train 3/6/9 tuần** — luôn có, mỗi tuần, strategy ngắn hạn
- **KB** — bộ nhớ dài hạn; bật/tắt + chọn profile giai đoạn
- **Epoch** — học nhiều vòng để KB tốt hơn; snapshot = chọn phiên bản KB

---

## 5b. Mining search space (cách miner tìm edge)

Khác với **train weeks** (nhìn bao nhiêu tuần) và **KB** (đã nhớ gì), **Mining search space** quyết định miner **được phép tìm theo kiểu nào**: RR mục tiêu, exit full/trail, anti-chase RSI/VWAP, cách chấm genome…

```
Cài đặt (preset) → Grid Search → Trade Model lưu space → Live/Paper remine theo model active
```

- Mặc định app: preset **`elite_or_quality`** (void SHORT khi RSI≥58 **hoặc** VWAP≥1.5, RR 3.2–4, exit full).
- Đổi preset ở Cài đặt **chưa** đổi Live — cần Grid → tạo / chọn Trade Model mới.
- Xóa Trade Model **không** mất preset trong code hay KB; train lại được.

Tài liệu đầy đủ (tiếng Việt, chi tiết + FAQ): mở expander **Mining search space — tài liệu đầy đủ** bên dưới, hoặc file `docs/mining_search_space.md`.

---

## 5c. Grid Search dựa trên những tham số nào?

Grid = **tích Descartes** các trục từ **Cài đặt** (không quét từng knob RR/ATR riêng — các knobs đó nằm trong mining preset).

| Trục | Settings | Ví dụ gần đây |
|------|----------|---------------|
| Train weeks | `strategy_train_weeks` | `3, 6, 9` |
| KB profile | `learning_era_keys` | `era_2025_2026_6thang` |
| KB epoch | `learning_loops` → ep1…epN | `1–4` |
| Mining preset | `mining_presets` | `elite_or_quality` |
| OOS / spread / slip | `backtest_*`, phí | cố định cho mọi combo |

```
Số combo ≈ train × KB profile × epoch × mining_preset
(ví dụ 3 × 1 × 4 × 1 = 12; không gồm KB OFF)
```

- **`grid_objective`** chỉ xếp hạng winner — **không** nhân số combo.
- Đổi Cài đặt → Grid chỉ chạy **combo mới**.
- Học KB **không** phụ thuộc mining preset; preset khóa khi Grid/remine/Live.

Tài liệu đầy đủ: expander **Grid Search — tham số & combo** bên dưới, hoặc `docs/grid_search.md`.

---

## 6. Các trang GUI (theo quy trình)

| Trang | Mục đích |
|-------|----------|
| **Tổng quan** | Tiến độ, KPI, Refresh data |
| **Học & tối ưu** | ① Cài đặt → ② Huấn luyện KB → ③ Grid Search → ④ Trade Models (Quản lý · Rủi ro · Nhật ký · Chiến lược) |
| **Giám sát paper** | **Desk nhẹ** — mô phỏng tuần trên nến MT5, **không** gửi EA · cùng Trade Model |
| **MT5 Bridge** | **Live** (lệnh MT5) + **Simulate** (replay HISTORY_FEED) · cùng Trade Model |
| **Hướng dẫn** | Thuật ngữ & viết tắt · quy trình · FAQ |

**Trade Model**: chọn một lần trong **Học & tối ưu → Trade Models → Quản lý** — **Paper · Live · Simulate** dùng chung (`active_trade_model.json` + cùng `conditions_fp` remine).

### Ba mode · cùng Trade Model

| | **Paper** | **Live** (Bridge) | **Simulate** |
|---|---|---|---|
| **Là gì** | Remine tuần hiện tại trên desk app | Quyết định từng bar → EA mở/đóng | Replay đoạn quá khứ qua App↔EA |
| **Tiền** | Không | Có (demo/live) trên MT5 | Không (history feed) |
| **OUTPUT** | `paper_monitor_state.json` · paper journal | `bridge/trades.json` (fill) | `bridge_sim/trades.json` |
| **Khi dùng** | Theo dõi nhẹ, không bật EA | Vận hành thật + **Parity / Health OOS** | Nghi đường bridge / so khớp quá khứ |
| **Không dùng để** | Chứng minh Live đúng OOS | — | Thay Parity tuần live |

```
Trade Model active (một combo)
        │
        ├─► Paper service     → desk nhẹ (không EA)
        ├─► Bridge Live       → decision.json → EA → fill (kiểm bằng Parity)
        └─► Bridge Simulate   → HISTORY_FEED → cùng engine remine
```

**Quy tắc trader:** Kiểm Live kỳ vọng = **Parity tuần này** + Health OOS (và fill `trades.json`). Paper `SIGNAL`/`FILLED` ≠ lệnh MT5. Simulate không bắt buộc mỗi ngày.

### Remine hàng tuần tự động vs cập nhật Trade Model

**Trade Model** = snapshot cấu hình đã lưu (`train_weeks`, KB profile/epoch, OOS, KPI từ Grid).
App **không** tự đổi model trong danh sách mỗi tuần.

| Việc | Tự động? | Điều kiện |
|------|----------|-----------|
| **Remine strategy mỗi tuần** (mine lại trên cửa sổ train gần nhất → tín hiệu tuần mới) | Có | **Paper** và/hoặc **MT5 Bridge Live** Start service (cùng Trade Model) |
| Đồng bộ lịch sử MT5 | Có (EA chunk + bar live) | Tổng quan hoặc MT5 Bridge |
| **Huấn luyện KB** (epoch mới) | Không | Học & tối ưu → ② Huấn luyện |
| **Grid Search** xếp hạng combo mới | Không | Khi đổi Cài đặt hoặc muốn model khác |
| **Tạo / chọn Trade Model** | Không | Chỉ khi đổi combo active (vd Best 3m → model khác) |
| Export Replay / Frozen EA (MT5 Tester) | Không | Chạy script export khi cần lịch/EA mới |

**Vận hành hàng ngày / tuần:** chọn Trade Model một lần → bật **Live** (và tuỳ chọn Paper desk) → mỗi tuần app tự remine theo cấu hình đó. Dùng **Parity** để đối chiếu OOS. **Simulate** khi cần replay.  
**Chỉ** chạy lại KB → Grid → chọn model khi muốn đổi “bộ não” (KB mới, train window / OOS khác).

### MT5 Bridge — dùng thế nào?

Đây là cầu nối **MetaTrader 5** (không phải MT4):

1. Mở **MT5 Bridge** → chọn Trade Model (Best 3m) → cấu hình **Loss guard** (max thua liên tiếp / ngày·tuần) → **Start service**
2. Service chạy **process riêng** (không phụ thuộc tab GUI) — đổi tab / refresh page **không** dừng; bấm **Stop** mới tắt (hoặc Loss guard tự Stop)
3. Trên MT5: compile/attach EA `ForgeBridge`, `InpMode = Live` (thư mục `MQL5/Files/bridge`)
4. Mỗi M15 mới: EA ghi `bar.json` → App decide → `decision.json` → EA BUY/SELL hoặc FLAT
5. Remine Live = **cùng đường Health OOS / Simulate** (KB ON, full FeatureMatrix, cùng `conditions_fp`). Trên desk Live mở **Parity tuần này** để đối chiếu `strategy_name` với weekly_log Health.
6. **Paper** = desk nhẹ (không bắt buộc để chứng minh Live). **Simulate** = replay quá khứ App↔EA khi cần.
7. Xem **Nhật ký giao tiếp** trên GUI (`comm_log.jsonl`: `bar_received`, `decision_sent`, `fill_received`)
8. Xem **Thống kê lệnh Bridge** (thắng/thua, R, profit) — EA ghi `fill.json` open/close → App lưu `trades.json`

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
| Tần suất | 7–10 lệnh/tuần, tối đa 2 lệnh/ngày broker |

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
| 5 | **MT5 Bridge Live** (+ tuỳ chọn Paper / Simulate) | Start Live → remine · Parity vs Health · Paper desk nhẹ nếu muốn |

Chỉ live **micro lot** khi Live + Parity/Health khớp kỳ vọng backtest.

**Không cần Grid lại mỗi tuần** — Paper/Live/Sim tự remine theo Trade Model đang chọn. Grid/KB chỉ khi muốn cập nhật model.

**Mining space lỗi thời?** Trade Models → **Sức khỏe** → panel *Mining space vs baseline miner* (A/B cùng KB; khác với KB ON/OFF).

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
data/mt5_btcusd_m15.parquet # Cache M15 chuẩn từ ForgeBridge/XM MT5
mt5_bridge/                 # Bridge App ↔ MT5 EA
mt5/Experts/ForgeBridgeM15.mq5    # EA Live
mt5/Experts/ForgeBridgeM15Sim.mq5 # EA Simulate (HistoryFeed)
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

- Một pair / một timeframe (BTC/USD M15)
- Paper Monitor dùng cùng dữ liệu nến M15 từ broker với Grid và MT5 Bridge
- MT5 Bridge cần EA + service App chạy đồng thời; Wine/SSL login broker vẫn có thể fail trên Linux Docker
- Intrabar SL/TP — thứ tự chạm có thể khác live
- RoR là ước lượng, không phải Monte Carlo đầy đủ
- Không dùng nguồn giá ngoài; lịch sử và bar live đều đến từ ForgeBridge/XM MT5

---

## 15. FAQ

**Q: Kết quả 60% WR có vào live được không?**  
A: Chỉ sau hold-out + spread + **Live Parity / Health OOS** khớp kỳ vọng. KB OFF phải vẫn profitable. Paper desk là tuỳ chọn.

**Q: KB ON hay OFF?**  
A: **OFF** để đánh giá. **ON** khi muốn tận dụng kinh nghiệm đã học (có rủi ro overfit).

**Q: Tại sao nhiều lệnh LONG?**  
A: Miner có thể bias theo regime. Kiểm tra Trade Journal → Direction bias.

**Q: Backtest chậm?**  
A: ~2 phút cho 4 năm / 224 tuần. Dùng cache data, tránh refresh liên tục.

**Q: Quy trình nào nên làm trước?**  
A: KB OFF baseline → học KB era → OOS với profile → Report Compare → hold-out → **Live + Parity** (Paper desk tuỳ chọn).

**Q: App có tự optimize mỗi tuần không?**  
A: **Có remine strategy mỗi tuần** khi Paper và/hoặc Bridge Live đang chạy (cùng Trade Model). **Không** tự Grid / tạo model mới.

**Q: Paper · Live · Simulate khác nhau thế nào?**  
A: **Cùng Trade Model active**. Paper = desk nhẹ không EA. Live = lệnh MT5 + Parity vs Health. Simulate = replay App↔EA quá khứ. Xem bảng mục **6**.

**Q: Paper có `SIGNAL` thì MT5 có vào lệnh không?**  
A: Chỉ khi Bridge Live + EA đang chạy **đúng lúc bar tín hiệu đóng**. Paper `FILLED` ≠ lệnh MT5.

**Q: Có hỗ trợ MT4 không?**  
A: Không — chỉ **MT5** (`ForgeBridgeM15.mq5`).

**Q: Xem log giao tiếp App ↔ EA ở đâu?**  
A: GUI **MT5 Bridge** → Nhật ký giao tiếp, hoặc file `mt5/bridge/comm_log.jsonl`.

**Q: Loss guard trên Live là gì?**  
A: Cấu hình khi Start: dừng service nếu lệnh **auto** thua liên tiếp đạt ngưỡng trong **ngày** hoặc **tuần**. Mặc định ngưỡng = **⌊|Max DD model|⌋ + 1** (vd DD 11.35R → 12). Ghi FLAT + Stop. Start lại xóa cờ tripped.

**Q: Khác nhau Train theo tuần, KB và Epoch?**
A: **Train 3/6/9 tuần** = mine strategy mỗi tuần WF (luôn chạy). **KB** = bộ nhớ dài hạn (rules/genomes/ML). **Epoch** = một vòng học full giai đoạn để cải thiện KB. Xem mục **5** trong Usage Guide.

**Q: Mining search space là gì? Đổi Settings có đổi Live không?**
A: Là **cách miner được phép tìm edge** (RR, exit, anti-chase…), khác KB/train weeks. Mặc định: preset **`elite_or_quality`**. Đổi ở Cài đặt chỉ ảnh hưởng Grid; Live theo **Trade Model active**. Xem mục **5b** và `docs/mining_search_space.md`.

**Q: Grid Search dựa trên những tham số nào?**
A: Train weeks × KB profile × epoch × mining preset (+ OOS/spread/slip cố định). `grid_objective` chỉ xếp hạng, không nhân combo. Xem mục **5c** và `docs/grid_search.md`.

---

## 16. Kiến trúc

```
Data → Features → Miner (+ML) → Walk-forward → Metrics
                      ↑
              KB / Evolution (optional)
```

*ForexForge v4 — Walk-forward strategy mining that learns from every trade.*
  """)

  _render_mining_search_space_doc()
  _render_grid_search_doc()

  with st.expander("Sơ đồ Train theo tuần · KB · Epoch (mermaid)"):
    st.code("""
graph TD
  E[Epoch: học offline full giai đoạn] --> KB[KB Profile]
  KB --> WF[Mỗi tuần OOS]
  WF --> T[Train 3/6/9 tuần]
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
  A[XM MT5 M15] --> B[Features]
  B --> C[Train 3/6/9 tuần]
  C --> D[Mine Strategy]
  D --> E[Trade OOS tuần]
  E --> F[Metrics / KB]
  F --> C
    """, language="text")
