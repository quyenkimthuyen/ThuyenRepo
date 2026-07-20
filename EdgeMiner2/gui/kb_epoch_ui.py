"""UI helpers — chọn KB snapshot / epoch."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from kb_profiles import list_snapshots


def format_snapshot_label(s: dict, *, short: bool = False) -> str:
  """Nhãn vòng học kèm metrics khi huấn luyện."""
  if s.get("cumulative") is None:
    ep = "Mới nhất"
  else:
    ep = f"Vòng {int(s['cumulative']):03d}"
  wr = s.get("win_rate_pct")
  tr = s.get("total_r")
  if short or (wr is None and tr is None):
    return s.get("label") or ep
  wr_s = f"{wr}%" if wr is not None else "?"
  tr_s = f"{tr:+.1f}R" if tr is not None else "?"
  return f"{ep} · thắng {wr_s} · {tr_s} (khi học)"


def snapshot_options(profile_id: str | None) -> list[dict]:
  if not profile_id:
    return []
  return list_snapshots(profile_id, include_latest=True)


def snapshot_label_to_cumulative(profile_id: str, label: str) -> int | None:
  for s in snapshot_options(profile_id):
    if format_snapshot_label(s) == label or s.get("label") == label:
      return s.get("cumulative")
  return None


def cumulative_to_label(profile_id: str, cumulative: int | str | None) -> str | None:
  if cumulative is None or cumulative in ("latest", "Latest"):
    for s in snapshot_options(profile_id):
      if s.get("cumulative") is None:
        return format_snapshot_label(s)
    return None
  try:
    cum = int(cumulative)
  except (TypeError, ValueError):
    return None
  for s in snapshot_options(profile_id):
    if s.get("cumulative") == cum:
      return format_snapshot_label(s)
  return None


def sync_epoch_picker_state(key_prefix: str, profile_id: str, snapshot: int | str | None):
  label = cumulative_to_label(profile_id, snapshot)
  if label:
    st.session_state[f"{key_prefix}_kb_epoch"] = label


def kb_epoch_picker(
  key_prefix: str,
  profile_id: str | None,
  *,
  default_snapshot: int | str | None = None,
  show_table: bool = True,
) -> int | str | None:
  """
  Chọn snapshot epoch — luôn hiện khi profile có snapshot.
  Returns: None = latest; int = cumulative epoch.
  """
  snaps = snapshot_options(profile_id)
  if not profile_id or not snaps:
    st.caption("Chưa có vòng học — chạy **Bộ nhớ & học** để tạo vòng 1, 2, …")
    return None

  options = {format_snapshot_label(s): s.get("cumulative") for s in snaps}
  labels = list(options.keys())

  if default_snapshot is not None:
    sync_epoch_picker_state(key_prefix, profile_id, default_snapshot)

  if f"{key_prefix}_kb_epoch" not in st.session_state and labels:
    st.session_state[f"{key_prefix}_kb_epoch"] = labels[-1]

  pick = st.selectbox(
    "Vòng học",
    labels,
    key=f"{key_prefix}_kb_epoch",
    help="Mỗi vòng = bộ nhớ sau một lần huấn luyện. So sánh tại **Nghiên cứu → So vòng học**.",
  )

  if show_table and len(snaps) > 1:
    rows = []
    for s in snaps:
      rows.append({
        "Vòng": "Mới nhất" if s.get("cumulative") is None else f"Vòng {s['cumulative']:03d}",
        "Thắng % (khi học)": s.get("win_rate_pct"),
        "R (khi học)": s.get("total_r"),
      })
    st.caption("Kết quả khi huấn luyện — **không** thay cho kiểm chứng backtest.")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

  val = options[pick]
  return None if val is None else val


def kb_profile_and_epoch_picker(
  key_prefix: str,
  show_meta: bool = True,
  oos_hint: str | None = None,
  default_snapshot: int | str | None = None,
) -> tuple[str | None, int | str | None]:
  from gui.components import kb_profile_picker
  pid = kb_profile_picker(key_prefix, show_meta=show_meta, oos_hint=oos_hint)
  snap = kb_epoch_picker(
    key_prefix, pid,
    default_snapshot=default_snapshot,
    show_table=bool(pid),
  ) if pid else None
  return pid, snap
