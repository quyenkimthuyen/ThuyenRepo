"""Usage Guide — matches product DoD 1:1."""
from __future__ import annotations

import streamlit as st


def render() -> None:
  st.header("Usage Guide — ForexForge v2")
  st.markdown(
    """
## Vong research (giu nguyen)

**Data → Backtest KB OFF → Hoc KB theo era → OOS KB ON → Compare → Hold-out → Paper**

| Buoc | Trang | Lam gi |
|------|-------|--------|
| 1 | Data Hub | Refresh Dukascopy EUR/USD H1 |
| 2 | Backtest Lab | KB OFF, spread 1.0 / slip 0.3, luu report |
| 3 | KB Era Hub | Tao profile era, hoc 3–5 epoch, `trained_to <= oos_from` |
| 4 | Report Compare | So sanh metrics + equity; chi chap nhan neu R/DD tot hon |
| 5 | Risk / Journal / Inspector | Kiem tra DD, trades, rules/genomes; hold-out truoc promote |
| 6 | Paper Monitor | Signal + fill theo cost model, journal tu dong |

## Nguyen tac vang

- Danh gia strategy: **KB OFF** + cost model
- Cai thien: **KB ON** + profile dung giai doan
- Leakage: hard **block** neu `trained_to > oos_from`
- Job nang chay **nen** — UI khong treo
- Live broker la phase rieng (`BrokerAdapter`), khong tron vao miner

## CLI

```bash
python -m forexforge backtest --oos-from 2024-01-01 --oos-to 2024-12-31
python -m forexforge learn --kb-profile era_2022_2023 --until-date 2023-12-31 --epochs 3
python -m forexforge backtest --kb --kb-profile era_2022_2023 --oos-from 2024-01-01
python -m forexforge reports --compare id1,id2
```

## Promote

Can hold-out >= 3 thang + leakage OK + hold-out total_r > 0 truoc khi coi profile "promote".
"""
  )
