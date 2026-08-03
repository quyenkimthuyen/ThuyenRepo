# Mining Search Space — Hướng dẫn dễ hiểu

Tài liệu giải thích **Mining search space**: lớp cấu hình quyết định *cách hệ thống tìm chiến lược mỗi tuần*, khác với KB (bộ nhớ) và train weeks (cửa sổ học ngắn hạn).

---

## 1. Ba khái niệm dễ nhầm — phân biệt nhanh

| | **Train weeks** | **KB** | **Mining search space** |
|--|--|--|--|
| Là gì | Cửa sổ dữ liệu gần nhất để mine mỗi tuần (3 / 6 / 9 tuần) | Bộ nhớ dài hạn: rule, genome, ML | **Luật chơi của miner**: RR, exit, bộ lọc anti-chase… |
| Đổi khi nào | Settings / Trade Model | Học epoch / chọn snapshot | Settings preset → Grid → lưu vào Trade Model |
| Ví dụ | “Học 6 tuần trước tuần OOS” | `era_2025_2026_6thang` ep3 | `elite_or_quality`: void RSI/VWAP, RR 3.2–4 |

```
Mỗi tuần walk-forward:

  [--- train N tuần ---][-- OOS tuần --]
           │
           ├─ KB (nếu bật) gợi ý rule / ML thông minh hơn
           └─ Mining search space = khung tham số miner được phép thử
```

- **KB** = “đã từng thấy gì trong quá khứ”
- **Mining space** = “được phép tìm theo kiểu nào”
- **Train weeks** = “nhìn bao nhiêu tuần gần đây”

Ba thứ độc lập. Đổi mining space **không** xóa KB. Xóa Trade Model **không** xóa preset trong code.

---

## 2. Mining search space là gì?

Khi remine, miner thử nhiều “genome” (bộ rule + ngưỡng + RR + cách thoát lệnh…). Tập hợp các lựa chọn đó gọi là **MiningSearchSpace**.

Ví dụ các knobs quan trọng:

| Knob | Ý nghĩa đời thường |
|------|-------------------|
| `rr_ratios` | Mục tiêu lãi/lỗ khi thắng (vd 2.5R, 3.2R, 4R) |
| `atr_multipliers` | Độ rộng stop theo ATR |
| `exit_mode` | Thoát full TP, trail/hybrid, hay partial |
| `score_thresholds` / `ml_probability_thresholds` | Ngưỡng vào lệnh chặt hay lỏng |
| `selection_mode` | Cách **chấm điểm** genome thắng cuộc |
| `anti_chase` | Hủy lệnh “đuổi giá” (RSI / VWAP quá mệt) |
| `edge_surgery` | Cắt giờ / phía lệnh độc trên **train only** |

**Preset** = một bộ knobs đã đặt tên sẵn trong `mining_presets.py` (vd `elite_or_quality`), để Settings / Grid / research script gọi bằng một chuỗi, không phải chỉnh tay từng số.

---

## 3. Luồng trong app (Settings → Grid → Model → Live)

```
┌─────────────────┐
│  Cài đặt        │  mining_presets = ["elite_or_quality"]  (mặc định khuyến nghị)
└────────┬────────┘
         │ build Grid combo = train × KB × epoch × preset
         ▼
┌─────────────────┐
│  Grid Search    │  mỗi dòng kết quả có thể gắn preset
└────────┬────────┘
         │ “Tạo Trade Model”
         ▼
┌─────────────────┐
│  Trade Model    │  lưu nguyên mining_search_space + train + KB + OOS
└────────┬────────┘
         │ set active
         ▼
┌─────────────────┐
│ Live / Paper /  │  remine hàng tuần = đọc space từ model active
│ Bridge          │  (không đọc lại Settings lúc runtime)
└─────────────────┘
```

### Ai quyết định gì?

| Nơi | Vai trò |
|-----|---------|
| **Cài đặt → Mining search space** | Preset nào Grid sẽ thử. Đổi → chữ ký grid đổi → cần chạy lại Grid. |
| **Trade Model** | Bản “đóng gói” dùng thật: Live/Paper/remine theo space **đã lưu**. |
| **`mining_presets.py`** | Định nghĩa preset trong code. Xóa model **không** mất preset. |

**Nguyên tắc vàng:** Muốn đổi hướng mining cho live → tạo / chọn Trade Model mới có `mining_search_space` đúng, rồi set active. Chỉ đổi Settings thì **chưa** đổi live cho đến khi Grid → tạo model mới.

---

## 4. Preset khuyến nghị: `elite_or_quality`

Đây là hướng mặc định của app sau cải tiến WR×RR (chấp nhận ít lệnh hơn để tăng chất lượng).

### Ý tưởng một câu

> Chỉ giữ lệnh SHORT “còn sức” (RSI và VWAP chưa exhaustion), nhắm TP xa hơn, thoát full — không thay lệnh kém hơn vào chỗ đã hủy.

### Các đòn bẩy chính

| Thành phần | Giá trị | Vì sao |
|------------|---------|--------|
| `selection_mode` | `elite_frontier` | Ưu tiên WR×RR cao; ít phạt tần suất thấp |
| `rr_ratios` | `[3.2, 3.5, 4.0]` | Winner lớn hơn để bù loss drag (~1.15R sau spread/slip) |
| `exit_modes_full_only` | `true` | Tránh hybrid/partial cắt lãi sớm → RR↓ |
| Anti-chase | **fixed**, logic **OR** | Void SHORT nếu RSI ≥ 58 **hoặc** VWAP dist ≥ 1.5 |
| Cách void | **không thay thế** | Hủy fill chase; **không** promote lệnh hạng thấp hơn |

### Anti-chase “void không thay thế” (quan trọng)

Cách sai (đã thử): lọc chase **trước** khi chọn lệnh trong ngày → miner lấy lệnh kém hơn thay chỗ → WR có thể **giảm**.

Cách đúng:

1. Chọn lệnh như bình thường (ranking giữ nguyên)
2. Nếu lệnh được chọn là chase → **hủy** (void)
3. Không kéo ứng viên khác lên thay

Signal dùng **signal-bar** (bar đóng trước entry), không lookahead entry-bar.

### Kết quả OOS tham chiếu (cùng KB)

Điều kiện so sánh: KB `era_2025_2026_6thang` **ep3**, train **6 tuần**, OOS từ `2026-01-01`, spread 1.0 / slip 0.3.

| | Baseline miner | `elite_or_quality` |
|--|--|--|
| Win rate | ~48% | **~71%** |
| Avg RR | ~2.46 | **~2.78** |
| Total R | ~+207 | ~+125 |
| Max DD | ~11.3 | **~2.5** |
| Lệnh / tuần | ~9 | ~2.2 |
| Profit factor | ~2.1 | **~6.4** |

**Trade-off cố ý:** chất lượng và DD tốt hơn nhiều; Total R và tần suất giảm. Phù hợp khi ưu tiên WR / ổn định hơn “nhiều lệnh”.

Model đã promote (ví dụ): `tm_breakthrough_elite_or_qualit_*` — xem danh sách **Trade Models** trong app.

---

## 5. Các preset khác (tóm tắt)

Không cần nhớ hết — Settings chỉ hiện **curated** (đã audit). Đầy đủ nằm trong `mining_presets.py`.

| Nhóm | Ví dụ | Khi nào dùng |
|------|--------|--------------|
| Baseline | `baseline` | So sánh công bằng / hành vi miner cũ |
| Frontier | `frontier_rr_hi` | Joint WR×RR nhẹ, gần giữ Total R |
| Anti-chase cân bằng | `anti_chase_fixed_70` | Void RSI≥70; WR↑ và Total R↑ |
| Edge gentle | `edge_gentle` | R↑ DD↓ gần tần suất baseline |
| Elite | **`elite_or_quality`**, `elite_55_4`… | WR/DD ưu tiên; ít lệnh hơn |

Audit xếp hạng + danh sách **DROP**: [`docs/mining_space_audit.md`](mining_space_audit.md).

Hằng số code: `RECOMMENDED_PRESET = "elite_or_quality"` · `CURATED_PRESETS` · `DEPRECATED_PRESETS`.

---

## 6. Xem / đổi trong GUI

### Cài đặt

**Học & tối ưu → ① Cài đặt → Mining search space**

- Multiselect preset (mặc định: Elite OR-quality)
- Bỏ trống = Grid dùng miner baseline (không nhân thêm chiều preset)
- Caption tóm tắt hướng khuyến nghị

### Trade Models

- Banner: dòng `mining …` (RSI/VWAP/RR/mode)
- Tab **Thông tin**: box tóm tắt search space của model đang chọn

### Grid Search

- Chữ ký settings có `msp:elite_or_quality` (và preset khác nếu chọn)
- Đổi preset → cảnh báo “cài đặt đã đổi” → chạy lại Grid phần combo mới

---

## 7. Xóa model rồi train lại?

**Có.** Xóa Trade Model chỉ mất metadata + report/schedule của model đó.

Còn lại:

- Preset `elite_or_quality` trong code
- Settings `mining_presets`
- KB profile / epoch (nếu không xóa KB)

### Cách A — CLI (nhanh, giống lúc research)

```bash
cd EdgeMinerM15
.venv/bin/python scripts/compare_wr_rr_breakthrough.py \
  --presets baseline,elite_or_quality \
  --workers 1 --promote --set-active
```

Script lấy train / KB / OOS từ **model active** (hoặc `--model-id`). Nếu đã xóa hết model liên quan, chọn một model còn KB `era_2025_2026_6thang` ep3 làm neo, hoặc tạo model baseline rồi chạy lại.

### Cách B — trong app

1. Cài đặt: giữ preset **Elite OR-quality**
2. Grid Search: chạy lại
3. Chọn combo: train **6 tuần** · KB **2025-2026-6thang** · **ep3** · preset elite_or_quality
4. Tạo Trade Model → set active

Số liệu OOS có thể lệch nhẹ theo data MT5 mới; hướng mining giữ nguyên nhờ preset.

---

## 8. File code liên quan

| File | Việc |
|------|------|
| `mining_presets.py` | Định nghĩa preset + `RECOMMENDED_PRESET` |
| `strategy_miner.py` | `MiningSearchSpace`, anti-chase void, `elite_frontier`, exit full-only |
| `meta_learner.py` | Chấm genome khi KB path dùng frontier/elite |
| `gui/app_settings.py` | Default Settings + chữ ký grid có `msp:` |
| `gui/views/settings_page.py` | UI chọn preset |
| `gui/grid_search_engine.py` | Nhân combo theo `mining_presets` |
| `gui/trade_model.py` / services | Remine đọc `mining_search_space` từ model |
| `scripts/compare_wr_rr_breakthrough.py` | A/B preset vs baseline, promote model |

---

## 9. Câu hỏi thường gặp

**Q: Đổi preset ở Cài đặt rồi Live có đổi ngay không?**  
A: Không. Live theo Trade Model active. Cần Grid (hoặc script promote) → model mới → set active.

**Q: Baseline miner có bị phá không?**  
A: Không. Không chọn preset / model không có `mining_search_space` → hành vi cũ.

**Q: Anti-chase có lookahead không?**  
A: Không — dùng feature trên **signal bar** (trước entry).

**Q: Vì sao Total R giảm dù WR tăng?**  
A: Ít lệnh hơn (void + RR cao khó hit). Expectancy/lệnh và DD thường tốt hơn; tổng R phụ thuộc tần suất.

**Q: `elite_55_4` vs `elite_or_quality`?**  
A: `elite_55_4` siết hơn (RSI&lt;55, RR=4) → WR>60% và RR>3 nhưng rất ít lệnh. `elite_or_quality` cân bằng WR rất cao + Total R / DD dễ dùng hơn cho app mặc định.

---

## 10. Tóm tắt một đoạn

Mining search space là **cách miner được phép tìm edge**, đóng gói thành preset. App mặc định hướng **`elite_or_quality`**: void SHORT exhaustion (RSI∨VWAP), RR ladder cao, exit full, chấm điểm elite. Settings điều khiển Grid; Trade Model đóng gói cho Live; xóa model vẫn train lại được vì preset + KB còn nguyên.
