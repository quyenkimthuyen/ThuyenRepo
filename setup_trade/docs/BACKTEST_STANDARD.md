# Backtest Standard — Setup Trade v1

## Chi phí

- Spread: 1.0 pip (config `costs.json`)
- Slippage: 0.2 pip mỗi chiều
- Round-trip cost áp dụng tại entry và exit trong `simulator/trade.py`

## Entry

- Tín hiệu phát sinh khi state machine báo `ENTRY_READY` trên **close nến H1**
- Không lookahead: RSI H4 chỉ cập nhật sau khi nến H4 đóng (`add_h4_rsi_closed_only`)

## SL / TP

| Hướng | TP | SL |
|-------|----|----|
| LONG | RSI H4 chạm band 68–72 | RSI H4 close < 48 hoặc price SL (ATR) |
| SHORT | RSI H4 chạm band 28–32 | RSI H4 close > 52 hoặc price SL (ATR) |

- `sl_on_ema_break`: tùy config (mặc định `false` v1)
- Giả định fill: SL tại giá stop; TP tại close bar khi RSI đạt band

## Walk-forward

- Label year T → optimize T+1 → final test T+2
- API từ chối optimize/backtest trên năm label (xem `config/periods.json`)

## PASS criteria

```text
trades >= 30
profit_factor >= 1.3
max_drawdown_pips <= 250
expectancy_pips > 0
monte_carlo_pf_p5 >= 1.0
```
