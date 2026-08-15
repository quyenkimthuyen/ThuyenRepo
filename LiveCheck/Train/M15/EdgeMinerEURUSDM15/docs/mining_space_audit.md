# Báo cáo audit Mining Search Space

**Ngày chạy:** 2026-08-03  
**Neo so sánh:** Trade Model `tm_h_c_6_tu_n_h_c_2025-2026-6th_bc18d887`  
**Điều kiện cố định:** train **6 tuần** · KB `era_2025_2026_6thang` **ep3** · OOS `2026-01-01`→data · spread 1.0 / slip 0.3  
**Số preset:** 28 (gồm baseline)  
**Dữ liệu thô:** `results/research/wr_rr_breakthrough/latest.json` · `mining_space_audit.json`

---

## 1. Baseline (neo)

| WR | RR | Total R | Max DD | PF | n | tpw |
|--|--|--|--|--|--|--|
| 47.83% | 2.457 | +206.9R | 11.32 | 2.12 | 276 | 9.2 |

Mọi Δ dưới đây = preset − baseline.

---

## 2. Bảng xếp hạng (score chất lượng)

Score nội bộ ưu tiên expectancy (WR×RR), R/DD, PF — phù hợp mục tiêu “cải thiện chất lượng”, không chỉ Total R.

| # | Preset | WR% | RR | Total R | DD | PF | tpw | ΔWR | ΔRR | ΔR | Verdict |
|--|--|--|--|--|--|--|--|--|--|--|--|
| 1 | **elite_or_quality** | 70.77 | 2.776 | 125.1 | **2.53** | **6.41** | 2.2 | +22.9 | +0.32 | −82 | **KEEP — khuyến nghị app** |
| 2 | elite_55_4 | 61.11 | **3.386** | 68.8 | 3.44 | 5.32 | 1.2 | +13.3 | +0.93 | −138 | KEEP — niche WR>60 & RR>3 |
| 3 | elite_60_3_vwap | 63.93 | 3.000 | 107.6 | 4.62 | 4.37 | 2.0 | +16.1 | +0.54 | −99 | KEEP |
| 4 | elite_60_35 | 56.00 | 2.933 | 136.7 | 4.41 | 3.13 | 3.3 | +8.2 | +0.48 | −70 | KEEP (dự phòng elite) |
| 5 | elite_60_3 | 60.32 | 2.897 | 98.1 | 4.43 | 3.91 | 2.1 | +12.5 | +0.44 | −109 | KEEP |
| 6 | anti_chase | 60.39 | 2.378 | 185.6 | 4.82 | 3.36 | 5.1 | +12.6 | −0.08 | −21 | KEEP — calibrate chase |
| 7 | nova | 57.52 | 2.442 | 173.7 | 4.82 | 3.17 | 5.1 | +9.7 | −0.02 | −33 | REVIEW → có thể gộp vào anti_chase |
| 8 | anti_chase_fixed_62 | 56.74 | 2.518 | 162.8 | 4.81 | 3.32 | 4.7 | +8.9 | +0.06 | −44 | REVIEW — thua fixed_70 về R |
| 9 | anti_chase_strict | 57.14 | 2.434 | 162.8 | 5.69 | 3.06 | 4.9 | +9.3 | −0.02 | −44 | REVIEW |
| 10 | nova_fixed | 56.64 | 2.482 | 159.9 | 5.91 | 3.15 | 4.8 | +8.8 | +0.03 | −47 | REVIEW |
| 11 | **anti_chase_fixed_70** | 52.34 | 2.520 | **228.3** | 6.67 | 2.74 | 7.8 | +4.5 | +0.06 | **+21** | **KEEP — cân bằng R+WR** |
| 12 | anti_chase_and_65_2 | 52.58 | 2.479 | 185.1 | 5.77 | 2.73 | 6.5 | +4.8 | +0.02 | −22 | REVIEW |
| 13 | anti_chase_and_70_15 | 51.95 | 2.499 | 216.3 | 7.96 | 2.53 | 7.7 | +4.1 | +0.04 | +9 | KEEP (AND nhẹ) |
| 14 | anti_chase_fixed_65 | 51.67 | 2.430 | 160.2 | 6.07 | 2.60 | 6.0 | +3.8 | −0.03 | −47 | REVIEW → thua fixed_70 |
| 15 | **edge_gentle** | 48.91 | 2.486 | **221.3** | **8.10** | 2.24 | 9.1 | +1.1 | +0.03 | **+14** | **KEEP — gần baseline + R↑ DD↓** |
| 16 | anti_chase_and_68_2 | 50.00 | 2.508 | 193.8 | 9.36 | 2.34 | 7.5 | +2.2 | +0.05 | −13 | REVIEW |
| 17 | frontier_rr_hi | 48.31 | 2.473 | 207.7 | 11.32 | 2.23 | 8.9 | +0.5 | +0.02 | +1 | KEEP nhẹ / neo frontier |
| 18 | baseline | 47.83 | 2.457 | 206.9 | 11.32 | 2.12 | 9.2 | 0 | 0 | 0 | **KEEP — bắt buộc** |
| 19 | anti_chase_fixed_68 | 49.09 | 2.444 | 175.5 | 11.01 | 2.38 | 7.3 | +1.3 | −0.01 | −31 | DROP ứng viên (thua fixed_70) |
| 20 | edge_surgery | 47.81 | 2.453 | 205.0 | 11.32 | 2.15 | 9.1 | −0.0 | −0.00 | −2 | **DROP** — trùng baseline |
| 21 | frontier_rr | 46.47 | 2.452 | 186.5 | 11.32 | 2.02 | 9.0 | −1.4 | −0.01 | −20 | **DROP** |
| 22 | edge_surgery_v2 | 44.98 | 2.500 | 177.1 | 9.90 | 1.88 | 9.0 | −2.9 | +0.04 | −30 | **DROP** |
| 23 | edge_side_only | 46.27 | 2.478 | 187.2 | **16.62** | 2.05 | 8.9 | −1.6 | +0.02 | −20 | **DROP** — DD xấu |
| 24 | edge_surgery_rr | 45.11 | 2.491 | 175.2 | 14.86 | 1.90 | 8.9 | −2.7 | +0.03 | −32 | **DROP** |
| 25 | edge_surgery_v2_clean | 44.44 | 2.529 | 158.1 | 12.87 | 1.90 | 8.1 | −3.4 | +0.07 | −49 | **DROP** |
| 26 | wr_rr_lock | 46.26 | 2.329 | 140.6 | 11.91 | 1.86 | 7.6 | −1.6 | −0.13 | −66 | **DROP** |
| 27 | wr_rr_sniper | 42.79 | 2.432 | 120.0 | 11.78 | 1.72 | 7.4 | −5.0 | −0.03 | −87 | **DROP — tệ nhất nhóm đầu** |
| 28 | wr_rr_frontier | 43.05 | 2.350 | 113.6 | **13.97** | 1.67 | 7.4 | −4.8 | −0.11 | −93 | **DROP — tệ nhất overall** |

---

## 3. Đề xuất loại bỏ (DROP)

Các preset **thua baseline rõ** trên WR và/hoặc Total R, hoặc thừa / DD xấu — nên **ẩn khỏi Settings UI** và đánh dấu deprecated (vẫn giữ trong code để regression CLI nếu cần).

| Preset | Lý do loại |
|--------|------------|
| `wr_rr_frontier` | WR −4.8pp, R −93, DD xấu hơn — tệ nhất |
| `wr_rr_sniper` | WR −5.0pp, R −87 — research cũ không transfer |
| `wr_rr_lock` | WR↓ RR↓ R −66 |
| `edge_surgery_v2_clean` | WR −3.4, R −49 |
| `edge_surgery_rr` | WR −2.7, R −32, DD↑ |
| `edge_side_only` | R↓ và **DD 16.6** (xấu nhất) |
| `edge_surgery_v2` | WR −2.9, R −30 |
| `frontier_rr` | WR −1.4, R −20 — bị `frontier_rr_hi` thay thế |
| `edge_surgery` | Gần như trùng baseline (Δ ≈ 0) — không thêm giá trị |
| `anti_chase_fixed_68` | Thua `fixed_70` trên WR/R/DD — dư thừa trong họ fixed |

### Ứng viên REVIEW (có thể gộp / ẩn sau)

Trùng chức năng với preset KEEP tốt hơn:

- `nova`, `nova_fixed` → gần `anti_chase` / `anti_chase_fixed_*`
- `anti_chase_fixed_62`, `fixed_65`, `anti_chase_strict` → thua `fixed_70` hoặc elite về cân bằng R
- `anti_chase_and_65_2`, `and_68_2` → thua `and_70_15` / `fixed_70`

Không bắt buộc xóa ngay; ưu tiên **ẩn khỏi curated Settings**.

---

## 4. Đề xuất giữ (KEEP) cho app

| Vai trò | Preset |
|---------|--------|
| Mặc định / khuyến nghị | **`elite_or_quality`** |
| Neo so sánh | **`baseline`** |
| Cân bằng Total R + WR↑ | **`anti_chase_fixed_70`**, **`edge_gentle`** |
| Elite chất lượng | `elite_60_3_vwap`, `elite_60_3`, `elite_55_4`, `elite_60_35` |
| Calibrate chase | `anti_chase` |
| Frontier nhẹ | `frontier_rr_hi` |
| AND void nhẹ | `anti_chase_and_70_15` |

**Curated Settings (2026-08-10 — gọn trùng lặp):**  
`elite_or_quality`, `anti_chase_fixed_70`, `edge_gentle`, `elite_55_4`, `baseline`

Ẩn khỏi Settings (vẫn trong code): `elite_60_3`, `elite_60_3_vwap`, `frontier_rr_hi`, và họ anti-chase/nova dư thừa.

---

## 5. Nhận xét ngắn

1. **Nhóm research cũ** (`wr_rr_*`) thất bại trên model/KB hiện tại — nên loại khỏi UI.  
2. **Nhóm edge_surgery*** hầu hết không thắng baseline ổn định; chỉ `edge_gentle` còn giá trị.  
3. **Anti-chase void** là đòn bẩy thật: fixed_70 giữ R; elite siết WR/DD.  
4. Tối ưu Mining space **có ý nghĩa** — cùng KB/train, chỉ đổi space đã tách rõ tốt/xấu.

---

## 6. Cách tái chạy audit

```bash
cd EdgeMinerM15
.venv/bin/python scripts/compare_wr_rr_breakthrough.py \
  --model-id tm_h_c_6_tu_n_h_c_2025-2026-6th_bc18d887 \
  --presets baseline,<danh_sách> \
  --workers 4
```

Rồi đọc lại `results/research/wr_rr_breakthrough/latest.json`.
