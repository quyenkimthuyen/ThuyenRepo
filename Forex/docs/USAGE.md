# PARL Usage Guide

Complete usage documentation for **Price Action Research Lab v1.0.0**.

## Installation

PARL runs entirely in the browser. Serve the project folder over HTTP:

```bash
cd Forex
python3 -m http.server 8080
```

Open `http://localhost:8080`. Do not open `index.html` directly (`file://` breaks ES modules).

### Requirements

- Modern browser (Chrome, Firefox, Edge)
- Python 3 or any static HTTP server
- No Node.js or database server required

---

## Recommended workflow

```
1. Import data     →  Data Manager (Ctrl+2)
2. Scan strategy   →  Strategies (Ctrl+3)
3. Run backtest    →  Simulation (Ctrl+4)
4. Review metrics  →  Statistics (Ctrl+5)
5. Export report   →  Reports (Ctrl+6)
6. Optimize params →  Optimizer (Ctrl+7)
7. Score signals   →  AI Signals (Ctrl+8) — auto after scan
```

---

## Module reference

### Data Manager (Ctrl+2)

- **Import:** CSV, JSON, or `.gz` files
- **Export:** Download candles as CSV/JSON
- **Reload defaults:** Load bundled OHLCV from `data/defaults/`
- **Storage:** IndexedDB (`parl_data` database)

**CSV format:**
```
timestamp,datetime,open,high,low,close,volume
```

### Chart (Ctrl+1)

- Candlestick chart with EMA 20 and EMA 50
- **Replay controls:** Play, Pause, Next, Previous, Reset, Live
- Replay never reveals future candles
- For datasets > 50,000 bars, chart shows the most recent window

**Replay shortcuts (chart view only):**

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| → | Next candle |
| ← | Previous candle |
| Home | Reset replay |
| End | Go live |

### Strategies (Ctrl+3)

Three built-in Price Action setups (see `docs/STRATEGY_SPECIFICATION.md`):

| ID | Name |
|----|------|
| `break-retest` | Break & Retest |
| `ema-pullback` | EMA Pullback |
| `liquidity-grab` | Liquidity Grab |

- Configure parameters per strategy
- **Run Selected** — scan one strategy
- **Run All Enabled** — scan all active plugins
- Signals export as JSON

### Simulation (Ctrl+4)

Mode 1: one strategy, one pair, one timeframe.

**Trade engine settings:**
- Order type: market or pending
- Spread, slippage, lot size
- Trailing stop, break-even, partial close

Results automatically update Statistics and Reports.

### Statistics (Ctrl+5)

Metrics: win rate, expectancy, profit factor, max drawdown, Sharpe, streaks, avg RR/SL/TP.

Includes equity curve and drawdown charts. Export JSON.

### Reports (Ctrl+6)

**Dashboard tab:** summary cards + equity curve

**Heatmaps tab:** performance by month, day, hour, session, strategy, pair, timeframe

**Export tab:**
- Trades CSV
- Full report JSON
- Dashboard PNG
- Print / Save as PDF

### Optimizer (Ctrl+7)

**Grid Search**
- Select parameters and value lists (`1,2,3` or `10:50:10`)
- Max 500 combinations
- Rank by expectancy, net profit, PF, Sharpe, or win rate

**Walk Forward**
- Rolling in-sample / out-of-sample windows
- Uses current strategy parameters

**Monte Carlo**
- Requires prior simulation
- Shuffles trade order (default 1000 iterations)
- Shows P5 / P50 / P95 balance distribution

### AI Signals (Ctrl+8)

Every signal scored 0–100 after strategy scan.

**Factors:** trend, momentum, location, volatility, price action quality, RR, session, spread

**Grades:** A (≥80), B (≥65), C (≥50), D (≥35), F (<35)

Use the min-score slider to filter low-quality signals.

---

## Keyboard shortcuts

| Shortcut | View |
|----------|------|
| Ctrl+B | Toggle sidebar |
| Ctrl+1–8 | Navigate views |
| Ctrl+9 / F1 | Documentation |

---

## Data persistence

| Storage | Content |
|---------|---------|
| IndexedDB | OHLCV candles |
| LocalStorage | Settings, strategy configs, simulation & statistics results |

Clear browser site data to reset. Export results before clearing.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Empty chart | Import or generate data in Data Manager |
| No statistics | Run Simulation first |
| Monte Carlo error | Run Simulation to generate trades |
| Grid search slow | Reduce parameter combinations; workers activate at 10k+ candles |
| Boot error: private field `#log` | Update to latest PARL. Use modern Chrome/Edge/Firefox and serve via `http://` |

---

## Further reading

- `docs/STRATEGY_SPECIFICATION.md` — exact strategy rules
- `docs/HUONG_DAN.md` — Vietnamese guide
- In-app docs: **Ctrl+9**
