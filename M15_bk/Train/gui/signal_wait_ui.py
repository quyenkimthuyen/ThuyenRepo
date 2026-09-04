"""Shared BUY/SELL gate wait UI — Bridge desk + Live Trade."""
from __future__ import annotations

from html import escape

import streamlit as st

from mt5_bridge.protocol import normalize_model_ids

_SW_CSS = """
<style>
.sw-wrap { font-family: "IBM Plex Sans", "Segoe UI", sans-serif; color: #1a1d23; }
.sw-head { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center;
  margin: 0.15rem 0 0.45rem 0; }
.sw-title { font-size: 0.88rem; font-weight: 650; margin: 0 0.35rem 0 0; color: #1f2937; }
.sw-chip { font-size: 0.75rem; font-weight: 650; letter-spacing: 0.02em;
  padding: 0.2rem 0.5rem; border-radius: 999px; border: 1px solid #e5e7eb;
  background: #f8fafc; color: #374151; }
.sw-chip.buy { border-color: #99f6e4; background: #ccfbf1; color: #0f766e; }
.sw-chip.sell { border-color: #fecaca; background: #fee2e2; color: #b91c1c; }
.sw-chip.ok { border-color: #a7f3d0; background: #ecfdf5; color: #047857; }
.sw-chip.wait { border-color: #fde68a; background: #fffbeb; color: #92400e; }
.sw-chip.muted { color: #6b7280; font-weight: 500; }
.sw-scroll { overflow-x: auto; margin: 0 0 0.55rem 0; }
.sw-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; margin: 0; }
.sw-table th { text-align: left; font-size: 0.65rem; letter-spacing: 0.06em; text-transform: uppercase;
  color: #6b7280; font-weight: 700; padding: 0.35rem 0.45rem; border-bottom: 1px solid #e5e7eb;
  background: #f8fafc; }
.sw-table td { padding: 0.4rem 0.45rem; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
.sw-table tr.row-buy { background: #f0fdfa; }
.sw-table tr.row-sell { background: #fef2f2; }
.sw-table tr.row-buy td:first-child { box-shadow: inset 3px 0 0 #0d9488; }
.sw-table tr.row-sell td:first-child { box-shadow: inset 3px 0 0 #dc2626; }
.sw-ok { color: #047857; font-weight: 700; }
.sw-wait { color: #b45309; font-weight: 650; }
.sw-dir.buy { color: #0f766e; font-weight: 700; }
.sw-dir.sell { color: #b91c1c; font-weight: 700; }
</style>
"""


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


def _chip(label: str, *, kind: str) -> str:
  return f'<span class="sw-chip {kind}">{escape(label)}</span>'


def _side_chip(side: str, block: dict) -> str:
  ready = bool(block.get("ready"))
  if ready:
    kind = "buy" if side == "BUY" else "sell"
    label = f"{side} sẵn sàng"
  else:
    kind = "wait"
    label = f"{side} {wait_side_caption(block)}"
  return _chip(label, kind=kind)


def _fmt_cell(val) -> str:
  if val is None or val == "":
    return "—"
  return str(val)


def _gates_table_html(rows: list[dict]) -> str:
  if not rows:
    return ""
  trs = []
  for r in rows:
    side = str(r.get("Phía") or "").upper()
    row_cls = "row-buy" if side == "BUY" else ("row-sell" if side == "SELL" else "")
    ok = r.get("Đạt") == "đạt"
    ok_html = '<span class="sw-ok">đạt</span>' if ok else '<span class="sw-wait">chưa</span>'
    dcls = "buy" if side == "BUY" else "sell"
    side_html = f'<span class="sw-dir {dcls}">{escape(side or "—")}</span>'
    trs.append(
      f'<tr class="{row_cls}">'
      f"<td>{side_html}</td>"
      f"<td>{escape(_fmt_cell(r.get('Điều kiện')))}</td>"
      f"<td>{escape(_fmt_cell(r.get('Hiện tại')))}</td>"
      f"<td>{escape(_fmt_cell(r.get('Cần')))}</td>"
      f"<td>{ok_html}</td>"
      "</tr>"
    )
  return (
    '<div class="sw-scroll"><table class="sw-table">'
    "<thead><tr><th>Phía</th><th>Điều kiện</th><th>Hiện tại</th><th>Cần</th><th>Đạt</th></tr></thead>"
    f"<tbody>{''.join(trs)}</tbody></table></div>"
  )


def render_signal_wait(*, file_status: dict, decision: dict) -> None:
  """Per Trade Model: how many BUY/SELL gates remain, current vs expect."""
  from gui.trade_model import (
    format_model_short,
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )

  st.markdown(_SW_CSS, unsafe_allow_html=True)
  roster_ids = normalize_model_ids(
    file_status.get("model_ids") or get_bridge_runtime_model_ids(),
    fallback=decision.get("model_id"),
  )
  per = file_status.get("per_model") if isinstance(file_status.get("per_model"), dict) else {}
  st.markdown("##### Chờ tín hiệu BUY / SELL")
  st.caption(
    "Bar đóng gần nhất. Mở từng model khi cần xem **hiện tại** vs **cần**. "
    "Hit lệnh khi mọi cổng phía đó đạt (và còn slot / không có lệnh mở)."
  )
  if not roster_ids:
    st.caption("Chưa có Trade Model trên roster.")
    return

  def _head(side: str, block: dict) -> str:
    if block.get("ready"):
      return f"{side} sẵn sàng"
    return f"{side} {wait_side_caption(block)}"

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

    with st.expander(
      f"{title} · {_head('BUY', buy)} · {_head('SELL', sell)} · {bar}",
      expanded=False,
      key=f"sw_wait_{mid}",
    ):
      st.markdown(
        f'<div class="sw-wrap"><div class="sw-head">'
        f'{_side_chip("BUY", buy)}{_side_chip("SELL", sell)}'
        f'{_chip(bar, kind="muted")}'
        f"</div></div>",
        unsafe_allow_html=True,
      )
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
        st.markdown(_gates_table_html(waiting_rows), unsafe_allow_html=True)
      else:
        st.success("Mọi cổng BUY/SELL trên bar này đã đạt.")
      if rows:
        with st.expander("Mọi điều kiện", expanded=False, key=f"sw_all_{mid}"):
          st.markdown(_gates_table_html(rows), unsafe_allow_html=True)
      names = (buy.get("waiting") or [])[:4]
      if names:
        st.caption("BUY còn: " + " · ".join(str(x) for x in names))
      s_names = (sell.get("waiting") or [])[:4]
      if s_names:
        st.caption("SELL còn: " + " · ".join(str(x) for x in s_names))
