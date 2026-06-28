# LongBTC — BTC Long-Term Research Lab

Nền tảng **frontend-only** nghiên cứu đầu tư Bitcoin dài hạn: xác định chu kỳ halving 4 năm, xu hướng, sóng Elliott và chu kỳ tâm lý thị trường.

**Version:** 2.0.0

## Khởi chạy

```bash
cd LongBTC
python3 -m http.server 8080
```

Mở [http://localhost:8080](http://localhost:8080)

Lần đầu: **Data Manager** → Reload Default Data (hoặc tự động tải BTCUSD W).

## Pipeline phân tích

| Bước | Module | Mô tả |
|------|--------|-------|
| 1 | Chu kỳ 4 năm | Vị trí trong chu kỳ halving, 4 giai đoạn |
| 2 | Xu hướng | Swing pivot, HH/HL, LH/LL, đoạn tăng/giảm/đi ngang |
| 3 | Sóng Elliott | Đếm sóng xung (1-5) và điều chỉnh (ABC) |
| 4 | Tâm lý TT | Ánh xạ sang giai đoạn tâm lý thị trường |

## Các màn hình

| Màn hình | Phím tắt | Mô tả |
|----------|----------|-------|
| Biểu đồ BTC | Ctrl+1 | Nến + overlay swing/xu hướng/chu kỳ |
| Tổng quan | Ctrl+2 | Dashboard tổng hợp phân tích |
| Chu kỳ 4 năm | Ctrl+3 | Halving, tiến độ chu kỳ |
| Xu hướng | Ctrl+4 | Swing và đoạn xu hướng |
| Sóng Elliott | Ctrl+5 | Chi tiết sóng |
| Tâm lý TT | Ctrl+6 | Vòng tâm lý thị trường |
| Data Manager | Ctrl+7 | Import/export OHLCV |
| Tài liệu | Ctrl+0 / F1 | Hướng dẫn tiếng Việt |

## Tech stack

- HTML5, CSS3, Vanilla JavaScript ES2023
- IndexedDB + LocalStorage
- Lightweight Charts
- Không backend, không kết nối broker

## Cấu trúc

```
LongBTC/
├── src/
│   ├── analysis/     # Cycle, Trend, Elliott, Psychology engines
│   ├── chart/        # Chart + analysis overlays
│   ├── data/         # IndexedDB, import/export
│   ├── core/         # App, Config, EventBus
│   └── ui/           # Views
├── data/defaults/    # BTCUSD W, D1, H4
└── tests/
```

## Chạy tests

```bash
node tests/run-all.mjs
```

## Lưu ý

Công cụ nghiên cứu — không phải lời khuyên đầu tư. Quá khứ không đảm bảo kết quả tương lai.
