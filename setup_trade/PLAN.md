# Setup Trade — Kế hoạch xây dựng app trading thực chiến

> **Mục tiêu:** Xây dựng app có thể dùng để **nghiên cứu, kiểm chứng và vận hành** chiến lược forex (bắt đầu EURUSD H1) với backtest **đáng tin**, walk-forward **sạch**, và pipeline label **nhất quán** — hướng tới kiếm lời bền vững, không chỉ UI đẹp.

> **Nguồn:** Kế thừa ưu điểm từ `AI_Trade/`, khắc phục toàn bộ nhược điểm đã review (legacy rối, alignment thấp, OOS không sạch, PF fail, thiếu test).

**Phiên bản plan:** 1.0  
**Ngày:** 2026-07-12  
**Repo mới:** `/home/toc/thuyen/repo/setup_trade`  
**Repo tham chiếu:** `/home/toc/thuyen/repo/AI_Trade`

---

## 1. Tầm nhìn & tiêu chí thành công

### 1.1 App là gì (và không là gì)

| Là | Không là |
|----|----------|
| Công cụ **research → validate → paper → live** một chiến lược rõ ràng | “AI tự tìm edge” mơ hồ |
| Label có **gate khớp rule** trước khi lưu | Gắn tag tùy ý rồi hy vọng analyze cứu |
| Backtest **cùng logic** với rule live | Label SL/TP tay khác engine backtest |
| Báo cáo trader: equity, DD, setup breakdown, ý nghĩa thống kê | Chỉ một con số PF |

### 1.2 Tiêu chí “đủ trade thật” (Definition of Done — sản phẩm)

Trước khi nối broker / chạy tiền thật, app phải đạt **tất cả**:

1. **Walk-forward sạch:** Train label năm T → optimize trên T+1 → báo cáo final trên T+2 (chưa từng optimize).
2. **Alignment label ≥ 70%** trên tập train trước khi coi Analyze hợp lệ.
3. **Out-of-sample PASS** (năm final): PF ≥ 1.3, ≥ 30 lệnh, max DD ≤ 250 pips (hoặc % equity), expectancy > 0.
4. **Robustness:** Monte Carlo / bootstrap trên chuỗi lệnh — PF median ≥ 1.1, worst-case DD trong ngưỡng chấp nhận.
5. **Paper trade 3 tháng:** Tín hiệu live khớp backtest (cùng bar close, cùng RSI H4 sync), log lệch < 5%.
6. **Test tự động:** CI chạy smoke + backtest deterministic trên fixture CSV.

### 1.3 Tiêu chí lợi nhuận (trader — thực tế)

- **Giai đoạn 1 (R&D):** Chứng minh edge trên EURUSD H1, 1–2 chiến lược, spread 1.0 + slippage 0.2 pips.
- **Giai đoạn 2 (vận hành):** Risk cố định 0.5–1% / lệnh, max 2 lệnh/tuần cùng setup, dừng tuần nếu DD > 3R.
- **Không kỳ vọng:** PF 2.0 trên 30 lệnh = “giàu” — coi đó là nhiễu cho đến khi lặp lại trên ≥ 2 năm OOS.

---

## 2. Kế thừa từ AI_Trade (giữ lại)

| Thành phần | Lý do giữ |
|------------|-----------|
| Chart Lightweight + RSI H4 panel đồng bộ | Đúng cách trader đọc chart |
| Split train / validation / backtest theo năm | Walk-forward đúng hướng |
| Registry chiến lược (`strategy_id` → module) | Mở rộng nhiều chiến lược sạch |
| Label setup: entry / SL / TP trên chart | Discretionary → systematic |
| Quality score setup (~50/năm) | Tránh over-label |
| Spread + slippage trong backtest | Gần thực tế hơn zero-cost |
| Workflow UI: Chiến lược → Label → Analyze → Backtest | Đúng tư duy vận hành |

---

## 3. Khắc phục (từ review — bắt buộc)

| Vấn đề AI_Trade | Giải pháp Setup Trade |
|-----------------|----------------------|
| Legacy similarity / score / tag_driven song song rule | **Một engine duy nhất:** rule-based state machine |
| Alignment label ~12% | **Label gate** + preview rule trước khi lưu |
| train_2024 optimize trên bt_2024 (cùng năm) | **Quy tắc OOS cứng** trong config + UI chặn |
| Label win/loss ≠ backtest PnL | **Cùng simulator** cho label outcome & backtest |
| Optimizer greedy, bar_stride=2 | Grid/Bayesian trên full bars; walk-forward nested |
| Không test | pytest + CI smoke |
| app.js monolith 2500 dòng | Tách module ES: `chart/`, `workflow/`, `reports/` |
| README lệch | Docs đồng bộ với từng phase |
| PF fail (0.44 / 0.82) | Chiến lược v1 theo spec trader (Note.txt), không đổi rule liên tục |

---

## 4. Chiến lược v1 — spec trader (cố định)

> Chi tiết đầy đủ trong `AI_Trade/Note.txt`. Đây là **một** chiến lược duy nhất cho Phase 1–3.

### 4.1 Vùng RSI H4

| Vùng | Band | Vai trò |
|------|------|---------|
| Thấp | 28–32 | TP SHORT / đáy sóng |
| Giữa | 48–52 | S/R — mốc 50 |
| Cao | 68–72 | TP LONG / đỉnh sóng |

### 4.2 EMA H1 (filter chung)

- **LONG:** Giá giữ hỗ trợ EMA50 và/hoặc EMA200 (pullback chạm EMA rồi bật).
- **SHORT:** Giá giữ kháng cự EMA50 và/hoặc EMA200.

### 4.3 Bốn setup (state machine)

| ID | Tên | LONG | SHORT |
|----|-----|------|-------|
| `s1_break_retest` | Break vùng 50 → retest | Vượt 52 → hồi 48–52 → bật lên | Thủng 48 → hồi 48–52 → bật xuống |
| `s2_extreme_bounce` | Chạm 70/30 → hồi 50 → bật | Trên 50 → chạm 68–72 → hồi 48–52 (lần 1–2) → bật | Dưới 50 → chạm 28–32 → hồi 48–52 (lần 1–2) → bật |

**TP:** LONG → band 68–72; SHORT → band 28–32.  
**SL:** Thủng band 48 (long) / 52 (short) trên RSI H4 **hoặc** mất EMA H1 (configurable).

### 4.4 Quy tắc implement (phải chốt trước code)

- [ ] RSI H4: dùng nến H4 **đóng** (không intrabar H1 giả).
- [ ] “Chạm band”: wick hay close trong band? (đề xuất: **close H4** trong band).
- [ ] “Thủng”: close ngoài band ≥ 1 nến H4.
- [ ] Đếm lần chạm 48–52: reset khi nào? (đề xuất: reset khi RSI H4 ra khỏi mid band > N nến).
- [ ] Entry H1: tại **close nến H1** sau khi state machine báo `ENTRY_READY`.

---

## 5. Kiến trúc hệ thống

```
setup_trade/
├── backend/
│   ├── core/           # config, periods, indicators (H1 + H4 RSI native)
│   ├── data/           # CSV load, resample H4, cache
│   ├── strategy/
│   │   ├── base.py     # Protocol: detect_state, entry_signal, sl_tp
│   │   └── rsi_ema_v1/ # state machine 4 setup (Note.txt)
│   ├── simulator/      # MỘT engine: label outcome + backtest + paper
│   ├── research/       # analyze, alignment, recommendations, optimize
│   ├── reports/        # metrics, equity, monte carlo, breakdown
│   ├── api/            # FastAPI routes mỏng
│   └── tests/          # pytest bắt buộc
├── frontend/
│   ├── src/
│   │   ├── chart/
│   │   ├── workflow/
│   │   ├── strategy/
│   │   ├── label/
│   │   └── reports/
│   └── index.html
├── config/
│   ├── periods.json    # train/val/test — KHÔNG trùng năm
│   ├── strategy_rsi_ema_v1.json
│   └── costs.json
├── data/
│   ├── market/eurusd_h1.csv
│   └── labels/
├── docs/
│   ├── WORKFLOW.md
│   ├── STRATEGY_RSI_EMA_V1.md
│   └── BACKTEST_STANDARD.md
└── scripts/
    ├── fetch_data.py
    └── run_backtest_cli.py
```

### 5.1 Nguyên tắc kiến trúc

1. **Single simulator** — `simulator/trade.py` là nguồn sự thật cho win/loss và PnL.
2. **State machine rõ ràng** — mỗi setup = file states + transitions + unit test fixture.
3. **Không sklearn / similarity** trong v1 — chỉ thêm khi v2 có nhu cầu ML.
4. **API mỏng** — logic trong `backend/`, không trong route handlers.
5. **Config-driven** — band, EMA tolerance, cooldown đều từ JSON có schema.

---

## 6. Walk-forward chuẩn (bắt buộc trong config)

```json
{
  "folds": [
    {
      "id": "fold_a",
      "label_year": 2022,
      "optimize_year": 2023,
      "final_test_year": 2024
    },
    {
      "id": "fold_b",
      "label_year": 2024,
      "optimize_year": 2025,
      "final_test_year": 2026
    }
  ],
  "rules": {
    "forbid_optimize_same_year_as_label": true,
    "forbid_backtest_on_label_year": true
  }
}
```

**UI:** Dropdown chỉ hiện năm hợp lệ; cảnh báo đỏ nếu user chọn sai.

---

## 7. Pipeline người dùng (v1)

```
① Định nghĩa chiến lược (config + diagram)
        ↓
② Label trên chart (gate: phải khớp state machine)
        ↓
③ Analyze — alignment, stats theo setup, gợi ý tắt setup yếu
        ↓
④ Optimize — CHỈ trên optimize_year (nested trong fold)
        ↓
⑤ Backtest final — final_test_year (một lần, không chỉnh tiếp)
        ↓
⑥ Báo cáo — equity, DD, Monte Carlo, breakdown
        ↓
⑦ Paper trade — log tín hiệu vs backtest
        ↓
⑧ Live (phase sau) — risk module, broker adapter
```

### 7.1 Label gate (tính năng then chốt)

Khi user click “Lưu setup”:

1. Chạy `strategy.detect_at(entry_time)` → trả về `setup_id`, `direction`, `state_snapshot`.
2. Nếu `setup_id == null` hoặc direction lệch → **chặn lưu**, hiện lý do + overlay trên chart.
3. Nếu khớp → lưu kèm `state_snapshot` (JSON) để audit sau này.
4. Win/loss label = chạy **cùng simulator** với SL/TP rule (không dùng SL/TP tay trừ khi mode `discretionary_override`).

### 7.2 Màn hình báo cáo trader (bắt buộc)

- Equity curve (pips hoặc R)
- Drawdown curve
- Bảng theo setup_id: trades, WR, PF, expectancy, avg hold bars
- Bảng theo tháng
- Phân phối R-multiple (histogram)
- Monte Carlo: PF percentiles, max DD percentiles
- Banner: “30 lệnh chưa đủ ý nghĩa thống kê” nếu N < 50

---

## 8. Roadmap theo phase

### Phase 0 — Nền móng (2 tuần)

**Mục tiêu:** Repo sạch, data đúng, CI xanh.

| Task | Deliverable |
|------|-------------|
| Scaffold repo | Cấu trúc thư mục, `requirements.txt`, `run.sh` |
| Copy & làm sạch data pipeline | H1 CSV + resample H4 RSI **native** |
| `periods.json` walk-forward | Không trùng năm label/optimize/test |
| pytest smoke | `/health`, load candles, 1 indicator sanity |
| `docs/BACKTEST_STANDARD.md` | Quy ước cost, entry bar, SL/TP |

**Exit criteria:** `pytest` pass; API trả candles + RSI H4 khớp tay tính trên 10 nến mẫu.

---

### Phase 1 — Strategy engine (3 tuần)

**Mục tiêu:** State machine 4 setup chạy đúng spec Note.txt.

| Task | Deliverable |
|------|-------------|
| `strategy/rsi_ema_v1/states.py` | Enum states + transitions |
| Unit test từng setup | Fixture JSON: given RSI/EMA series → expect signal |
| `simulator/trade.py` | Walk forward bar, TP/SL theo RSI band + EMA |
| CLI `run_backtest_cli.py` | Chạy backtest không UI, in metrics |

**Exit criteria:** 20+ unit tests pass; backtest 1 năm chạy < 30s; log mẫu 5 lệnh inspect tay được.

---

### Phase 2 — Label app (3 tuần)

**Mục tiêu:** Label có gate, chart dùng được hàng ngày.

| Task | Deliverable |
|------|-------------|
| Chart H1 + RSI H4 (port từ AI_Trade, tách module) | `frontend/src/chart/` |
| Label gate API | `POST /api/setups` validate qua engine |
| Workflow strip + context bar | Port + đơn giản hóa |
| Bỏ legacy UI | Ẩn score/sequence/similarity |
| Lưu `state_snapshot` trên mỗi setup | Audit alignment |

**Exit criteria:** Không lưu được setup lệch rule; alignment trên label mới ≥ 90%.

---

### Phase 3 — Research & optimize (2 tuần)

**Mục tiêu:** Analyze + optimize đáng tin.

| Task | Deliverable |
|------|-------------|
| `research/analyze.py` | Alignment, by_setup stats, recommendations |
| `research/optimize.py` | Grid trên optimize_year only; nested CV optional |
| Tự tắt setup WR < 38% (≥5 mẫu) | Ghi vào strategy JSON + log |
| Báo cáo HTML/PDF export | Equity + Monte Carlo |

**Exit criteria:** Optimize không chạm final_test_year; báo cáo đủ section trader.

---

### Phase 4 — Validation thực chiến (4 tuần — song song label)

**Mục tiêu:** Chứng minh edge OOS.

| Tuần | Việc |
|------|------|
| 1–2 | Label 50 setup/fold trên label_year (chỉ khi gate pass) |
| 3 | Analyze + optimize trên optimize_year |
| 4 | Backtest **một lần** final_test_year + Monte Carlo |

**Exit criteria fold:** Final PASS theo mục 1.2; nếu fail → sửa **rule** hoặc **filter**, không tinh chỉnh thêm trên final year.

---

### Phase 5 — Paper & live prep (4 tuần)

| Task | Deliverable |
|------|-------------|
| Paper trade module | Log signal mỗi H1 close, so sánh backtest |
| Risk module | % risk, max daily DD, max positions |
| Broker adapter interface | `BrokerPort` — implement mock trước |
| Alert (Telegram/email optional) | Tín hiệu ENTRY_READY |

**Exit criteria:** 3 tháng paper khớp backtest; risk rules không vi phạm.

---

### Phase 6 — Live (sau khi Phase 4–5 pass)

- Micro lot / demo broker
- Journal tự động mỗi lệnh
- Kill switch: dừng bot nếu DD tuần > X R

---

## 9. Tham số optimize (giới hạn — tránh overfit)

Chỉ optimize các tham số **ít nguy hiểm**:

| Tham số | Grid gợi ý | Ghi chú |
|---------|------------|---------|
| `ema_tolerance_atr` | 0.25 – 0.55 | Khoảng cách giá–EMA |
| `entry_cooldown_bars` | 12 – 48 | H1 bars |
| `mid_touch_max` (setup 2) | 1 – 2 | Cố định 2 nếu spec không đổi |
| `sl_on_ema_break` | true/false | Boolean |

**Không optimize trong v1:** band RSI (28/32/48/52/68/72) — đó là spec trader, đổi = chiến lược khác.

---

## 10. Metrics & PASS criteria (chuẩn hóa)

```python
PASS = (
    trades >= 30
    and profit_factor >= 1.3
    and max_drawdown_pips <= 250
    and expectancy_pips > 0
    and monte_carlo_pf_p5 >= 1.0  # 5th percentile PF
)
```

Hiển thị thêm (không PASS cứng):

- Sharpe trên chuỗi R (annualized approx)
- Max consecutive losses
- Profit per month stability

---

## 11. Tech stack

| Layer | Chọn |
|-------|------|
| Backend | Python 3.11+, FastAPI |
| Data | pandas, numpy |
| Test | pytest, pytest-cov (target 80% core) |
| Frontend | Vanilla ES modules (hoặc Vite nếu cần build) |
| Chart | Lightweight Charts |
| CI | GitHub Actions: lint + pytest |
| DB (optional phase 2+) | SQLite cho labels + run history |

---

## 12. Migration từ AI_Trade

| Mang sang | Không mang |
|-----------|------------|
| `eurusd_h1.csv`, splits concept | `bar_importance` similarity backtest |
| Chart UX, RSI panel sync | `tag_driven`, `global` rules |
| labels/setups.json (sau re-label) | Legacy `train_2024.json` root |
| strategy_registry pattern | sklearn decision tree analyze |
| quality.json scoring (điều chỉnh) | app.js monolith nguyên khối |

**Bước migrate label:** Không import 100 setup cũ — alignment 12% sẽ poison research. Label lại trên gate mới hoặc script auto-tag chỉ khi gate pass.

---

## 13. Rủi ro & giảm thiểu

| Rủi ro | Giảm thiểu |
|--------|------------|
| Overfit optimize | Chỉ 4 tham số; final year chạm 1 lần |
| RSI H4 sync sai | Native H4 bars, test so khớp MT4/TradingView |
| Trader label lệch mắt | Gate + preview bắt buộc |
| PF cao do may mắn | Monte Carlo + 2 folds walk-forward |
| Scope creep | v1 chỉ 1 strategy; EMA cross để v2 |
| Không kiếm lời | Chấp nhận: app chỉ **chứng minh** edge; profit cần kỷ luật + đủ N |

---

## 14. Checklist trước mỗi release

- [ ] `pytest` pass
- [ ] `docs/` khớp behavior
- [ ] Walk-forward config không có năm trùng
- [ ] Không còn code path similarity trong backtest mặc định
- [ ] Sample backtest report đính kèm trong `docs/samples/`
- [ ] Version tag + changelog

---

## 15. Ưu tiên tuần đầu (action items)

1. Tạo repo scaffold + `config/periods.json` walk-forward sạch.
2. Implement `indicators/rsi_h4.py` — RSI trên nến H4 thật, merge vào H1 view.
3. Viết `strategy/rsi_ema_v1/test_s1_long.py` — 1 fixture break+retest long.
4. Viết `simulator/trade.py` skeleton — 1 lệnh long, TP RSI band.
5. `docs/STRATEGY_RSI_EMA_V1.md` — copy spec từ Note.txt + quy ước close/wick.

---

## 16. Tài liệu kèm theo (tạo dần theo phase)

| File | Nội dung |
|------|----------|
| `docs/WORKFLOW.md` | Hướng dẫn user từng tab |
| `docs/STRATEGY_RSI_EMA_V1.md` | Spec 4 setup + diagram |
| `docs/BACKTEST_STANDARD.md` | Cost, entry, SL/TP, no lookahead |
| `docs/LABEL_GATE.md` | Khi nào được lưu setup |
| `docs/DECISIONS.md` | ADR: tại sao bỏ similarity, v.v. |

---

## 17. Kết luận

**Setup Trade** không phải AI_Trade thêm vài nút — mà là **hệ thống có một sự thật duy nhất** (state machine + simulator), **một quy trình walk-forward sạch**, và **label chỉ khi rule khớp**. UI đẹp là phụ; **PF trên năm chưa đụng tới** mới là thước đo.

Nếu Phase 4 fail trên cả 2 folds: quay lại spec trader (filter trend, session London/NY, bỏ setup 2 lần chạm 3…) — **không** thêm layer ML để cứu PF.

---

*Plan maintainer: cập nhật file này khi chốt quy ước close/wick và kết quả fold đầu tiên.*
