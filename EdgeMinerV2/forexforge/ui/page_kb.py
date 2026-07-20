"""3. KB Era Hub"""
from __future__ import annotations

import streamlit as st

from forexforge import services as svc
from forexforge.guardrails import can_promote_profile, check_epoch_limit
from forexforge.store import Store
from forexforge.ui.helpers import job_progress_panel, leakage_banner, metric_row


def render() -> None:
  st.header("3. KB Era Hub")
  st.success("Buoc 3/6 — Hoc KB tren giai doan TRUOC khi test OOS.")
  st.caption("Vd: hoc 2022-2023, roi backtest OOS 2024. Giong trang KB & Giai doan ban cu.")

  profiles = svc.profiles()
  st.dataframe(profiles, width="stretch")

  st.subheader("Chay learning cho profile")
  st.markdown(
    """
**Cach chay `era_2024_2025` (vi du):**
1. Profile id = `era_2024_2025`
2. Hoc tu `2024-01-01` → den `2025-12-31`
3. Epochs = `3` (lan dau)
4. Bam **Create profile** (neu chua co) roi **Start learning**
5. Doi job `done` (Data Hub → Jobs). Mat kha lau.
6. Sau do OOS: `2026-01-01` → `2026-07-17` → **Run OOS KB ON**
"""
  )
  c1, c2 = st.columns(2)
  pid = c1.text_input("Profile id", "era_2022_2023")
  pname = c2.text_input("Ten hien thi", pid)
  d1, d2, d3 = st.columns(3)
  from_date = d1.text_input("Hoc tu", "2022-01-01")
  until = d2.text_input("Hoc den", "2023-12-31")
  epochs = d3.number_input("Epochs", 1, 8, 3)

  limit = check_epoch_limit(pid, additional=int(epochs))
  if not limit.ok:
    st.warning(limit.reasons[0])

  if st.button("Create profile"):
    svc.create_profile(pid, pname)
    st.success(f"Created {pid}")
    st.rerun()

  bg = st.checkbox("Hoc nen (khuyen nghi)", value=True)
  if st.button("Start learning", type="primary", disabled=not limit.ok):
    try:
      if bg:
        jid = svc.submit_learn_job(
          kb_profile=pid,
          kb_name=pname,
          from_date=from_date,
          until_date=until,
          epochs=int(epochs),
        )
        st.session_state["learn_job"] = jid
        st.success(f"Queued learn job={jid}. Hoc mat nhieu phut — UI van dung duoc.")
      else:
        with st.spinner("Learning..."):
          report = svc.run_learn_sync(
            kb_profile=pid,
            kb_name=pname,
            from_date=from_date,
            until_date=until,
            epochs=int(epochs),
          )
        st.session_state["learn_report"] = report
        st.success("Learning done")
    except Exception as exc:
      st.error(str(exc))

  job_progress_panel(Store(), st.session_state.get("learn_job"))
  if st.session_state.get("learn_report"):
    st.subheader("Epoch history")
    st.dataframe(st.session_state["learn_report"].epoch_history, width="stretch")

  st.subheader("OOS backtest voi KB (buoc 4a)")
  oos_from = st.text_input("OOS from", "2024-01-01", key="kb_oos_from")
  oos_to = st.text_input("OOS to", "2024-12-31", key="kb_oos_to")
  check = svc.leakage_status(pid, oos_from)
  leakage_banner(check.ok, check.message)

  if st.button("Run OOS KB ON", disabled=not check.ok):
    try:
      jid = svc.submit_backtest_job(
        use_kb=True,
        kb_profile=pid,
        oos_from=oos_from,
        oos_to=oos_to,
        label=f"oos_{pid}",
      )
      st.session_state["bt_job"] = jid
      st.success(f"Queued {jid} — sau do so sanh o Report Compare")
    except Exception as exc:
      st.error(str(exc))

  st.subheader("Promote guardrail")
  verdict = can_promote_profile(pid, oos_from=oos_from, holdout_report=None, require_holdout=True)
  if verdict.ok:
    st.success("Co the promote (neu da co hold-out).")
  else:
    for r in verdict.reasons:
      st.warning(r)

  snaps = svc.snapshots(pid)
  if snaps:
    st.subheader("Snapshots")
    st.dataframe(snaps, width="stretch")

  if st.button("Xoa profile", type="secondary"):
    if svc.delete_profile(pid):
      st.success("Deleted")
      st.rerun()

  st.caption("Tiep theo: **4. Report Compare** de so KB OFF vs KB ON.")
