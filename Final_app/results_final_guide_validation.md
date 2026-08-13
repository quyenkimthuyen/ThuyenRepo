# Final_app — GUIDE validation (from-scratch train)

OOS **`2026-01-01` → `2026-08-07`** · generated 2026-08-13T00:04:37+05:30

Playbook: `GUIDE_TRAIN_TRADE_MODELS.md`
Live models on-window: **64** · Pareto ★: **12**

## Best per cell (TF × Symbol)

- **M15 EUR**: maxR `StretchR_2` (124.119R) · maxPF `EliteQuality_4` (PF 2.219) · best R/DD `EliteRDD_2` (12.453)
- **M15 GBP**: maxR `StretchR_2` (134.06R) · maxPF `EliteQuality_2` (PF 3.99) · best R/DD `EliteRDD_2` (20.185)
- **M5 EUR**: maxR `BestTotalR` (285.037R) · maxPF `BestQuality` (PF 2.188) · best R/DD `BestTotalR` (21.48)
- **M5 GBP**: maxR `BestTotalR` (276.427R) · maxPF `ElitePF_2` (PF 2.524) · best R/DD `BestQuality` (15.238)

## All models (R/DD rank)

| ★ | TF | Sym | Label | R | PF | WR | DD | R/DD | n | KB |
|---|----|-----|-------|---|----|----|----|------|---|----|
| ★ | M5 | EUR | BestTotalR | 285.037 | 1.603 | 42.26 | 13.27 | 21.48 | 698 | era_2025_h2 |
| ★ | M15 | GBP | EliteRDD_2 | 70.849 | 3.387 | 58.33 | 3.51 | 20.185 | 48 | era_2025_2026_6thang |
| ★ | M5 | EUR | EliteQuality | 187.327 | 1.904 | 41.97 | 9.63 | 19.452 | 355 | era_5_thang_cuoi_2025 |
| ★ | M5 | EUR | BestQuality | 127.555 | 2.188 | 47.19 | 6.79 | 18.786 | 178 | era_2025_h2 |
| ★ | M15 | GBP | StretchR_2 | 134.06 | 2.1 | 53.4 | 7.66 | 17.501 | 206 | era_2025_2026_6thang |
| ★ | M5 | EUR | EliteRDD | 194.051 | 1.903 | 43.55 | 11.71 | 16.571 | 349 | era_5_thang_cuoi_2025 |
|  | M15 | GBP | BestQuality | 131.547 | 2.088 | 52.68 | 8.59 | 15.314 | 224 | era_2025_h2 |
| ★ | M5 | GBP | BestQuality | 237.712 | 1.818 | 41.89 | 15.6 | 15.238 | 413 | era_5_thang_cuoi_2025 |
|  | M5 | GBP | BestWinRate | 272.588 | 1.586 | 42.5 | 18.08 | 15.077 | 640 | era_5_thang_cuoi_2025 |
|  | M5 | GBP | BestTotalR | 276.427 | 1.599 | 42.48 | 19.06 | 14.503 | 652 | era_5_thang_cuoi_2025 |
| ★ | M15 | GBP | EliteQuality | 51.995 | 3.393 | 56.25 | 3.65 | 14.245 | 48 | era_2025_h2 |
|  | M15 | GBP | ElitePF | 52.138 | 3.124 | 57.14 | 3.73 | 13.978 | 49 | era_2025_h2 |
| ★ | M5 | EUR | BestWinRate | 138.042 | 2.183 | 47.78 | 9.93 | 13.902 | 180 | era_2025_h2 |
| ★ | M5 | GBP | EliteRDD | 199.073 | 1.612 | 41.21 | 15.28 | 13.028 | 398 | era_5_thang_cuoi_2025 |
|  | M5 | GBP | EliteQuality | 264.986 | 1.545 | 41.98 | 20.43 | 12.97 | 648 | era_5_thang_cuoi_2025 |
| ★ | M15 | GBP | EliteQuality_2 | 57.965 | 3.99 | 67.35 | 4.56 | 12.712 | 49 | era_2025_2026_6thang |
|  | M15 | EUR | EliteRDD_2 | 59.651 | 2.089 | 45.16 | 4.79 | 12.453 | 93 | era_2025_h2 |
|  | M5 | EUR | StretchR | 265.34 | 1.567 | 41.57 | 21.36 | 12.422 | 664 | era_2025_h2 |
|  | M15 | EUR | EliteQuality_4 | 69.535 | 2.219 | 46.46 | 5.92 | 11.746 | 99 | era_2025_h2 |
|  | M5 | GBP | EliteRDD_2 | 154.079 | 1.413 | 40.2 | 13.73 | 11.222 | 505 | era_2025_2026_6thang |
|  | M15 | EUR | EliteQuality_3 | 68.542 | 1.728 | 41.26 | 6.14 | 11.163 | 143 | era_2025_h2 |
|  | M5 | EUR | ElitePF | 102.875 | 2.062 | 46.45 | 9.28 | 11.086 | 155 | era_2025_h2 |
|  | M5 | GBP | StretchR | 264.683 | 1.525 | 41.47 | 24.07 | 10.996 | 668 | era_5_thang_cuoi_2025 |
|  | M15 | GBP | EliteRDD | 55.068 | 2.767 | 53.23 | 5.02 | 10.97 | 62 | era_2025_h2 |
|  | M15 | EUR | ElitePF_3 | 63.366 | 2.112 | 47.42 | 5.89 | 10.758 | 97 | era_2025_h2 |
|  | M15 | EUR | StretchWR_2 | 77.189 | 1.74 | 41.06 | 7.2 | 10.721 | 151 | era_2025_h2 |
|  | M5 | GBP | EliteQuality_2 | 46.324 | 2.51 | 48.15 | 4.34 | 10.674 | 54 | era_2025_2026_6thang |
|  | M5 | GBP | LowDD_2 | 41.601 | 2.319 | 51.11 | 3.97 | 10.479 | 45 | era_2025_2026_6thang |
|  | M15 | EUR | EliteRDD | 88.371 | 1.396 | 36.43 | 8.76 | 10.088 | 280 | era_2025_h2 |
|  | M15 | GBP | BestBalance | 90.828 | 1.727 | 46.01 | 9.11 | 9.97 | 213 | era_2025_h2 |
|  | M5 | EUR | EliteWR | 115.886 | 1.845 | 45.2 | 11.77 | 9.846 | 177 | era_2025_h2 |
|  | M15 | GBP | BestWinRate | 83.014 | 1.667 | 46.19 | 8.52 | 9.743 | 210 | era_2025_h2 |
|  | M15 | GBP | BestTotalR | 88.599 | 1.731 | 45.41 | 9.11 | 9.725 | 218 | era_2025_h2 |
| ★ | M15 | GBP | LowDD | 23.519 | 2.791 | 61.9 | 2.42 | 9.719 | 21 | era_2025_h2 |
|  | M15 | GBP | EliteWR_2 | 33.965 | 2.989 | 57.89 | 3.54 | 9.595 | 38 | era_2025_2026_6thang |
|  | M15 | EUR | LowDD | 54.011 | 1.483 | 40.56 | 5.78 | 9.344 | 143 | era_2025_h2 |
|  | M5 | GBP | EliteWR | 237.592 | 1.801 | 42.45 | 25.6 | 9.281 | 424 | era_5_thang_cuoi_2025 |
|  | M5 | GBP | EliteWR_2 | 48.328 | 2.431 | 50.0 | 5.22 | 9.258 | 50 | era_2025_2026_6thang |
|  | M15 | EUR | StretchR_2 | 124.119 | 1.677 | 39.93 | 13.43 | 9.242 | 283 | era_2025_h2 |
|  | M5 | EUR | LowDD | 81.941 | 1.76 | 42.86 | 8.91 | 9.197 | 154 | era_2025_h2 |
|  | M5 | GBP | ElitePF | 213.004 | 1.816 | 42.26 | 23.98 | 8.883 | 407 | era_5_thang_cuoi_2025 |
|  | M15 | GBP | ElitePF_2 | 41.614 | 3.932 | 58.62 | 4.72 | 8.817 | 29 | era_2025_2026_6thang |
|  | M15 | EUR | StretchWR_3 | 73.585 | 1.781 | 41.1 | 8.42 | 8.739 | 146 | era_2025_h2 |
|  | M15 | EUR | StretchWR | 79.341 | 1.839 | 42.25 | 9.24 | 8.587 | 142 | era_2025_h2 |
|  | M15 | EUR | EliteWR_2 | 64.825 | 2.069 | 45.19 | 7.8 | 8.311 | 104 | era_2025_h2 |
|  | M15 | EUR | ElitePF_2 | 56.544 | 1.823 | 41.38 | 7.01 | 8.066 | 116 | era_2025_h2 |
|  | M15 | EUR | StretchR | 113.575 | 1.522 | 39.21 | 14.33 | 7.926 | 278 | era_2025_h2 |
|  | M15 | EUR | EliteWR | 47.312 | 1.717 | 42.55 | 6.19 | 7.643 | 94 | era_2025_h2 |
|  | M5 | GBP | ElitePF_2 | 49.241 | 2.524 | 50.98 | 6.57 | 7.495 | 51 | era_2025_2026_6thang |
|  | M15 | GBP | StretchR | 68.371 | 1.523 | 40.99 | 9.54 | 7.167 | 222 | era_2025_h2 |
|  | M15 | EUR | LowDD_2 | 32.854 | 1.572 | 40.79 | 4.85 | 6.774 | 76 | era_2025_h2 |
|  | M15 | EUR | EliteQuality | 32.682 | 2.15 | 42.0 | 4.98 | 6.563 | 50 | era_2025_h2 |
|  | M15 | GBP | LowDD_2 | 22.189 | 1.98 | 45.83 | 3.51 | 6.322 | 24 | era_2025_2026_6thang |
|  | M5 | GBP | StretchR_2 | 145.971 | 1.387 | 39.53 | 23.84 | 6.123 | 506 | era_2025_2026_6thang |
|  | M15 | GBP | EliteWR | 17.027 | 2.632 | 54.55 | 3.63 | 4.691 | 22 | era_2025_h2 |
|  | M15 | GBP | BestPF | 80.958 | 1.639 | 40.21 | 17.35 | 4.666 | 189 | era_5_thang_cuoi_2025 |
|  | M15 | EUR | ElitePF | 27.49 | 2.012 | 39.22 | 5.94 | 4.628 | 51 | era_2025_h2 |
|  | M15 | EUR | BestQuality | 61.14 | 1.259 | 36.6 | 15.33 | 3.988 | 235 | era_2025_h2 |
|  | M15 | EUR | BestTotalR | 54.323 | 1.211 | 34.96 | 15.77 | 3.445 | 226 | era_2025_h2 |
|  | M15 | EUR | BestPF | 41.354 | 1.216 | 33.18 | 13.95 | 2.964 | 223 | era_2025_h2 |
|  | M5 | GBP | LowDD | 24.07 | 1.561 | 41.67 | 9.33 | 2.58 | 48 | era_2025_h2 |
|  | M15 | EUR | BestBalance | 55.98 | 1.241 | 35.78 | 22.33 | 2.507 | 232 | era_2025_h2 |
|  | M15 | EUR | BestWinRate | 41.458 | 1.133 | 33.89 | 17.24 | 2.405 | 239 | era_2025_h2 |
|  | M15 | EUR | EliteQuality_2 | 19.001 | 1.536 | 36.0 | 8.35 | 2.276 | 50 | era_2025_h2 |

## Kỳ vọng GUIDE (qualitative)

1. Cùng OOS → so sánh EUR/GBP × M15/M5 hợp lệ.
2. M15 EUR thường PF/WR/R/DD cao hơn, ít lệnh hơn M5.
3. M5 thường Total R / mật độ cao hơn; BestQuality R/DD cạnh tranh.
4. GBP frontier khác EUR (spread/noise) — không copy genome.
5. Objective `quality` → active nên nghiêng BestQuality/Balance chứ không chỉ BestTotalR.
