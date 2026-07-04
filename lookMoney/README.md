# lookMoney

Python backtester for **EUR/USD H1** during **London** and **New York** sessions.

## Strategy (v2 — H4 trend pullback)

Trend-pullback on H1 with **H4 EMA50 alignment**:

- Sessions: **London 07–16 UTC** + **New York 13–21 UTC**
- **H4 trend** must agree (close vs EMA50 on 4H)
- **H1**: EMA20 pullback + bullish/bearish candle + StochRSI cross
- **ADX** 18–40 (trend without exhaustion)
- **SL**: structural swing ± ATR buffer (wider stop → higher win rate)
- **TP**: exactly **2R** from entry (after spread)
- **Risk**: **1%** account per trade (position sized to SL distance)

Previous strategies tested (confluence pullback, London Asian breakout) did not reach 50% win rate on this dataset.

## Risk (hard-coded rules)

| Rule | Default |
|------|---------|
| Risk per trade | 1% |
| Max daily loss | 3% → halt |
| Max drawdown | 15% → halt |
| Max consecutive losses | 5 → halt |
| Min R:R | 1.5 |

## Setup

```bash
cd lookMoney
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run backtest

```bash
python main.py backtest
python main.py backtest --refresh
python main.py backtest -o results/
python main.py backtest --csv data/eurusd_h1.csv --start 2024-01-01
```

### Fair validation (1y develop + 2y OOS)

To avoid overfitting, use a fixed split from dataset start:

| Phase | Period | Purpose |
|-------|--------|---------|
| **Develop** | Year 1 | Build and tune strategy parameters |
| **OOS** | Years 2–3 | Blind test — frozen params, causal signals (no future bars) |

```bash
# Full protocol: develop then OOS
python main.py validate -o results/validate/

# Or run phases separately
python main.py backtest --phase develop -o results/develop/
python main.py backtest --phase oos -o results/oos/
```

Tune `config/eur_usd.yaml` only using **develop** metrics. **OOS** is the honest score.

## Project layout

```
config/eur_usd.yaml      # Strategy & risk parameters
src/lookmoney/
  data/fetcher.py
  execution/mt5_data.py  # MT5 H1 feed
  live/runner.py         # Paper trade loop
  live/state.py          # Paper state persistence
  strategies/eur_usd_h1.py
  risk/manager.py
  backtest/engine.py
main.py
```

## Paper trade (MT5 demo + simulated P&L)

Poll **H1 từ MT5 demo**, chạy strategy, **mô phỏng khớp lệnh local** (không gửi order lên broker).

### Chuẩn bị MT5 demo

1. Cài [MetaTrader 5](https://www.metatrader5.com/) + mở **demo account**
2. Đăng nhập terminal, bật symbol **EURUSD** trong Market Watch
3. `pip install MetaTrader5`
4. Chỉnh `config/eur_usd.yaml` → section `mt5` (symbol, login nếu cần)

### Lệnh

```bash
# Một lần (sau khi nến H1 đóng, mặc định từ :02 phút mỗi giờ)
python main.py paper

# Xem trạng thái
python main.py paper --status

# Reset tài khoản ảo
python main.py paper --reset --run

# Vòng lặp mỗi giờ
python main.py paper-loop

# Test không cần MT5 (dùng CSV)
python main.py paper --csv data/eurusd_h1.csv --force
```

### File log

| File | Nội dung |
|------|----------|
| `data/paper_state.json` | Balance, lệnh mở, bar đã xử lý |
| `data/paper_trades.csv` | Lịch sử đóng lệnh + P&L |
| `data/paper_signals.csv` | Signal mở / bị risk chặn |

## Next steps

1. Run `python main.py validate` and review OOS metrics
2. Paper trade: `python main.py paper` (MT5 demo) or `python main.py paper-loop`
3. Compare paper logs vs backtest after 2–3 months
4. Optional: send real demo orders via MT5 API (level 3)

**Disclaimer:** Past performance does not guarantee future results. This is research tooling, not financial advice.
