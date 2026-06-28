# Price Action Research Lab (PARL)

A **frontend-only** research platform for Price Action traders: discover which setups, pairs, timeframes, and parameters have real edge after spread — before risking live capital. Not a trading bot — no auto-trading, no backend, no broker connection.

**Version:** 1.0.0

## Quick start

```bash
cd Forex
python3 -m http.server 8080
```

Open [http://localhost:8080](http://localhost:8080)

On first launch: **Data Manager** → reload default data or import CSV.

## Features

| Module | Shortcut | Description |
|--------|----------|-------------|
| Chart | Ctrl+1 | Candlestick chart + bar-by-bar replay (UTC jump) |
| Data Manager | Ctrl+2 | Import/export OHLCV via IndexedDB |
| Strategies | Ctrl+3 | 7 Price Action setups (Break & Retest, EMA, Wyckoff, …) |
| Compare | Ctrl+4 | Rank strategies on same symbol/TF by expectancy |
| Simulation | Ctrl+5 | Backtest + optional AI score filter & compare |
| Statistics | Ctrl+6 | Expectancy, PF, drawdown, equity curve |
| Reports | Ctrl+7 | Dashboard, heatmaps, CSV/JSON/PNG/PDF export |
| Optimizer | Ctrl+8 | Grid search (parallel), Sensitivity chart, WF, Monte Carlo |
| AI Signals | Ctrl+9 | 0–100 signal scores with factor breakdown |
| Documentation | Ctrl+0 / F1 | In-app usage guide |

## Tech stack

- HTML5, CSS3, Vanilla JavaScript ES2023
- IndexedDB (candles + large research results) + LocalStorage (settings)
- Lightweight Charts
- Web Workers for heavy computations

## Documentation

- [Usage guide (English)](docs/USAGE.md)
- [Hướng dẫn sử dụng (Tiếng Việt)](docs/HUONG_DAN.md)
- [Strategy specification](docs/STRATEGY_SPECIFICATION.md)
- In-app: press **Ctrl+0** or **F1**

## Project structure

```
Forex/
├── index.html
├── docs/           # Specifications & guides
├── css/            # Stylesheets
├── src/
│   ├── core/       # App, Config, EventBus
│   ├── data/       # IndexedDB, import/export
│   ├── chart/      # Chart engine
│   ├── strategy/   # Plugin system
│   ├── strategies/ # Built-in PA setups
│   ├── research/   # Strategy compare engine
│   ├── simulation/ # Trade engine
│   ├── statistics/ # Performance metrics
│   ├── analytics/  # Heatmaps
│   ├── report/     # Export
│   ├── optimizer/  # Grid search (parallel), sensitivity, walk-forward, MC
│   ├── scoring/    # AI signal scores
│   ├── performance/# Web Workers
│   └── ui/         # Views
└── tests/          # Node.js test runners
```

## Run tests

```bash
node tests/run-all.mjs
```

## License

Research tool — use at your own risk. Past performance does not guarantee future results.
