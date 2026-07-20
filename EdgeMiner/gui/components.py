"""Shared Streamlit UI components."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def kpi_row(items: list[tuple[str, str, str | None]]):
  """Render KPI metrics row. items: (label, value, delta_or_hint)."""
  cols = st.columns(len(items))
  for col, (label, value, hint) in zip(cols, items):
    col.metric(label, value, hint if hint and hint.startswith(("+", "-")) else None)
    if hint and not hint.startswith(("+", "-")):
      col.caption(hint)


def constraint_checklist(constraints: dict, labels: dict[str, str] | None = None):
  from gui.glossary import CONSTRAINT_LABELS
  labels = labels or CONSTRAINT_LABELS
  for key, label in labels.items():
    ok = constraints.get(key, False)
    icon = "✅" if ok else "❌"
    st.markdown(f"{icon} **{label}**")


def status_banner(report: dict | None, kb: dict, data_meta: dict):
  if report:
    dr = report.get("data_range", {})
    cfg = report.get("config", {})
    st.caption(
      f"Data: **{dr.get('start', '?')} → {dr.get('end', '?')}** "
      f"({dr.get('bars', '?')} bars) · "
      f"KB: **{kb.get('genomes', 0)}** genomes, **{kb.get('rules', 0)}** rules · "
      f"Last fetch: {data_meta.get('fetched_at', 'n/a')[:10] if data_meta.get('fetched_at') else 'n/a'} · "
      f"Backtest KB: **{'ON' if cfg.get('use_learning_kb') else 'OFF'}**"
    )
  else:
    st.info("Chưa có báo cáo backtest. Chạy **Nghiên cứu → Backtest**.")


def warn_long_bias(pct_long: float):
  if pct_long >= 85:
    st.warning(
      f"⚠️ **LONG bias {pct_long:.0f}%** — strategy có thể chỉ hoạt động khi EUR/USD tăng. "
      "Kiểm tra kỹ trước khi live."
    )


def _profile_label(p: dict) -> str:
  from gui.glossary import format_memory_profile
  tf = p.get("trained_from") or "?"
  tt = p.get("trained_to") or "?"
  ep = p.get("epochs", 0)
  name = format_memory_profile(p.get("id")) if p.get("id") else p.get("name", "?")
  return f"{name} [học {tf} → {tt}, {ep} vòng]"


def list_kb_profiles_df(*, include_legacy: bool = False):
  from kb_profiles import list_era_profiles, list_profiles
  profiles = list_era_profiles(include_legacy=include_legacy) if not include_legacy else list_profiles()
  if not profiles:
    return pd.DataFrame()
  return pd.DataFrame(profiles)


def suggested_oos_range(profile_id: str) -> tuple[str, str]:
  """Gợi ý OOS ngay sau giai đoạn KB đã học."""
  from kb_profiles import get_profile
  p = get_profile(profile_id)
  if not p or not p.get("trained_to"):
    return "2024-01-01", "2024-12-31"
  start = pd.Timestamp(p["trained_to"]) + pd.Timedelta(days=1)
  end = start + pd.DateOffset(years=1) - pd.Timedelta(days=1)
  return str(start.date()), str(end.date())


def kb_profile_picker(
  key_prefix: str = "kb",
  allow_none: bool = False,
  show_meta: bool = True,
  oos_hint: str | None = None,
) -> str | None:
  """Chọn KB profile; tùy chọn lọc theo mốc OOS."""
  from kb_profiles import DEFAULT_PROFILE_ID, list_era_profiles, suggest_profiles_for_oos

  profiles = list_era_profiles()
  if oos_hint:
    suggested = {p["id"] for p in suggest_profiles_for_oos(oos_hint)}
    fit = [p for p in profiles if p["id"] in suggested]
    if fit:
      profiles = fit

  if not profiles:
    st.caption("Chưa có profile bộ nhớ — tạo ở **Bộ nhớ & học**.")
    return DEFAULT_PROFILE_ID if not allow_none else None

  options = {
    (_profile_label(p) if show_meta else f"{p['name']} ({p['id']})"): p["id"]
    for p in profiles
  }
  labels = list(options.keys())
  pick = st.selectbox(
    "Profile bộ nhớ (giai đoạn đã học)", labels, key=f"{key_prefix}_profile",
    help="Mỗi profile = kinh nghiệm học trên một khoảng thời gian.",
  )
  pid = options[pick]

  if show_meta:
    p = next(x for x in profiles if x["id"] == pid)
    st.caption(
      f"Học: **{p.get('trained_from', '?')} → {p.get('trained_to', '?')}** · "
      f"{p.get('epochs', 0)} vòng học · "
      f"{'✓ file OK' if p.get('exists') else '✗ thiếu file'}"
    )
  return pid


def kb_epoch_picker(
  key_prefix: str,
  profile_id: str | None,
  *,
  default_snapshot: int | str | None = None,
  show_table: bool = True,
) -> int | str | None:
  from gui.kb_epoch_ui import kb_epoch_picker as _picker
  return _picker(
    key_prefix, profile_id,
    default_snapshot=default_snapshot,
    show_table=show_table,
  )


def kb_profile_and_epoch_picker(
  key_prefix: str,
  show_meta: bool = True,
  oos_hint: str | None = None,
  default_snapshot: int | str | None = None,
) -> tuple[str | None, int | str | None]:
  """Chọn profile + epoch snapshot. Returns (profile_id, snapshot_epoch)."""
  pid = kb_profile_picker(key_prefix, show_meta=show_meta, oos_hint=oos_hint)
  snap = kb_epoch_picker(
    key_prefix, pid,
    default_snapshot=default_snapshot,
    show_table=bool(pid),
  ) if pid else None
  return pid, snap


def oos_period_inputs(
  key_prefix: str,
  profile_id: str | None = None,
  default_from: str = "",
  default_to: str = "",
) -> tuple[str, str]:
  """Nhập khoảng kiểm chứng; auto-fill từ profile nếu trống."""
  from gui.glossary import HELP
  sug_from, sug_to = suggested_oos_range(profile_id) if profile_id else ("2024-01-01", "2024-12-31")
  c1, c2, c3 = st.columns([2, 2, 1])
  with c1:
    oos_from = st.text_input(
      "Kiểm chứng từ (YYYY-MM-DD)", default_from or sug_from, key=f"{key_prefix}_oos_from",
      help=HELP["oos"],
    )
  with c2:
    oos_to = st.text_input(
      "Kiểm chứng đến (YYYY-MM-DD)", default_to or sug_to, key=f"{key_prefix}_oos_to",
      help=HELP["oos"],
    )
  with c3:
    st.write("")
    if st.button("Gợi ý", key=f"{key_prefix}_oos_suggest", help="Điền ngay sau giai đoạn đã học"):
      st.session_state[f"{key_prefix}_oos_from"] = sug_from
      st.session_state[f"{key_prefix}_oos_to"] = sug_to
      st.rerun()
  return oos_from.strip(), oos_to.strip()


def warn_no_costs():
  from gui.glossary import HELP
  st.caption(
    f"ℹ️ Phí mặc định: chênh lệch **1.0** / trượt giá **0.3** pip — "
    "chỉnh trong **Cài đặt**."
  )


ERA_PRESETS = [
  ("2022–2023 → test 2024", "era_2022_2023", "2022-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
  ("2022–2024 → test 2025–2026", "era_2022_2024", "2022-01-01", "2024-12-31", "2025-01-01", "2026-12-31"),
  ("2023–2024 → test 2025–2026", "era_2023_2024", "2023-01-01", "2024-12-31", "2025-01-01", "2026-12-31"),
  ("2024 (1 năm) → test 2025–2026", "era_2024", "2024-01-01", "2024-12-31", "2025-01-01", "2026-12-31"),
]


def kb_validation_banner(profile_id: str, oos_from: str | None):
  from kb_profiles import kb_valid_for_backtest
  if not profile_id:
    return
  ok, msg = kb_valid_for_backtest(profile_id, oos_from or "2022-01-01")
  if ok:
    st.success(f"KB: {msg}")
  else:
    st.error(f"KB: {msg}")


def warn_kb_leak(use_kb: bool):
  if use_kb:
    st.info(
      "ℹ️ **Bộ nhớ bật** — mỗi tuần chỉ dùng kinh nghiệm **trước** tuần đó "
      "(không nhìn trước tương lai)."
    )
