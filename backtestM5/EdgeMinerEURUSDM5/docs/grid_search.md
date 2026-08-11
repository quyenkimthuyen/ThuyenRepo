# Grid Search — các tham số & cách sinh combo

Grid Search quét **tích Descartes** các trục lấy từ **Cài đặt** (`results/app_settings.json`). Mỗi combo = một walk-forward backtest (remine theo tuần trên cửa sổ train + KB snapshot, đo trên OOS).

Liên quan: [Mining search space](mining_search_space.md) (một trục của Grid) · `gui/grid_search_engine.py` · `gui/app_settings.py`.

---

## 1. Các trục quét

| Trục | Key Settings | Ý nghĩa |
|------|--------------|---------|
| **Train weeks** | `strategy_train_weeks` | Cửa sổ học mỗi tuần WF (thường `3 / 6 / 9`) |
| **KB profile (era)** | `learning_era_keys` → `kb_profile` | Bộ nhớ dài hạn đã học (vd `era_2025_2026_6thang`) |
| **KB epoch** | `learning_loops` → ep1…epN | Snapshot KB sau vòng học thứ N |
| **Mining preset** | `mining_presets` | Search space miner (vd `elite_or_quality`) |
| **OOS window** | `backtest_from` / `backtest_to` | Khoảng kiểm chứng (cố định cho mọi combo) |
| **Spread / slip** | `spread_pips` / `slippage_pips` | Phí mô phỏng (cố định cho mọi combo) |

### Công thức số combo

```
train × KB profile × epoch × mining_preset
```

- `include_kb_off = False` (mặc định từ Settings) → **không** nhân thêm dòng KB OFF.
- Bỏ trống `mining_presets` → không nhân chiều preset (mỗi train×KB×epoch một combo, miner baseline).
- Cắt trần: `max_runs` (hiện 200).

### Ví dụ (Settings đang dùng gần đây)

| Trục | Giá trị |
|------|---------|
| Train | `3, 6, 9` |
| KB | `era_2025_2026_6thang` |
| Epoch | `1 … 4` (`learning_loops = 4`) |
| Mining | `elite_or_quality` |
| OOS | `2026-04-01` → `2026-12-31` |
| Spread / slip | `1.0` / `0.3` pip |

→ **3 × 1 × 4 × 1 = 12 combo**.

Đổi Cài đặt → chữ ký grid đổi → Grid chỉ chạy **combo mới**, giữ kết quả cũ.

---

## 2. Không nằm trong lưới (nhưng ảnh hưởng kết quả)

| Tham số | Vai trò |
|---------|---------|
| **`grid_objective`** | Cách **xếp hạng / chọn winner** (`total_r`, `win_rate_pct`, `profit_factor`, `risk_adjusted`) — **không** nhân số combo. Chọn trên trang **Grid Search**; đổi mục tiêu → Best / bảng xếp lại ngay (không chạy lại combo) |
| Feature profile | Cố định `current` (không phải trục Grid) |
| RR / anti-chase / exit / `selection_mode`… | Nằm **trong** mining preset, không phải trục riêng |

**Lưu ý:** Học KB (`run_learning` / Huấn luyện bộ nhớ) **không** truyền mining preset — KB học bằng miner mặc định. Mining space chỉ khóa khi **Grid / remine / Live** dùng space gắn trên combo hoặc Trade Model.

---

## 3. Mỗi combo chạy gì

1. Load KB snapshot (nếu KB ON) + FeatureMatrix.
2. Walk-forward: mỗi tuần OOS mine trên `train_weeks` gần nhất (`mine_strategy_learning` / miner + optional space).
3. Backtest OOS với spread/slip của Settings.
4. Ghi hàng kết quả + `mining_search_space` (nếu có preset) → có thể **Tạo Trade Model**.

Chữ ký combo (rút gọn) gồm: `train` · KB · epoch · OOS · `msp:<preset>` (nếu có).

---

## 4. Xem / đổi trong GUI

| Nơi | Việc |
|-----|------|
| **Học & tối ưu → ① Cài đặt** | Chọn train, era, vòng học, OOS, spread/slip, mining preset |
| **② Huấn luyện bộ nhớ** | Phải đủ epoch theo Settings trước khi Grid sẵn sàng đủ combo |
| **③ Grid Search** | Chọn **mục tiêu xếp hạng**, chạy combo mới / force toàn bộ · xem Best / bảng |
| **Trade Models** | Một model = một combo đã chọn (lưu nguyên `mining_search_space`) |

---

## 5. File code

| File | Việc |
|------|------|
| `gui/app_settings.py` | `grid_build_kwargs`, `settings_grid_signature` |
| `gui/grid_search_engine.py` | `GridSpec`, `build_grid`, chạy walk-forward |
| `gui/views/grid_search.py` | UI Grid |
| `gui/views/settings_page.py` | UI Cài đặt |
| `mining_presets.py` | Preset → search space |
| `run_backtest.py` | `run_walk_forward` |
