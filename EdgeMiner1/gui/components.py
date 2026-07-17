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
  default_labels = {
    "profitable": "Profitable (1Y)",
    "win_rate_above_60": "Win Rate > 60% (1Y)",
    "rr_above_2": "RR > 2 (1Y)",
    "trades_per_week_near_2": "~2 lệnh/tuần",
  }
  labels = labels or default_labels
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
    st.info("Chưa có báo cáo backtest. Chạy Backtest Lab hoặc Command Center.")


def warn_long_bias(pct_long: float):
  if pct_long >= 85:
    st.warning(
      f"⚠️ **LONG bias {pct_long:.0f}%** — strategy có thể chỉ hoạt động khi EUR/USD tăng. "
      "Kiểm tra kỹ trước khi live."
    )


def _profile_label(p: dict) -> str:
  tf = p.get("trained_from") or "?"
  tt = p.get("trained_to") or "?"
  ep = p.get("epochs", 0)
  return f"{p['name']} [{tf} → {tt}, {ep} ep]"


def list_kb_profiles_df():
  from kb_profiles import list_profiles
  profiles = list_profiles()
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
  from kb_profiles import DEFAULT_PROFILE_ID, list_profiles, suggest_profiles_for_oos

  profiles = [p for p in list_profiles() if p.get("exists")]
  if oos_hint:
    suggested = {p["id"] for p in suggest_profiles_for_oos(oos_hint)}
    fit = [p for p in profiles if p["id"] in suggested]
    if fit:
      profiles = fit

  if not profiles:
    st.caption("Chưa có KB profile — tạo ở **KB & Giai đoạn** hoặc Learning Center.")
    return DEFAULT_PROFILE_ID if not allow_none else None

  options = {
    (_profile_label(p) if show_meta else f"{p['name']} ({p['id']})"): p["id"]
    for p in profiles
  }
  labels = list(options.keys())
  pick = st.selectbox("KB Profile (giai đoạn)", labels, key=f"{key_prefix}_profile")
  pid = options[pick]

  if show_meta:
    p = next(x for x in profiles if x["id"] == pid)
    st.caption(
      f"Học: **{p.get('trained_from', '?')} → {p.get('trained_to', '?')}** · "
      f"{p.get('epochs', 0)} epoch · "
      f"{'✓ file OK' if p.get('exists') else '✗ thiếu file'}"
    )
  return pid


def kb_epoch_picker(key_prefix: str, profile_id: str | None) -> int | str | None:
  """
  Chọn snapshot epoch của profile.
  Returns: None/'latest' = file chính; int = cumulative epoch snapshot.
  """
  from kb_profiles import LATEST_SNAPSHOT, list_snapshots

  if not profile_id:
    return None
  snaps = list_snapshots(profile_id)
  if len(snaps) <= 1:
    return None
  options = {s["label"]: s.get("cumulative") for s in snaps}
  labels = list(options.keys())
  pick = st.selectbox(
    "KB Epoch (snapshot)",
    labels,
    key=f"{key_prefix}_kb_epoch",
    help="Latest = KB sau lần học gần nhất. Epoch N = trạng thái KB ngay sau epoch N.",
  )
  val = options[pick]
  return None if val is None else val


def kb_profile_and_epoch_picker(
  key_prefix: str,
  show_meta: bool = True,
  oos_hint: str | None = None,
) -> tuple[str | None, int | str | None]:
  """Chọn profile + epoch snapshot. Returns (profile_id, snapshot_epoch)."""
  pid = kb_profile_picker(key_prefix, show_meta=show_meta, oos_hint=oos_hint)
  snap = kb_epoch_picker(key_prefix, pid) if pid else None
  return pid, snap


def oos_period_inputs(
  key_prefix: str,
  profile_id: str | None = None,
  default_from: str = "",
  default_to: str = "",
) -> tuple[str, str]:
  """Nhập khoảng OOS; auto-fill từ profile nếu trống."""
  sug_from, sug_to = suggested_oos_range(profile_id) if profile_id else ("2024-01-01", "2024-12-31")
  c1, c2, c3 = st.columns([2, 2, 1])
  with c1:
    oos_from = st.text_input(
      "OOS từ (YYYY-MM-DD)", default_from or sug_from, key=f"{key_prefix}_oos_from",
      help="Chỉ test walk-forward từ mốc này",
    )
  with c2:
    oos_to = st.text_input(
      "OOS đến (YYYY-MM-DD)", default_to or sug_to, key=f"{key_prefix}_oos_to",
    )
  with c3:
    st.write("")
    if st.button("Gợi ý", key=f"{key_prefix}_oos_suggest", help="Điền OOS ngay sau giai đoạn KB"):
      st.session_state[f"{key_prefix}_oos_from"] = sug_from
      st.session_state[f"{key_prefix}_oos_to"] = sug_to
      st.rerun()
  return oos_from.strip(), oos_to.strip()


def era_workflow_panel(key_prefix: str, *, in_sidebar: bool = False) -> dict:
  """
  Panel chọn KB + epoch + mốc OOS cho backtest.
  Returns: {use_kb, kb_profile, kb_snapshot, oos_from, oos_to}
  """
  container = st.sidebar if in_sidebar else st
  with container:
    use_kb = st.toggle("Dùng Knowledge Base", value=True, key=f"{key_prefix}_use_kb")
    kb_profile, kb_snapshot, oos_from, oos_to = None, None, "", ""
    if use_kb:
      kb_profile, kb_snapshot = kb_profile_and_epoch_picker(key_prefix, show_meta=True)
      st.markdown("**Giai đoạn backtest (OOS)**")
      oos_from, oos_to = oos_period_inputs(key_prefix, kb_profile)
      if kb_profile:
        kb_validation_banner(kb_profile, oos_from or "2022-01-01")
      warn_kb_leak(True)
    return {
      "use_kb": use_kb,
      "kb_profile": kb_profile,
      "kb_snapshot": kb_snapshot,
      "oos_from": oos_from or None,
      "oos_to": oos_to or None,
    }


ERA_PRESETS = [
  ("2022–2023 → test 2024", "era_2022_2023", "2022-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
  ("2022–2024 → test 2025", "era_2022_2024", "2022-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
  ("2023–2024 → test 2025", "era_2023_2024", "2023-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
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
      "ℹ️ **KB ON** — chọn profile giai đoạn + mốc OOS. "
      "Mỗi tuần chỉ dùng kinh nghiệm KB **trước** tuần đó (causal as_of)."
    )


def warn_no_costs():
  st.caption(
    "ℹ️ Chi phí giao dịch: chỉnh **Spread/Slippage** trong Backtest Lab (mặc định 1.0 / 0.3 pip)."
  )
