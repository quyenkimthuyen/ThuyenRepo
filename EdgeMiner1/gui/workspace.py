"""Bridge nội bộ: Trade Profile ↔ report cache (giữ tên workspace cho tương thích code)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

from kb_profiles import DEFAULT_PROFILE_ID, get_profile
from run_backtest import REPORT_DIR

WORKSPACE_PATH = REPORT_DIR / "active_workspace.json"
WORKSPACES_DIR = REPORT_DIR / "workspaces"

PICKER_PREFIXES = ("hub_learn",)  # widget KB hub tab Học


def workspace_id(ws: dict) -> str:
  pid = re.sub(r"[^a-zA-Z0-9_-]+", "_", (ws.get("kb_profile") or "default"))
  oos_f = (ws.get("oos_from") or "auto")[:10].replace("-", "")
  oos_t = (ws.get("oos_to") or "auto")[:10].replace("-", "")
  tm = ws.get("train_months", 6)
  return f"{pid}__{oos_f}_{oos_t}__t{tm}"


def workspace_report_path(ws: dict | None = None) -> Path:
  ws = ws or get_active_workspace()
  WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
  return WORKSPACES_DIR / f"{workspace_id(ws)}.json"


def format_workspace_label(ws: dict) -> str:
  from gui.glossary import build_trade_profile_label
  return build_trade_profile_label({
    "train_months": ws.get("train_months", 6),
    "use_kb": ws.get("use_learning", True),
    "kb_profile": ws.get("kb_profile"),
    "kb_snapshot": ws.get("kb_snapshot"),
    "oos_from": ws.get("oos_from"),
    "oos_to": ws.get("oos_to"),
  })


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data: dict):
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def get_active_workspace() -> dict:
  from gui.trade_profile import get_active_trade_profile, trade_profile_to_workspace
  tp = get_active_trade_profile()
  ws = trade_profile_to_workspace(tp)
  st.session_state["active_workspace"] = ws
  return ws


def set_active_workspace(**fields) -> dict:
  from gui.trade_profile import (
    get_active_trade_profile, set_active_trade_profile, workspace_fields_to_trade_profile,
  )
  tp_fields = workspace_fields_to_trade_profile(**fields)
  if "label" in fields and fields["label"] is not None:
    tp_fields["label"] = fields["label"]
  set_active_trade_profile(**tp_fields)
  ws = get_active_workspace()
  save_workspace_file(ws)
  sync_workspace_pickers(ws)
  return ws


def save_workspace_file(ws: dict):
  _write_json(WORKSPACE_PATH, ws)


def load_workspace_file() -> dict | None:
  return _read_json(WORKSPACE_PATH)


def set_active_from_preset(
  label: str,
  kb_profile: str,
  learn_from: str,
  learn_until: str,
  oos_from: str,
  oos_to: str,
) -> dict:
  return set_active_workspace(
    label=label,
    kb_profile=kb_profile,
    learn_from=learn_from,
    learn_until=learn_until,
    oos_from=oos_from,
    oos_to=oos_to,
    use_learning=True,
    kb_snapshot=None,
  )


def sync_workspace_from_backtest(report: dict) -> dict:
  cfg = report.get("config") or {}
  fields = {
    "kb_profile": cfg.get("kb_profile"),
    "kb_snapshot": cfg.get("kb_snapshot"),
    "oos_from": cfg.get("oos_from"),
    "oos_to": cfg.get("oos_to"),
    "use_learning": bool(cfg.get("use_learning_kb")),
    "train_months": cfg.get("train_months"),
    "spread_pips": cfg.get("spread_pips"),
    "slippage_pips": cfg.get("slippage_pips"),
    "backtest_total_r": (report.get("overall_oos") or {}).get("total_r"),
  }
  if cfg.get("kb_profile"):
    fields["label"] = format_workspace_label({
      "kb_profile": cfg.get("kb_profile"),
      "oos_from": cfg.get("oos_from"),
      "oos_to": cfg.get("oos_to"),
      "train_months": cfg.get("train_months", 6),
    })
  return set_active_workspace(**{k: v for k, v in fields.items() if v is not None})


def sync_workspace_from_learning(report: dict) -> dict:
  return set_active_workspace(
    kb_profile=report.get("kb_profile"),
    learn_from=report.get("trained_from"),
    learn_until=report.get("trained_to"),
    label=format_workspace_label({
      "kb_profile": report.get("kb_profile"),
      "oos_from": get_active_workspace().get("oos_from"),
      "oos_to": get_active_workspace().get("oos_to"),
      "train_months": get_active_workspace().get("train_months", 6),
    }),
  )


def save_workspace_report(report: dict, ws: dict | None = None):
  ws = ws or get_active_workspace()
  payload = dict(report)
  cfg = dict(payload.get("config") or {})
  if ws.get("trade_profile_id"):
    cfg["trade_profile_id"] = ws["trade_profile_id"]
  payload["config"] = cfg
  _write_json(workspace_report_path(ws), payload)


def load_workspace_report(ws: dict | None = None) -> dict | None:
  return _read_json(workspace_report_path(ws))


def profile_mismatch_details(report: dict, ws: dict | None = None) -> list[str]:
  """Liệt kê field lệch giữa báo cáo và Trade Profile."""
  ws = ws or get_active_workspace()
  cfg = report.get("config") or {}
  diffs: list[str] = []

  def _add(label: str, a, b):
    if a is not None and b is not None and a != b:
      diffs.append(f"**{label}:** báo cáo `{a}` · profile `{b}`")

  _add("Cửa sổ học (tháng)", cfg.get("train_months"), ws.get("train_months"))
  _add("Profile bộ nhớ", cfg.get("kb_profile"), ws.get("kb_profile"))
  ep_cfg = cfg.get("kb_snapshot")
  ep_ws = ws.get("kb_snapshot")
  if ep_ws is not None and ep_cfg != ep_ws:
    from gui.glossary import format_epoch
    diffs.append(
      f"**Vòng học:** báo cáo `{format_epoch(ep_cfg)}` · profile `{format_epoch(ep_ws)}`"
    )
  _add("Kiểm chứng từ", cfg.get("oos_from"), ws.get("oos_from"))
  _add("Kiểm chứng đến", cfg.get("oos_to"), ws.get("oos_to"))
  _add("Chênh lệch (pip)", cfg.get("spread_pips"), ws.get("spread_pips"))
  _add("Trượt giá (pip)", cfg.get("slippage_pips"), ws.get("slippage_pips"))
  kb_on = bool(cfg.get("use_learning_kb"))
  prof_kb = bool(ws.get("use_learning"))
  if kb_on != prof_kb:
    diffs.append(
      f"**Bộ nhớ:** báo cáo `{'bật' if kb_on else 'tắt'}` · profile `{'bật' if prof_kb else 'tắt'}`"
    )
  return diffs


def report_matches_profile(report: dict, ws: dict | None = None) -> bool:
  """Backtest có khớp Trade Profile đang active không."""
  return report_matches_workspace(report, ws)


def report_matches_workspace(report: dict, ws: dict | None = None) -> bool:
  ws = ws or get_active_workspace()
  cfg = report.get("config") or {}
  if ws.get("kb_profile") and cfg.get("kb_profile") != ws.get("kb_profile"):
    return False
  if ws.get("oos_from") and cfg.get("oos_from") != ws.get("oos_from"):
    return False
  if ws.get("oos_to") and cfg.get("oos_to") != ws.get("oos_to"):
    return False
  if ws.get("train_months") and cfg.get("train_months") != ws.get("train_months"):
    return False
  if ws.get("kb_snapshot") != cfg.get("kb_snapshot"):
    # None và missing đều coi là latest — chỉ so khi workspace có epoch cụ thể
    if ws.get("kb_snapshot") is not None:
      return False
  return True


def load_report_for_workspace() -> dict | None:
  """Báo cáo khớp profile active — không trả về backtest cũ của profile khác."""
  ws_report = load_workspace_report()
  if ws_report and report_matches_workspace(ws_report):
    return ws_report
  main = _read_json(REPORT_DIR / "backtest_report.json")
  if main and report_matches_workspace(main):
    return main
  return None


def ensure_workspace_loaded():
  from gui.trade_profile import ensure_trade_profiles_loaded
  ensure_trade_profiles_loaded()
  ws = get_active_workspace()
  if not WORKSPACE_PATH.exists():
    save_workspace_file(ws)
  if not st.session_state.get("_workspace_pickers_synced"):
    sync_workspace_pickers(ws)
    st.session_state["_workspace_pickers_synced"] = True


def sync_workspace_pickers(ws: dict | None = None):
  """Đồng bộ widget KB hub (tab Học) từ Trade Profile."""
  from kb_profiles import get_profile

  ws = ws or get_active_workspace()
  pid = ws.get("kb_profile") or DEFAULT_PROFILE_ID
  p = get_profile(pid)

  if p:
    st.session_state["hub_learn_id"] = pid
    st.session_state["hub_learn_name"] = p.get("name") or pid
    if p.get("trained_from"):
      st.session_state["hub_learn_from"] = p["trained_from"]
    if p.get("trained_to"):
      st.session_state["hub_learn_until"] = p["trained_to"]


def render_workspace_banner(container=None):
  from gui.trade_profile import render_profile_card
  render_profile_card(container=container or st)


def render_sidebar_trade_profiles():
  from gui.trade_profile import render_sidebar_trade_profiles
  render_sidebar_trade_profiles()


# Aliases
ensure_profiles_loaded = ensure_workspace_loaded
render_sidebar_profiles = render_sidebar_trade_profiles
render_sidebar_workspace = render_sidebar_trade_profiles
