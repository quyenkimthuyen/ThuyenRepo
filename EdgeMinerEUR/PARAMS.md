# ForexForge — Tài liệu tham số

Tài liệu tham chiếu đầy đủ cho mọi tham số cấu hình trong app.  
Nguồn chính: `config.py`, `gui/app_settings.py`, `strategy_miner.py`, `run_backtest.py`.

**Cập nhật:** 2026-07-21 · Trade Model active: `tm_h_c_3_th_ng_h_c_2023_2025_v__0eddb767`

---

## Profile đã chốt (sau A/B)

Các giá trị dưới đây đã được so sánh walk-forward OOS 2025–2026 và chọn theo **ổn định** (WR cao, DD thấp), trừ khi ghi chú khác.

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| `reopt_period` | **week** | +130.7R vs monthly +116.7R |
| `max_trades_per_week` | **2** | Tốt hơn 1 lệnh/ngày về WR/PF/DD |
| `max_hold_bars` | **24** | WR 61.4%, DD 3.3R (vs 48 bars max R) |
| `min_bars_between` | **4** | +135.4R, PF 2.96 |
| `trail_activate_r` | **1.0** | Mode ổn định: WR 66.7%, DD 3.8R |
| `trail_distance_r` | **0.5** | |
| `spread_pips` | **1.0** | EUR/USD |
| `slippage_pips` | **0.3** | |

Kết quả A/B chi tiết: `results/max_hold_compare.json`, `results/exec_params_compare.json`, `results/reopt_compare.json`, `results/trade_quota_compare.json`.

---

## 1. Thị trường & dữ liệu (`config.py`)

| Tham số | Mặc định | Mô tả |
|---------|----------|--------|
| `DEFAULT_PAIR` | `EUR/USD` | Cặp tiền duy nhất |
| `DEFAULT_TF` | `H1` | Khung thời gian |
| `DEFAULT_START_DATE` | `2022-01-01` | Ngày bắt đầu tải Dukascopy |
| `MIN_TRAIN_BARS` | `500` | Tối thiểu bar để mine |

Cache giá: `data/eurusd_h1.parquet` (+ `data/eurusd_h1_meta.json`).

---

## 2. Walk-forward & học (`config.py`)

| Tham số | Mặc định | Mô tả |
|---------|----------|--------|
| `TRAIN_MONTHS` | `3` | Cửa sổ train mặc định (CLI) — GUI thử 3/6/9 |
| `TARGET_TRADES_PER_WEEK` | `2.0` | Mục tiêu tần suất lệnh khi chấm điểm strategy |
| `DEFAULT_HOLDOUT_MONTHS` | `0` | Tháng cuối giữ riêng (strict forward); `0` = tắt |

### `reopt_period`

| Giá trị | Ý nghĩa |
|---------|---------|
| `week` | Mine lại **mỗi tuần** — mặc định, bám thị trường |
| `month` | Mine **1 lần/tháng** — ít overfit, R thấp hơn |

Cấu hình GUI: **Cài đặt → Tần suất cập nhật chiến lược** (`results/app_settings.json` → `reopt_period`).

---

## 3. Phí mô phỏng (`config.py`)

| Tham số | Mặc định | Đơn vị | Mô tả |
|---------|----------|--------|--------|
| `DEFAULT_SPREAD_PIPS` | `1.0` | pip | Chênh lệch mua/bán (0.0001 EUR/USD) |
| `DEFAULT_SLIPPAGE_PIPS` | `0.3` | pip | Trượt giá khi khớp lệnh |

Áp dụng cho: backtest, grid search, paper monitor, MT5 export meta.

---

## 4. Risk dashboard (`config.py`)

| Tham số | Mặc định | Mô tả |
|---------|----------|--------|
| `DEFAULT_RISK_PCT_PER_TRADE` | `1.0` | % vốn risk mỗi lệnh (tính R, risk of ruin) |
| `DEFAULT_MAX_WEEKLY_LOSS_R` | `4.0` | Ngưỡng cảnh báo lỗ tuần (R) |

`run_walk_forward(..., risk_pct_per_trade=1.0)` — truyền vào `compute_metrics`.

---

## 5. Thực thi lệnh — đã lock (`config.py`)

### Max hold (H1 bars)

| Tham số | Giá trị | Grid miner |
|---------|---------|------------|
| `DEFAULT_MAX_HOLD_BARS` | **24** | `MAX_HOLD_GRID = [24, 36, 48]` |

Đóng lệnh tự động sau N bar nếu chưa chạm SL/TP.

### Khoảng cách giữa lệnh

| Tham số | Giá trị | Grid miner |
|---------|---------|------------|
| `DEFAULT_MIN_BARS_BETWEEN` | **4** | `MIN_BARS_BETWEEN_GRID = [2, 4, 6]` |

Số bar H1 tối thiểu giữa hai entry.

### Trail hybrid (exit mode `hybrid`)

| Tham số | Giá trị | Mô tả |
|---------|---------|--------|
| `DEFAULT_TRAIL_ACTIVATE_R` | **1.0** | Bật trail khi lời ≥ 1R |
| `DEFAULT_TRAIL_DISTANCE_R` | **0.5** | SL trail cách đỉnh 0.5R |

Miner chỉ dùng `HYBRID_TRAIL_GRID` (1 cặp stable).  
So sánh A/B đầy đủ: `HYBRID_TRAIL_COMPARE_GRID` trong `scripts/compare_exec_params.py`.

---

## 6. Chiến lược — `MinedStrategy` (`strategy_miner.py`)

Các field được mine hoặc gán khi walk-forward. Giá trị **mặc định struct** (trước khi mine):

| Field | Mặc định | Mine grid / ghi chú |
|-------|----------|------------------------|
| `long_rules` / `short_rules` | `[]` | Tối đa 6 rule/mỗi phía; continuous + binary features |
| `score_threshold` | `2.0` | `[0.6, 1.0, 1.6, 2.2]` |
| `atr_mult_sl` | `0.9` | `[0.9, 1.05]` — hệ số ATR cho SL |
| `rr_ratio` | `2.5` | `[2.5, 3.0]` — risk:reward TP |
| `max_hold_bars` | `24` | `MAX_HOLD_GRID` |
| `min_bars_between` | `4` | `MIN_BARS_BETWEEN_GRID` |
| `min_rules_match` | `2` | `[1, 2]` — số rule tối thiểu khớp |
| `max_trades_per_week` | `2` | Cố định khi mine |
| `max_trades_per_day` | `0` | `0` = tắt; `>0` override quota tuần |
| `ml_prob_min` | `0.40` | `[0.36, 0.40, 0.44, 0.48]` |
| `exit_mode` | `"trail"` | `full`, `hybrid` (1 cặp trail), `partial` |
| `partial_pct` | `0.4` | Chỉ `partial`: % đóng sớm |
| `partial_at_r` | `1.2` | Chỉ `partial`: đóng một phần tại XR |
| `trail_activate_r` | `1.0` | Từ `DEFAULT_TRAIL_*` |
| `trail_distance_r` | `0.5` | |
| `session_filter` | `True` | Lọc phiên London/NY |
| `ml_scorer` | `None` | ML filter logistic — fit mỗi cửa sổ train |
| `name` | `"mined_v3"` | Tên genome |

### Exit modes

| Mode | Hành vi |
|------|---------|
| `full` | Giữ đến TP/SL/max_hold |
| `hybrid` | Partial logic + trail sau `trail_activate_r` |
| `partial` | Chốt một phần tại `partial_at_r`, phần còn lại full/trail |
| `trail` | Trail thuần (legacy default field) |

### Features dùng khi mine

**Continuous:** `rsi`, `adx`, `bb_pos`, `bb_width_pct`, `atr_pct`, `zscore_20`, `price_vs_ema21`, `price_vs_ema50`, `ema_slope_8`, `ema_slope_21`, `macd_hist`, `roc_5`, `body_ratio`, `lower_wick_ratio`, `upper_wick_ratio`

**Binary long:** `sweep_low_fade`, `squeeze_break_up`, `pullback_long`, `range_buy`, `engulf_bull`, `macd_cross_up`, `ema_stack_bull`

**Binary short:** `sweep_high_fade`, `squeeze_break_dn`, `pullback_short`, `range_sell`, `engulf_bear`, `macd_cross_dn`, `ema_stack_bear`

---

## 7. Cài đặt GUI (`gui/app_settings.py` → `results/app_settings.json`)

| Key | Mặc định | Mô tả |
|-----|----------|--------|
| `strategy_train_months` | `[3, 6, 9]` | Cửa sổ train — grid thử từng giá trị |
| `learning_era_keys` | `["2022-2025", "2023-2025", "2024-2025"]` | Giai đoạn học KB |
| `learning_loops` | `4` | Số epoch/vòng học mỗi era (1–12) |
| `backtest_from` | `2025-01-01` | OOS bắt đầu |
| `backtest_to` | `2026-12-31` | OOS kết thúc |
| `spread_pips` | `1.0` | |
| `slippage_pips` | `0.3` | |
| `grid_objective` | `total_r` | `total_r` \| `win_rate_pct` \| `profit_factor` \| `risk_adjusted` |
| `reopt_period` | `week` | `week` \| `month` |

### Giai đoạn học (`LEARNING_ERA_OPTIONS`)

| Key | KB profile | Học từ | Học đến |
|-----|------------|--------|---------|
| `2022-2025` | `era_2022_2025` | 2022-01-01 | 2025-12-31 |
| `2023-2025` | `era_2023_2025` | 2023-01-01 | 2025-12-31 |
| `2024-2025` | `era_2024_2025` | 2024-01-01 | 2025-12-31 |

Quy tắc: `trained_to ≤ oos_from` — app kiểm tra leakage.

---

## 8. Walk-forward API (`run_walk_forward`)

| Tham số | Mặc định | Mô tả |
|---------|----------|--------|
| `use_learning` | `True` | Bật Knowledge Base |
| `train_months` | `3` | Cửa sổ train mỗi kỳ reopt |
| `spread_pips` / `slippage_pips` | `1.0` / `0.3` | |
| `holdout_months` | `0` | Forward test strict cuối dataset |
| `risk_pct_per_trade` | `1.0` | |
| `kb_profile` | `default` | ID profile (`era_2023_2025`, …) |
| `kb_snapshot` | `latest` | Epoch snapshot (`1`, `2`, …) |
| `oos_from` / `oos_to` | `None` | Giới hạn OOS |
| `reopt_period` | `week` | |
| `max_trades_per_day` | `0` | Override quota (A/B only) |
| `max_hold_bars` | `None` | Override cố định (A/B) |
| `min_bars_between` | `None` | Override cố định (A/B) |
| `trail_hybrid` | `None` | `(activate_r, distance_r)` — force hybrid |

### CLI `run_backtest.py`

```bash
python run_backtest.py \
  --no-kb \
  --spread 1.0 --slippage 0.3 \
  --holdout-months 0 \
  --kb-profile era_2023_2025 --kb-epoch 1 \
  --oos-from 2025-01-01 --oos-to 2026-12-31 \
  --reopt-period week
```

---

## 9. Paper Monitor (`results/paper_monitor_config.json`)

| Key | Mặc định | Mô tả |
|-----|----------|--------|
| `enabled` | `false` | Tự chạy khi `interval_minutes > 0` |
| `interval_minutes` | `0` | Chu kỳ quét (phút) |
| `use_learning` | `false` | Dùng KB khi mine tuần hiện tại |
| `kb_profile` | `default` | Profile KB |
| `kb_snapshot` | `null` | Epoch snapshot |
| `spread_pips` | `1.0` | |
| `slippage_pips` | `0.3` | |
| `running` | — | Trạng thái runtime |
| `last_run_at` / `next_run_at` | — | Timestamp |

Paper dùng **Trade Model active** + cấu hình trên.

---

## 10. Trade Model

Lưu tại `results/trade_models.json`, báo cáo đầy đủ `results/trade_models/{id}.json`.

| Field (model record) | Mô tả |
|----------------------|--------|
| `id` | `tm_...` |
| `label` | Tên hiển thị (train, era, epoch, OOS, R) |
| `train_months` | Cửa sổ train đã chọn |
| `use_kb` | KB on/off |
| `kb_profile` | Era profile |
| `kb_snapshot` | Epoch |
| `oos_from` / `oos_to` | Kiểm chứng |
| `spread_pips` / `slippage_pips` | |
| `reopt_period` | week/month |
| `metrics` | WR, R, DD, PF, … |

Active model: `results/active_trade_model.json` → `id`.

---

## 11. Knowledge Base

| Tham số | Mô tả |
|---------|--------|
| Profile file | `learning/kb_profiles/{era}.json` |
| Snapshot | `learning/kb_profiles/snapshots/{era}/epNNN.json` |
| `MAX_GENOMES` | Giới hạn genome lưu (trong `knowledge_base.py`) |
| Genome fields | Rules, RR, exit, trail, fitness, … |

`dict_to_strategy` fallback trail: `DEFAULT_TRAIL_ACTIVATE_R` / `DEFAULT_TRAIL_DISTANCE_R` (không còn 1.8/0.6).

---

## 12. MT5 Expert Advisor export

```bash
python scripts/export_mt5_ea.py
python scripts/export_mt5_ea.py --model-id tm_xxx
python scripts/export_mt5_ea.py --no-remine   # dùng last_strategy đã cache
```

Output: `mt5/output/` — `ForexForgeEA.mq5`, `Include/ForgeConfig.mqh`, `forge_export.json`.

### `#define` trong `ForgeConfig.mqh`

| Define | Nguồn |
|--------|--------|
| `FORGE_SCORE_THRESHOLD` | strategy |
| `FORGE_ML_PROB_MIN` | strategy |
| `FORGE_MIN_RULES_MATCH` | strategy |
| `FORGE_MIN_BARS_BETWEEN` | default **4** |
| `FORGE_MAX_TRADES_WEEK` | default **2** |
| `FORGE_MAX_HOLD_BARS` | default **24** |
| `FORGE_RR` | strategy (mined 2.5 hoặc 3.0) |
| `FORGE_ATR_MULT` | strategy |
| `FORGE_EXIT_MODE` | `full` / `hybrid` / `partial` |
| `FORGE_SESSION_FILTER` | 0/1 |
| `FORGE_PARTIAL_PCT` / `FORGE_PARTIAL_AT_R` | partial exit |
| `FORGE_TRAIL_ACTIVATE_R` | default **1.0** |
| `FORGE_TRAIL_DISTANCE_R` | default **0.5** |
| `FORGE_SPREAD_PIPS` / `FORGE_SLIPPAGE_PIPS` | meta |
| `FORGE_LONG_RULES_*` / `FORGE_SHORT_RULES_*` | rules arrays |
| `FORGE_ML_*` | ML model (thường disabled trên MT5) |

**Lưu ý:** Export mine lại strategy **tuần hiện tại** (`remine=True`). `exit_mode` có thể là `full` nếu miner chọn full cho tuần đó; trail defaults vẫn embed cho hybrid.

---

## 13. Scripts so sánh A/B

| Script | Tham số test | Kết quả |
|--------|--------------|---------|
| `scripts/compare_reopt_period.py` | week vs month | `results/reopt_compare.json` |
| `scripts/compare_trade_quota.py` | 2/week vs 1/day | `results/trade_quota_compare.json` |
| `scripts/compare_max_hold.py` | 24/36/48 | `results/max_hold_compare.json` |
| `scripts/compare_exec_params.py` | min_bars + trail | `results/exec_params_compare.json` |

---

## 14. Ràng buộc mục tiêu hệ thống

Backtest báo cáo `constraints_met`:

| Constraint | Điều kiện |
|------------|-----------|
| `win_rate_above_60` | WR 1 năm ≥ 60% |
| `rr_above_2` | Avg RR 1 năm ≥ 2 |
| `profitable` | Total R 1 năm > 0 |
| `trades_per_week_near_2` | 1.2 ≤ lệnh/tuần ≤ 3.0 |

---

## 15. File cấu hình — tra cứu nhanh

| File | Nội dung |
|------|----------|
| `config.py` | Default toàn cục, grid miner |
| `results/app_settings.json` | Cài đặt GUI |
| `results/active_trade_model.json` | Model đang dùng |
| `results/paper_monitor_config.json` | Paper monitor |
| `mt5/output/forge_export.json` | Export MT5 gần nhất |
| `gui/glossary.py` | Help text UI (tiếng Việt) |

---

*ForexForge — tham số thay đổi theo `config.py` và `results/app_settings.json`. Sau khi đổi default execution, chạy lại grid hoặc ít nhất re-export MT5.*
