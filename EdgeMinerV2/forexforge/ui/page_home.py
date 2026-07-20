"""Home / huong dan dung — trang mac dinh."""
from __future__ import annotations

import streamlit as st

from forexforge import services as svc
from forexforge.store import Store


def render() -> None:
  st.header("ForexForge v2 — Bat dau o day")
  st.markdown(
    """
### Ban cu vs ban moi (ngan gon)

| | **Ban cu (EdgeMiner1)** | **Ban moi (v2)** |
|--|-------------------------|------------------|
| Dung nhu the nao | Bam nut, cho ket qua tren man hinh | Bam nut → job chay **nen** → xem o Jobs / Report |
| Khi hoc nhieu epoch | App de treo | UI **khong treo** |
| KB sai thoi gian (leakage) | Canh bao | **Chan cung** — khong cho chay |
| Luu ket qua | File JSON lon | SQLite + so sanh Report |
| Thuat toan trade | Giong nhau | **Giong nhau** (WF 3 thang → 1 tuan, cost, KB) |

**Ket luan:** v2 tot hon ve on dinh / an toan research. UX hien tai don gian hon ban cu — lam dung **6 buoc ben duoi** la du.
"""
  )

  meta = svc.load_data_meta()
  store = Store()
  reports = store.list_reports(5)
  c1, c2, c3 = st.columns(3)
  c1.metric("Data bars", meta.get("bars", "chua co"))
  c2.metric("Reports da luu", len(store.list_reports(100)))
  c3.metric("Jobs gan day", len(store.list_runs(20)))

  st.divider()
  st.subheader("Lam theo thu tu (copy tu ban cu)")

  st.markdown(
    """
**Buoc 1 — Lay data**  
Vao menu **1. Data Hub** → bam **Refresh Data**.

**Buoc 2 — Do baseline (QUAN TRONG)**  
Vao **2. Backtest Lab**  
- De **KB OFF** (khong tick KB ON)  
- OOS from `2024-01-01` → to `2024-12-31`  
- Spread `1.0` / Slippage `0.3`  
- Tick **Chay nen** → bam **Run backtest**  
- Doi xong: vao **4. Report Compare** xem ket qua

**Buoc 3 — Hoc KB theo giai doan**  
Vao **3. KB Era Hub**  
- Profile vd `era_2022_2023`  
- Hoc tu `2022-01-01` den `2023-12-31`, epochs `3`  
- Bam **Start learning** (nen)

**Buoc 4 — Test OOS voi KB**  
Van o **KB Era Hub**  
- OOS `2024-01-01` → `2024-12-31`  
- Neu xanh (OK) → **Run OOS KB ON**

**Buoc 5 — So sanh**  
**4. Report Compare** → chon 2 report (KB OFF vs KB ON) → xem WR / Total R / equity

**Buoc 6 — Paper**  
**6. Paper Monitor** → **Paper tick** de xem tin hieu tuan nay (chua len live)
"""
  )

  st.info(
    "Meo: moi lan bam Run/Start learning se tao **job_id**. "
    "Neu chua thay ket qua, bam Refresh job status hoac xem bang Jobs o Data Hub."
  )

  if reports:
    st.subheader("Report moi nhat")
    st.dataframe(reports, width="stretch")
  else:
    st.warning("Chua co report — hay chay Buoc 2 (Backtest KB OFF) truoc.")
