# ForexForge v2

Rebuild: giữ walk-forward + KB causal + cost model; UI mỏng; SQLite; job nền; paper sim; broker stub.

## Cài đặt

```bash
cd EdgeMinerV2
pip install -r requirements.txt
pip install -e .
pip install streamlit plotly   # UI
```

## Chạy app

```bash
streamlit run forexforge/ui_app.py
# http://localhost:8501
```

## 6 bước Usage Guide

1. **Data Hub** — Refresh Dukascopy EUR/USD H1  
2. **Backtest Lab** — KB OFF + cost model, archive report  
3. **KB Era Hub** — học era, hard-block `trained_to > oos_from`  
4. **Report Compare** — metrics + equity side-by-side  
5. **Risk / Journal / Inspector** — DD, trades, rules/genomes  
6. **Paper Monitor** — signal + fill cost model + journal  

## CLI

```bash
python -m forexforge backtest --oos-from 2024-01-01 --oos-to 2024-12-31
python -m forexforge learn --kb-profile era_2022_2023 --until-date 2023-12-31 --epochs 3
python -m forexforge backtest --kb --kb-profile era_2022_2023 --oos-from 2024-01-01
python -m forexforge paper
python -m forexforge jobs
python -m forexforge reports --compare id1,id2
python -m forexforge migrate --src C:\Work\ThuyenRepo\EdgeMiner1
```

## Kiến trúc

```
UI (Streamlit mỏng) → Jobs/CLI → Core (wf_runner / KB / cost)
                                      ↓
                              SQLite + Parquet OHLC
                                      ↓
                         Paper sim → BrokerAdapter (stub / future MT5)
```

## DoD

| Mục | Trạng thái |
|-----|------------|
| Baseline WF + cost semantics | Core extract từ EdgeMiner1 |
| Anti-leakage CI + UI block | `leakage.py` + tests |
| Job nền không treo UI | `jobs.py` + `--bg` |
| Report archive compare ≥ 2 | SQLite `reports` |
| Paper journal bền | `paper_sim` jsonl |
| README = Usage Guide | trang Usage Guide trong app |

## Test

```bash
pytest -q
```
