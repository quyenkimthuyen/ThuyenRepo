"""Bridge nội bộ: Trade Model ↔ report cache."""
from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

from kb_profiles import DEFAULT_PROFILE_ID, get_profile
from run_backtest import REPORT_DIR

WORKSPACE_PATH = REPORT_DIR / "active_workspace.json"
WORKSPACES_DIR = REPORT_DIR / "workspaces"

PICKER_PREFIXES = ("hub_learn",)


def workspace_id(ws: dict) -> str:
  pid = re.sub(r"[^a-zA-Z0-9_-]+", "_", (ws.get("kb_profile") or "default"))
  oos_f = (ws.get("oos_from") or "auto")[:10].replace("-", "")
  oos_t = (ws.get("oos_to") or "auto")[:10].replace("-", "")
  tm = ws.get("train_weeks", 6)
  mid = ws.get("trade_model_id") or "nomodel"
  return f"{mid}__{pid}__{oos_f}_{oos_t}__t{tm}"


def workspace_report_path(ws: dict | None = None) -> Path:
  ws = ws or get_active_workspace()
  from gui.trade_model import get_active_trade_model, model_report_path
  m = get_active_trade_model()
  if m and m.get("id"):
    return model_report_path(m["id"])
  WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
  return WORKSPACES_DIR / f"{workspace_id(ws)}.json"


def format_workspace_label(ws: dict) -> str:
  from gui.glossary import build_trade_profile_label
  return build_trade_profile_label({
    "train_weeks": ws.get("train_weeks", 6),
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
  from gui.trade_model import get_active_trade_model, trade_model_to_workspace
  m = get_active_trade_model()
  ws = trade_model_to_workspace(m)
  st.session_state["active_workspace"] = ws
  return ws


def set_active_workspace(**fields) -> dict:
  from gui.trade_model import get_active_trade_model, set_active_trade_model
  m = get_active_trade_model()
  if m:
    updated = {**m, **{k: v for k, v in fields.items() if v is not None}}
    from gui.trade_model import load_models_store, save_models_store
    store = load_models_store()
    for i, x in enumerate(store["models"]):
      if x.get("id") == m["id"]:
        store["models"][i] = updated
        break
    save_models_store(store)
    st.session_state["active_trade_model"] = updated
  ws = get_active_workspace()
  save_workspace_file(ws)
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
  from gui.trade_model import get_active_trade_model, save_model_report
  m = get_active_trade_model()
  if m:
    save_model_report(m["id"], report)
  return get_active_workspace()


def sync_workspace_from_learning(report: dict) -> dict:
  return get_active_workspace()


def save_workspace_report(report: dict, ws: dict | None = None):
  from gui.trade_model import get_active_trade_model, save_model_report
  m = get_active_trade_model()
  if m:
    save_model_report(m["id"], report)
  else:
    ws = ws or get_active_workspace()
    payload = dict(report)
    cfg = dict(payload.get("config") or {})
    if ws.get("trade_model_id"):
      cfg["trade_model_id"] = ws["trade_model_id"]
    payload["config"] = cfg
    _write_json(workspace_report_path(ws), payload)


def load_workspace_report(ws: dict | None = None) -> dict | None:
  return _read_json(workspace_report_path(ws))


def profile_mismatch_details(report: dict, ws: dict | None = None) -> list[str]:
  ws = ws or get_active_workspace()
  cfg = report.get("config") or {}
  diffs: list[str] = []

  def _add(label: str, a, b):
    if a is not None and b is not None and a != b:
      diffs.append(f"**{label}:** báo cáo `{a}` · model `{b}`")

  _add("Cửa sổ học (tuần)", cfg.get("train_weeks"), ws.get("train_weeks"))
  _add("Profile bộ nhớ", cfg.get("kb_profile"), ws.get("kb_profile"))
  ep_cfg = cfg.get("kb_snapshot")
  ep_ws = ws.get("kb_snapshot")
  if ep_ws is not None and ep_cfg != ep_ws:
    from gui.glossary import format_epoch
    diffs.append(
      f"**Vòng học:** báo cáo `{format_epoch(ep_cfg)}` · model `{format_epoch(ep_ws)}`"
    )
  _add("Kiểm chứng từ", cfg.get("oos_from"), ws.get("oos_from"))
  _add("Kiểm chứng đến", cfg.get("oos_to"), ws.get("oos_to"))
  return diffs


def report_matches_profile(report: dict, ws: dict | None = None) -> bool:
  return report_matches_workspace(report, ws)


def report_matches_workspace(report: dict, ws: dict | None = None) -> bool:
  """True nếu config báo cáo khớp workspace (không gọi report_matches_model — tránh vòng lặp)."""
  ws = ws or get_active_workspace()
  cfg = report.get("config") or {}
  if cfg.get("trade_model_id") and ws.get("trade_model_id"):
    return cfg["trade_model_id"] == ws["trade_model_id"]
  return not profile_mismatch_details(report, ws)


def load_report_for_workspace() -> dict | None:
  from gui.trade_model import get_active_trade_model, load_model_report
  m = get_active_trade_model()
  if m:
    rep = load_model_report(m["id"])
    if rep:
      return rep
  ws_report = load_workspace_report()
  if ws_report and report_matches_workspace(ws_report):
    return ws_report
  main = _read_json(REPORT_DIR / "backtest_report.json")
  if main and report_matches_workspace(main):
    return main
  return None


def ensure_workspace_loaded():
  from gui.app_settings import ensure_settings_loaded
  from gui.trade_model import ensure_trade_models_loaded
  ensure_settings_loaded()
  ensure_trade_models_loaded()
  ws = get_active_workspace()
  if load_workspace_file() != ws:
    save_workspace_file(ws)
  if not st.session_state.get("_workspace_pickers_synced"):
    sync_workspace_pickers(ws)
    st.session_state["_workspace_pickers_synced"] = True


def sync_workspace_pickers(ws: dict | None = None):
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
  from gui.trade_model import format_model_oneline, get_active_trade_model
  container = container or st
  m = get_active_trade_model()
  if m:
    container.info(f"📦 {format_model_oneline(m)}")
  else:
    container.warning("Chưa chọn trade model — tạo từ **Học → Grid Search**.")


ensure_profiles_loaded = ensure_workspace_loaded
render_sidebar_profiles = lambda: None
render_sidebar_workspace = lambda: None
