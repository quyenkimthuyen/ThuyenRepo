# Hướng dẫn train Trade Model tốt hơn — xuyên Timeframe & Symbol

Tài liệu này ghi lại **những việc đã thực sự giúp** cải thiện Trade Model trên desk `backtest/` (M15) và `backtestM5/` (M5), với EURUSD / GBPUSD khác nhau. Không phải lý thuyết chung — là playbook đã chạy và đo được.

**Thước đo chuẩn (bắt buộc):** OOS `2026-01-01` → `2026-08-07`  
Mọi so sánh / promote / Pareto chỉ hợp lệ trên cửa sổ này.

---

## 0. Tư duy cốt lõi

Hiệu quả train **không** đến từ “copy model M15 sang M5” hay “Total R cao nhất”.  
Thứ tự đòn bẩy đã kiểm chứng:

1. **Cùng thước đo OOS** (protocol)  
2. **KB era khớp regime sắp OOS**  
3. **Objective Grid / promote đúng mục tiêu live** (`quality` > raw `total_r` khi cần trade thật)  
4. **Search space scale theo TF** (hold / spacing / target TPW)  
5. **Chấp nhận frontier khác nhau theo symbol** (EUR vs GBP)  
6. Preset / fitness / anti-chase (tinh chỉnh)  
7. Ensemble + ổn định theo tháng (sau khi đã có Pareto đơn)

TF và symbol **có** ảnh hưởng, nhưng chúng định hình *frontier* — không thay thế 1–4.

---

## 1. Checklist trước khi train (mọi desk mới)

### 1.1 Cô lập runtime (song song 4 app)

| Mục | Phải khác nhau |
|-----|----------------|
| INSTANCE | `M15E21` / `M15G23` / `M5E31` / `M5G33` |
| Bridge folder | `bridge_*` + `bridge_sim_*` riêng |
| Magic Live/Sim | Giãn ≥20 giữa desk (xem `results_magic_isolation.md`) |
| Streamlit + chart ports | Không trùng |

Không dùng EA generic `ForgeBridge.mq5` cho live — chỉ EA instance (`ForgeBridgeM15E21`, `…M5E31`, …).

### 1.2 Khóa OOS trước Grid

Trong `app_settings.json` / workspace:

```text
backtest_from = 2026-01-01
backtest_to   = 2026-08-07
```

Sau khi có nhiều Trade Model lệch cửa sổ:

```bash
# M5
cd backtestM5 && ./run_unify_oos.sh

# M15
cd backtest && ./run_unify_oos.sh

# Bảng chung 4 cell
python ../build_cross_oos_pareto.py   # từ repo root: python build_cross_oos_pareto.py
```

**Đừng** promote / so sánh model khi registry còn `oos_from/oos_to` khác nhau.

### 1.3 Dữ liệu

- Chỉ parquet MT5 đúng symbol + TF của desk (`mt5_*_m15.parquet` / `mt5_*_m5.parquet`).
- Không reuse Trade Model hoặc genome M15 trên desk M5 (và ngược lại).

---

## 2. Scale mining theo Timeframe (bài học M15 → M5)

### Vì sao clone M15 “yếu” trên M5?

Giữ nguyên `max_hold_bars=96`, `min_bars_between=12`, `target_trades_per_week≈7` trên M5 = **under-capacity**: quá ít tín hiệu / hold quá ngắn theo clock M5.

### Công thức thực tế đã dùng

| Tham số | M15 (tham chiếu) | M5 (sau retune) |
|---------|------------------|-----------------|
| `max_hold_bars` | ~96 | **192** (≈ cùng phút wall-clock) |
| `min_bars_between` | ~12 | **16** |
| `target_trades_per_week` | ~7–10 | **12–16** (elite); baseline có thể cao hơn |
| `max_trades_per_day` | — | **5** |
| Feature profile | `current` | `m5_parity` |
| Fitness TPW bands | cố định kiểu M15 | **scale theo target_tpw** (không hard-cap 7–10) |

Preset hữu ích trên M5: `elite_or_quality`, `elite_m5_balanced`, `anti_chase_fixed_70`.

**Quy tắc:** đổi TF → scale bar-counts & TPW trước; chỉ rồi mới Grid.

---

## 3. KB Learning — đòn bẩy lớn nhất sau OOS

### Đã thấy trên data

- `era_3_thang_cuoi_2025` → OOS 2026 thường **rất xấu**.
- `era_5_thang_cuoi_2025` + `era_2025_h2` (+ đôi khi `2025-2026-6thang`) → GBP/EUR M5 nhảy rõ.
- Remine genome trên **KB cũ sai** chỉ cải thiện một phần; **KB retrain + Grid** mới “đủ bài”.

### Pipeline khuyến nghị (mỗi desk)

```text
1) Chọn 2–3 learning eras gần regime OOS
2) Learning loops ≥ 4 (KB snapshots)
3) Grid trên các era × train_weeks × presets
4) Promote theo objective quality (không chỉ Total R)
5) unify_oos / re-score lại toàn bộ live models
```

Scripts đã dùng:

- `scripts/run_kb_then_grid.py`
- `scripts/complete_m5_quality.py` (KB → grid quality → promote)
- `scripts/unify_oos_compare.py`

### Train weeks

Thử **cả tw=3 và tw=6** trên Grid — không mặc định tw=6 luôn thắng. Có case tw3 + era tốt > tw6.

---

## 4. Objective Grid / cách chọn “Best*”

| Objective | Ra sách kiểu | Khi nào dùng |
|-----------|--------------|--------------|
| `total_r` | Nhiều lệnh, R cao, DD dễ phình | Research ceiling |
| `win_rate_pct` / PF-heavy | Ít lệnh, PF/WR đẹp | Muốn chất lượng cực cao (hay gặp M15) |
| **`quality`** | Cân R–PF–DD | **Live mặc định (M5 đã thắng nhờ cái này)** |

Promote nên giữ **portfolio nhãn**:

- `BestQuality` — active mặc định (PF/DD)
- `BestBalance` / `BestPF` — chân thứ hai
- `BestTotalR` — shelf / research (đừng active nếu DD xấu)

**Không** lấy Total R #1 làm active chỉ vì bảng đẹp.

Chỉ số phụ để chọn 1 book live: **R/DD**, rồi PF, rồi độ ổn định tháng.

---

## 5. Symbol khác nhau — đừng copy nguyên recipe

| | EURUSD | GBPUSD |
|--|--------|--------|
| Spread desk | ~1.0 | ~1.5 |
| Frontier | Dễ ra PF cao / DD thấp | R tuyệt đối có thể cao hơn, DD/PF kém hơn |
| Active gợi ý | BestQuality / BestBalance | BestQuality + BestPF (ensemble) |

**Làm đúng:** cùng pipeline (OOS + KB + quality grid + scale TF).  
**Làm sai:** copy nguyên genome/preset TPW của EUR sang GBP (hoặc M15→M5) rồi kết luận “symbol này yếu”.

---

## 6. Vòng cải thiện đã chứng minh (M5)

Thứ tự đã chạy thành công:

```text
A. Retune fitness/preset/space (remine trên KB cũ)
   → cải thiện một phần (DD↓, R/DD↑), chưa đủ

B. Full KB retrain + Grid objective=quality + promote Best*
   → đạt target quality EUR/GBP

C. Stretch / multi-era / thêm preset
   → mở Pareto, không phải mọi metric cùng lúc

D. Round 3: ensemble BestQuality+BestBalance (EUR)
            / BestQuality+BestPF (GBP)
   + walk-forward ổn định theo tháng
   → capital_split hoặc union_dedupe tùy desk

E. Unify OOS mọi model + Pareto EUR/GBP × M15/M5
   → một thước đo, chọn book theo R/DD / Pareto ★
```

Artifacts tham chiếu:

- `backtestM5/results_m5_retune_eval.md`
- `backtestM5/results_m5_quality_complete.md`
- `backtestM5/results_m5_round3.md`
- `backtestM5/results_m5_oos_unified.md`
- `results_cross_oos_pareto.md`
- `results_magic_isolation.md`

---

## 7. Ensemble & ổn định tháng (sau khi đã có 2 chân)

Khi đã có BestQuality + chân phụ:

```bash
cd backtestM5 && ./run_round3.sh
```

Modes hữu ích:

| Mode | Ý nghĩa |
|------|---------|
| `capital_split_50_50` | Mỗi chân 0.5R — êm, Sharpe tháng tốt (EUR) |
| `union_dedupe` | Gộp lệnh, bỏ trùng giờ+side — giữ R, vá tháng đỏ (GBP) |
| `agree_month` | Chỉ cộng tháng cả hai chân dương — defensive |

Chỉ ensemble khi **cùng OOS** và đã unify KPI.

---

## 8. So sánh xuyên TF/symbol (một thước đo)

```bash
# Sau unify M15 + M5:
python build_cross_oos_pareto.py
```

Đọc bảng:

1. Chỉ model `oos_from/to` = canonical  
2. ★ = Pareto (max R, max PF, min DD)  
3. Rank phụ theo **R/DD** để chọn live  
4. Best-per-cell: maxR / maxPF / best R/DD theo từng ô TF×Symbol  

Nhận xét đã thấy trên cùng OOS:

- **M15 EUR** dẫn chất lượng (PF/WR/R/DD cực cao, ít lệnh).  
- **M5 EUR** cân bằng tốt (BestBalance / BestQuality).  
- **M5 GBP** cao Total R hơn nhưng DD nặng hơn.  
- **M15 GBP** đứng giữa — PF khá, R vừa.

---

## 9. Playbook “desk mới” (BTC, JPY, TF khác…)

Copy checklist này theo thứ tự — **đừng nhảy bước**:

1. Clone desk → INSTANCE / bridge / magic / ports riêng (`results_magic_isolation.md`).  
2. Khóa OOS canonical.  
3. Scale `hold` / `spacing` / `tpw` theo TF (quy đổi theo phút wall-clock + mật độ lệnh mong muốn).  
4. Chọn 2–3 KB eras gần OOS; **retrain KB**, không chỉ remine.  
5. Grid `objective=quality` + vài preset elite/anti-chase.  
6. Promote BestQuality (+ Balance/PF); archive model cửa sổ lệch.  
7. `unify_oos` → xem R/DD & tháng dương.  
8. (Optional) Round-3 ensemble nếu có 2 chân bổ sung.  
9. Đưa vào Pareto chung với các desk khác **cùng OOS**.

Dừng sớm nếu: KB era xấu, hoặc đang so sánh lệch OOS, hoặc active là BestTotalR DD cao.

---

## 10. Anti-patterns (đã mắc / đã tránh)

| Sai | Đúng |
|-----|------|
| So sánh R khi OOS khác nhau | `unify_oos` trước |
| Clone M15 space nguyên sang M5 | Scale hold/TPW |
| Remine mãi trên KB sai era | Retrain KB multi-era |
| Active = max Total R | Active = quality / R/DD |
| Một objective cho mọi symbol | Cùng pipeline, khác điểm trên frontier |
| Magic sát nhau EUR/GBP | Base cách ≥20 |
| Sim `models.json` dùng magic Live | `DEFAULT_SIM_MAGIC` |
| Kết luận “M5 kém M15” khi chưa cùng OOS | Pareto sau unify |

---

## 11. Validation từ đầu — `Final_app/`

Để chứng minh playbook trên **4 desk sạch** (EUR/GBP × M15/M5):

```bash
cd /home/thuyenng/work/ThuyenRepo
EdgeMinerM15B5/.venv/bin/python Final_app/bootstrap_clone_clean.py
chmod +x Final_app/run_final_train.sh
nohup Final_app/run_final_train.sh > Final_app/final_train.nohup.log 2>&1 &
tail -f Final_app/final_train.log
```

Kết quả Pareto: `Final_app/results_final_guide_validation.md`  
Chi tiết desk: `Final_app/README.md`

## Split Lab / Live

Xem `Final_app/split_app/README.md`:

- **Lab** = 4 desk `Final_app/EdgeMiner*` + `lab/export_trade_package.py`
- **Live** = `split_app/live` (import `.tmpkg`, roster, 1 EA `ForgeBridgeLive`)

## 12. Lệnh hay dùng (tóm tắt)

```bash
# Quản lý 2 app M5
cd backtestM5 && ./manage_clones.sh status|start|stop|restart

# KB → Grid quality (theo script desk)
# python EdgeMinerEURUSDM5/scripts/complete_m5_quality.py

# Unify OOS + cập nhật KPI registry
cd backtestM5 && ./run_unify_oos.sh --reuse
cd ../backtest && ./run_unify_oos.sh --reuse

# Ensemble + monthly stability
cd ../backtestM5 && ./run_round3.sh

# Pareto 4 cell
cd /home/thuyenng/work/ThuyenRepo && python build_cross_oos_pareto.py
```

---

## 13. Định nghĩa “model tốt hơn” trong hệ này

Một Trade Model được coi là **tiến bộ** khi, trên **cùng OOS**:

- R/DD tăng (hoặc DD giảm rõ ở R tương đương), **và/hoặc**
- PF / WR cải thiện không đánh đổi DD thảm họa, **và**
- Tỷ lệ tháng dương ổn (Round-3), **và**
- Phù hợp dual-run (magic/bridge không đụng desk khác).

Total R đơn lẻ **không** đủ để gọi là train thành công.
