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
3. Compare setups  →  Compare (Ctrl+4) — optional, same symbol/TF
4. Run backtest    →  Simulation (Ctrl+5)
5. Review metrics  →  Statistics (Ctrl+6)
6. Export report   →  Reports (Ctrl+7)
7. Optimize params →  Optimizer (Ctrl+8)
8. Score signals   →  AI Signals (Ctrl+9) — auto after scan
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
- **Replay controls:** Play, Pause, Next, Previous, Reset, Live, **Jump to date**
- Jump date field uses **UTC** (matches candle timestamps)
- Replay never reveals future candles
- For datasets > 50,000 bars, chart shows the most recent window
- Signal review: entry/SL/TP overlay from AI Signals or Simulation trade list

**Replay shortcuts (chart view only):**

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| → | Next candle |
| ← | Previous candle |
| Home | Reset replay |
| End | Go live |

### Strategies (Ctrl+3)

Seven built-in Price Action setups (see `docs/STRATEGY_SPECIFICATION.md`):

| ID | Name |
|----|------|
| `break-retest` | Break & Retest |
| `ema-pullback` | EMA Pullback |
| `liquidity-grab` | Liquidity Grab |
| `inside-bar-breakout` | Inside Bar Breakout |
| `pin-bar-rejection` | Pin Bar Rejection |
| `wyckoff-spring-utad` | Wyckoff Spring / UTAD |
| `wyckoff-range-test` | Wyckoff Range Test |

- Configure parameters per strategy
- **Run Selected** — scan one strategy
- **Run All Enabled** — scan all active plugins
- Signals export as JSON

### Compare (Ctrl+4)

Run multiple strategies on the **same symbol and timeframe** and rank by expectancy.

- Tick which strategies to include (all enabled by default)
- **Compare** — scans each setup, simulates trades with current Simulation settings, sorts by expectancy
- Best row highlighted; results persist across sessions

Use this before committing to one setup or before deep parameter tuning.

### Simulation (Ctrl+5)

Mode 1: one strategy, one pair, one timeframe.

**Trade engine settings:**
- Order type: market or pending
- Spread, slippage, lot size
- Trailing stop, break-even, partial close

**AI score filter (optional):**
- Enable **AI score filter** and set **Min score** (default 65)
- Simulation scores signals, then trades only those at/above the threshold
- **Compare vs all signals** — side-by-side summary: all signals vs filtered set (WR, Net, Expectancy)
- Primary trade list uses the **filtered** set when filter is on

Results automatically update Statistics and Reports.

### Statistics (Ctrl+6)

Metrics: win rate, expectancy, profit factor, max drawdown, Sharpe, streaks, avg RR/SL/TP.

Includes equity curve and drawdown charts. Export JSON.

### Reports (Ctrl+7)

**Dashboard tab:** summary cards + equity curve

**Heatmaps tab:** performance by month, day, hour, session, strategy, pair, timeframe

**Export tab:**
- Trades CSV
- Full report JSON
- Dashboard PNG
- Print / Save as PDF

### Optimizer (Ctrl+8)

Four tabs: **Grid Search**, **Sensitivity**, **Walk Forward**, **Monte Carlo**.

**Grid Search**
- Select parameters and value lists (`1,2,3` or `10:50:10`)
- Max 500 combinations
- **Suggest from data** — fill value grids from candle volatility (avg 14-bar range + timeframe)
- **Restore defaults** — reset to default ±1-step grids per strategy
- Form state (ticks, values, rank, auto WF) **persists when switching tabs** (per strategy, current session only)
- Rank by expectancy, net profit, PF, Sharpe, or win rate
- **Auto walk-forward on best combo** (default on)
- **Apply best to Strategy** — save rank #1 combo to Strategies (Ctrl+3)
- **Parallel execution** — ≥4 combos use Web Worker pool (4 threads) when available; results header shows `(parallel)`

**Sensitivity** (new tab)
- Uses data from the **last Grid Search run** (`optimizedParamKeys` + `paramGrid` stored in results)
- Line chart: Win Rate (left axis) and Expectancy / Net Profit (right axis, $)
- Toggle metrics: **WR / Exp / Net**
- Parameter dropdown lists only params included in that grid run
- Hides buckets with &lt;5 avg trades per combo

**Walk Forward**
- Rolling in-sample / out-of-sample windows
- Uses current strategy parameters (or best combo from grid)

**Monte Carlo**
- Requires prior simulation
- Shuffles trade order (default 1000 iterations)
- Shows P5 / P50 / P95 balance distribution

**Recommended workflow:** Grid Search → Sensitivity chart → Apply best to Strategy → Walk Forward → Simulation → Monte Carlo

#### Optimizer updates (28 Jun 2025)

- **Sensitivity** tab split from Top Results  
- **Suggest from data**, **Restore defaults**, **Apply best to Strategy**  
- **Parallel** grid search via Web Worker pool (≥4 combos)  
- Grid form **persists across tabs** (per strategy, current session)  
- Sensitivity uses **gridded params only** (`optimizedParamKeys`) + **Net Profit** metric  
- Chart toolbar: param dropdown + **WR / Exp / Net** toggles  

### AI Signals (Ctrl+9)

Every signal scored 0–100 after strategy scan.

**Factors:** trend, momentum, location, volatility, price action quality, RR, session, spread

**Grades:** A (≥80), B (≥65), C (≥50), D (≥35), F (<35)

Use the min-score slider to filter the signal list. To **backtest** only high-score signals, enable **AI score filter** in Simulation.

---

## Keyboard shortcuts

| Shortcut | View |
|----------|------|
| Ctrl+B | Toggle sidebar |
| Ctrl+1 | Chart |
| Ctrl+2 | Data Manager |
| Ctrl+3 | Strategies |
| Ctrl+4 | Compare |
| Ctrl+5 | Simulation |
| Ctrl+6 | Statistics |
| Ctrl+7 | Reports |
| Ctrl+8 | Optimizer |
| Ctrl+9 | AI Signals |
| Ctrl+0 / F1 | Documentation |

---

## Data persistence

| Storage | Content |
|---------|---------|
| IndexedDB (`parl_data`) | OHLCV candles **and** large result blobs (simulation, statistics, reports, optimizer, scored signals, strategy compare) |
| LocalStorage | Lightweight settings, strategy parameter configs, panel sizes |

Large results migrate automatically from older LocalStorage saves to IndexedDB on first load.

Clear browser site data (or **Reset app** in Data Manager) to wipe everything. Export results before clearing.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Empty chart | Import or generate data in Data Manager |
| No statistics | Run Simulation first |
| Monte Carlo error | Run Simulation to generate trades |
| Grid search slow | Reduce combinations (max 500). ≥4 combos run in parallel on Web Workers (4 threads) when available |
| Sensitivity tab empty | Run Grid Search first; need ≥2 distinct values for at least one gridded parameter |
| Optimizer form reset | Grid form persists across tabs in-session; full page reload clears it — use **Restore defaults** to reset grids |
| Grid search storage error | Reload app — results now use IndexedDB; old quota errors should not recur |
| Jump date wrong timezone | Jump field is UTC — match timestamps shown in replay bar |
| Boot error: private field `#log` | Update to latest PARL. Use modern Chrome/Edge/Firefox and serve via `http://` |

---

## Further reading

- `docs/STRATEGY_SPECIFICATION.md` — exact strategy rules
- `docs/HUONG_DAN.md` — Vietnamese guide
- In-app docs: **Ctrl+0** or **F1**
