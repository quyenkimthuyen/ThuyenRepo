# BestTrade

Ứng dụng giao dịch chuyên nghiệp xây dựng trên chiến lược **Pin Bar Elite** — kết quả tốt nhất sau kiểm chứng out-of-sample trong [SystemTrain](../systemtrain).

## Chiến lược

**Pin Bar Elite** là chiến lược price action trên EURUSD 1H:

- Pin bar tại swing high/low (wick dài, thân nhỏ)
- Filter 4H stack + ADX 1H thấp
- Session London (9–16 UTC)
- Risk 2%/lệnh, RR 2.0

### Kết quả kiểm chứng (SystemTrain OOS 2 năm)

| Metric | Giá trị |
|--------|---------|
| Return | +33.0% |
| Win Rate | 61% |
| Profit Factor | 2.90 |
| Max Drawdown | 4.0% |
| Số lệnh | 18 |

So với Wyckoff (+18.7%) và RSI Divergence (+19.0%), Pin Bar Elite có return cao nhất với số lệnh đủ để đánh giá thống kê.

## Cài đặt

```bash
cd bestTrade
pip install -r requirements.txt
```

Yêu cầu project **systemtrain** ở thư mục sibling (`../systemtrain`) với dữ liệu EURUSD đã tải.

## Chạy app

```bash
streamlit run run_app.py
```

## Chạy backtest CLI

```bash
python3 run_backtest.py
python3 run_backtest.py --year 2024 --equity 5000 --json
```

## Kiến trúc

```
bestTrade/
├── run_app.py          # Streamlit UI
├── run_backtest.py     # CLI backtest
├── config/strategy.yaml
└── besttrade/
    ├── engine.py       # Wrapper SystemTrain engine
    ├── paths.py        # Link tới systemtrain
    └── ui/             # Theme & components
```

Engine backtest, signal detection và chart component được kế thừa trực tiếp từ SystemTrain — đảm bảo kết quả nhất quán với quy trình kiểm chứng gốc.
