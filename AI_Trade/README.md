# AI Trade Lab

Ứng dụng label setup forex **EURUSD 1H**, phân tích pattern từ setup bạn đánh dấu, và backtest theo split thời gian.

## Workflow

1. **Train (2022)** — đánh dấu setup trên chart: Entry → SL → TP
2. **Analyze** — AI trích pattern chung từ setup, sinh rule chiến lược
3. **Backtest 2023** — validation (tinh chỉnh nếu cần)
4. **Backtest 2024–26** — out-of-sample test (không optimize)

## Cài đặt

```bash
cd AI_Trade
pip install -r requirements.txt
python scripts/fetch_data.py   # tải EURUSD H1 2022→nay từ Dukascopy
chmod +x run.sh
./run.sh
```

Mở: http://127.0.0.1:8766

## Cấu trúc

```
AI_Trade/
  backend/          # FastAPI: data, indicators, labels, analyzer, backtest
  frontend/         # Chart (Lightweight Charts) + UI label
  config/splits.json
  data/
    eurusd_h1.csv
    labels/setups.json
    strategies/latest.json
  scripts/fetch_data.py
```

## Label setup

- Chọn **Long/Short**
- Click chart theo thứ tự: **Entry → SL → TP**
- SL/TP có thể chỉnh bằng input hoặc click chart
- Chỉ lưu được setup trong **năm Train (2022)**

## Split dữ liệu

| Tập | Năm | Mục đích |
|-----|-----|----------|
| Train | 2022 | Label + học pattern |
| Validation | 2023 | Tinh chỉnh |
| Test | 2024–2026 | Out-of-sample |

## Pass criteria (backtest)

- Profit factor ≥ 1.3
- Max drawdown ≤ 20% (ước lượng pip)
- ≥ 30 lệnh

## Lưu ý

- Cần **≥ 5 setup** (win/loss) trước khi Analyze có ý nghĩa; khuyến nghị 50+
- Backtest mô phỏng spread 1 pip + slippage 0.2 pip
- Test set chỉ chạy khi đã hài lòng với validation — tránh overfit
