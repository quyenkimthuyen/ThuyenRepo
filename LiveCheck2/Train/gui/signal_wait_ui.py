"""Shared BUY/SELL gate wait UI — Bridge desk + Live Trade."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from mt5_bridge.protocol import normalize_model_ids


def wait_side_caption(block: dict | None) -> str:
  if not isinstance(block, dict) or not block:
    return "—"
  if block.get("ready"):
    return "sẵn sàng"
  n = block.get("waiting_n")
  total = block.get("total")
  if n is None:
    return "—"
  if total:
    return f"chờ {n}/{total}"
  return f"chờ {n}"


def render_signal_wait(*, file_status: dict, decision: dict) -> None:
  """Per Trade Model: how many BUY/SELL gates remain, current vs expect."""
  from gui.trade_model import (
    format_model_short,
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )

  roster_ids = normalize_model_ids(
    file_status.get("model_ids") or get_bridge_runtime_model_ids(),
    fallback=decision.get("model_id"),
  )
  per = file_status.get("per_model") if isinstance(file_status.get("per_model"), dict) else {}
  st.markdown("##### Chờ tín hiệu BUY / SELL")
  st.caption(
    "Bar đóng gần nhất. Mỗi dòng = một điều kiện của model: **hiện tại** vs **cần**. "
    "Hit lệnh khi mọi cổng phía đó đạt (và còn slot / không có lệnh mở)."
  )
  if not roster_ids:
    st.caption("Chưa có Trade Model trên roster.")
    return

  for mid in roster_ids:
    wait = (per.get(mid) or {}).get("signal_wait") if isinstance(per.get(mid), dict) else None
    if not wait and str(decision.get("model_id") or "") == str(mid):
      wait = decision.get("signal_wait")
    if not wait and len(roster_ids) == 1:
      wait = decision.get("signal_wait")
    model = get_model_by_id(mid)
    title = format_model_short(model, max_len=42) if model else mid[:28]
    if not wait:
      st.caption(f"**{title}** · chưa có bar quyết định — Start service Live.")
      continue
    buy = wait.get("buy") or {}
    sell = wait.get("sell") or {}
    bar = str(wait.get("bar_time") or "—")[:19]

    def _head(side: str, block: dict) -> str:
      if block.get("ready"):
        return f"{side} sẵn sàng"
      return f"{side} chờ {block.get('waiting_n', 0)}/{block.get('total', 0)}"

    with st.expander(
      f"{title} · {_head('BUY', buy)} · {_head('SELL', sell)} · {bar}",
      expanded=len(roster_ids) == 1,
    ):
      rows = []
      for block in (buy, sell):
        for g in block.get("gates") or []:
          cur = g.get("current")
          rows.append({
            "Phía": block.get("side") or g.get("side") or "",
            "Điều kiện": g.get("label"),
            "Hiện tại": "—" if cur is None else cur,
            "Cần": g.get("expect"),
            "Đạt": "đạt" if g.get("ok") else "chưa",
          })
      waiting_rows = [r for r in rows if r["Đạt"] == "chưa"]
      if waiting_rows:
        st.caption("Đang chờ:")
        st.dataframe(pd.DataFrame(waiting_rows), hide_index=True, use_container_width=True)
      else:
        st.success("Mọi cổng BUY/SELL trên bar này đã đạt.")
      if rows:
        with st.expander("Mọi điều kiện", expanded=False):
          st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
      names = (buy.get("waiting") or [])[:4]
      if names:
        st.caption("BUY còn: " + " · ".join(str(x) for x in names))
      s_names = (sell.get("waiting") or [])[:4]
      if s_names:
        st.caption("SELL còn: " + " · ".join(str(x) for x in names))
