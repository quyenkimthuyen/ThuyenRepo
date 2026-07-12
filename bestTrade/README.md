# BestTrade

Ứng dụng Pin Bar Elite với **paper trading**, **forward test blind**, và **analytics** — bước chuẩn bị trước khi trade thật.

## Tính năng mới

| Tính năng | Mô tả |
|-----------|--------|
| **Validated vs Sandbox** | Params khóa cho forward test; sandbox chỉ để thử |
| **Paper trading** | Đánh giá tín hiệu trên nến đóng, journal JSONL |
| **Forward test** | Khóa params + so sánh paper vs backtest cùng kỳ |
| **Monte Carlo** | Bootstrap shuffle trên lệnh OOS |
| **Monthly/Quarterly** | Phân tích ổn định theo tháng/quý |
| **Stress spread** | Backtest với spread 0.5 / 1.0 / 1.5 pip |

## Cài đặt

```bash
cd bestTrade
pip install -r requirements.txt
```

Cần `../systemtrain` với dữ liệu EURUSD.

## Chạy app

```bash
streamlit run run_app.py
```

## Backtest report

```bash
python3 run_report.py                      # mặc định 2023–2026
python3 run_report.py --from-year 2023 --to-year 2026 --equity 1000
```

Lưu vào `output/`:
- `backtest_report_2023_2026.json`
- `backtest_report_2023_2026.txt`
- `backtest_report_2023_2026.md`

## Paper trading CLI

```bash
# Chạy 1 lần
python3 run_paper.py

# Loop mỗi 15 phút (cron-friendly)
python3 run_paper.py --loop --interval-minutes 15

# Reset state
python3 run_paper.py --reset
```

## Workflow khuyến nghị

```
1. Dashboard → xem Monte Carlo & OOS metrics
2. Paper & Forward → "Bắt đầu forward test" (Validated mode)
3. Chạy paper định kỳ 3–6 tháng
4. So sánh paper vs backtest — delta return nên nhỏ
5. Analytics → monthly stability, stress spread
6. Chỉ sau đó mới trade thủ công size nhỏ
```

## Tests

```bash
python3 tests/test_engine.py
```

## Lưu ý

- Paper **không** kết nối broker — chỉ mô phỏng signal + fill theo engine
- Forward test yêu cầu **Validated mode** (params khóa)
- Sandbox chỉ để nghiên cứu, không dùng cho quyết định live
