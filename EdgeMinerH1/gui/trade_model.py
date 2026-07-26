"""Trade Model — mô hình giao dịch tạo từ Grid Search (dùng cho paper & phân tích)."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from gui.glossary import build_trade_profile_label
from run_backtest import REPORT_DIR

MODELS_PATH = REPORT_DIR / "trade_models.json"
ACTIVE_MODEL_PATH = REPORT_DIR / "active_trade_model.json"
MODELS_DIR = REPORT_DIR / "trade_models"


def _read_json(path: Path) -> dict | list | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data):
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def _new_id(label: str) -> str:
  slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", label.lower()).strip("_")[:28]
  return f"tm_{slug or 'model'}_{uuid.uuid4().hex[:8]}"


def _normalize_snapshot(val) -> int | None:
  if val is None or val in ("latest", "Latest", ""):
    return None
  try:
    return int(val)
  except (TypeError, ValueError):
    return None


def load_models_store() -> dict:
  data = _read_json(MODELS_PATH)
  if not data or not isinstance(data, dict):
    return {"models": []}
  return data


def save_models_store(store: dict):
  _write_json(MODELS_PATH, store)


def list_trade_models() -> list[dict]:
  return load_models_store().get("models") or []


def get_model_by_id(model_id: str) -> dict | None:
  for m in list_trade_models():
    if m.get("id") == model_id:
      return m
  return None


def load_active_model_id() -> str | None:
  data = _read_json(ACTIVE_MODEL_PATH)
  if isinstance(data, dict) and data.get("id"):
    return data["id"]
  models = list_trade_models()
  return models[0]["id"] if models else None


def save_active_model_id(model_id: str | None):
  if model_id:
    _write_json(ACTIVE_MODEL_PATH, {"id": model_id})
  elif ACTIVE_MODEL_PATH.exists():
    ACTIVE_MODEL_PATH.unlink()


def format_model_label(m: dict) -> str:
  if m.get("label_custom"):
    return m.get("label") or m.get("id", "?")
  return build_trade_profile_label({
    "train_months": m.get("train_months"),
    "use_kb": m.get("use_kb", True),
    "kb_profile": m.get("kb_profile"),
    "kb_snapshot": m.get("kb_snapshot"),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
  })


def format_model_oneline(m: dict) -> str:
  line = format_model_label(m)
  if m.get("total_r") is not None:
    line += f" · **{m['total_r']:+.2f}R**"
  return line


def model_report_path(model_id: str) -> Path:
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}.json"


def save_model_report(model_id: str, report: dict):
  payload = dict(report)
  cfg = dict(payload.get("config") or {})
  cfg["trade_model_id"] = model_id
  payload["config"] = cfg
  _write_json(model_report_path(model_id), payload)


def load_model_report(model_id: str | None = None) -> dict | None:
  mid = model_id or load_active_model_id()
  if not mid:
    return None
  return _read_json(model_report_path(mid))


def get_active_trade_model(*, force_reload: bool = False) -> dict | None:
  if force_reload:
    st.session_state.pop("active_trade_model", None)
  if "active_trade_model" in st.session_state:
    return st.session_state["active_trade_model"]
  mid = load_active_model_id()
  if not mid:
    return None
  m = get_model_by_id(mid)
  if m:
    st.session_state["active_trade_model"] = m
  return m


def set_active_trade_model(model_id: str | None) -> dict | None:
  if model_id:
    m = get_model_by_id(model_id)
    if not m:
      raise ValueError(f"Trade model `{model_id}` không tồn tại.")
    save_active_model_id(model_id)
    st.session_state["active_trade_model"] = m
    st.session_state.pop("backtest_report", None)
    try:
      from mt5_bridge.background import save_config as save_bridge_config
      save_bridge_config(model_id=model_id)
    except Exception:
      pass
    try:
      from gui.workspace import save_workspace_file
      save_workspace_file(trade_model_to_workspace(m))
    except Exception:
      pass
    return m
  save_active_model_id(None)
  st.session_state.pop("active_trade_model", None)
  return None


def model_from_grid_row(row: dict, *, run_id: str | None = None, label: str | None = None) -> dict:
  from gui.app_settings import canonical_kb_profile, default_learning_era
  from gui.services import load_data_meta
  tm = row.get("train_months", 6)
  kb = canonical_kb_profile(row.get("kb_profile")) or default_learning_era()["kb_profile"]
  ep = _normalize_snapshot(row.get("kb_snapshot"))
  auto_label = label or build_trade_profile_label({
    "train_months": tm,
    "use_kb": bool(row.get("use_kb", True)),
    "kb_profile": kb if row.get("use_kb") else None,
    "kb_snapshot": ep,
    "oos_from": row.get("oos_from"),
    "oos_to": row.get("oos_to"),
  })
  if label is None and row.get("total_r") is not None:
    auto_label += f" · {row.get('total_r', 0):+.1f}R"
  data_meta = load_data_meta()
  if data_meta.get("source") != "mt5_ea" or not data_meta.get("fingerprint"):
    raise RuntimeError("Không thể tạo Trade Model khi dữ liệu chưa được xác nhận từ MT5 EA.")
  return {
    "train_months": tm,
    "use_kb": bool(row.get("use_kb", True)),
    "kb_profile": kb if row.get("use_kb") else None,
    "kb_snapshot": ep,
    "oos_from": row.get("oos_from"),
    "oos_to": row.get("oos_to"),
    "spread_pips": row.get("spread_pips", DEFAULT_SPREAD_PIPS),
    "slippage_pips": row.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    "total_r": row.get("total_r"),
    "win_rate_pct": row.get("win_rate_pct"),
    "max_drawdown_r": row.get("max_drawdown_r"),
    "profit_factor": row.get("profit_factor"),
    "n_trades": row.get("n_trades"),
    "source": "grid_search",
    "data_source": data_meta.get("source"),
    "data_broker": data_meta.get("broker"),
    "data_symbol": data_meta.get("pair"),
    "data_timeframe": data_meta.get("timeframe"),
    "data_timezone": data_meta.get("broker_timezone"),
    "data_start": data_meta.get("start"),
    "data_end": data_meta.get("end"),
    "data_bars": data_meta.get("bars"),
    "data_fingerprint": data_meta.get("fingerprint"),
    "feature_schema": 1,
    "grid_run_id": run_id,
    "grid_key": row.get("key"),
    "label": auto_label,
    "label_custom": bool(label),
  }


def find_model_by_grid_key(grid_key: str | None) -> dict | None:
  if not grid_key:
    return None
  for m in list_trade_models():
    if m.get("grid_key") == grid_key:
      return m
  return None


def find_model_by_label(label: str | None) -> dict | None:
  if not label:
    return None
  key = label.strip().lower()
  for m in list_trade_models():
    if (m.get("label") or "").strip().lower() == key:
      return m
    # also match formatted display label for non-custom
    if format_model_label(m).strip().lower() == key:
      return m
  return None


def _unique_label(desired: str) -> str:
  """Avoid identical display names: Best 3m, Best 3m (2), …"""
  base = (desired or "Trade model").strip() or "Trade model"
  existing = {(m.get("label") or "").strip().lower() for m in list_trade_models()}
  existing |= {format_model_label(m).strip().lower() for m in list_trade_models()}
  if base.lower() not in existing:
    return base
  n = 2
  while f"{base} ({n})".lower() in existing:
    n += 1
  return f"{base} ({n})"


def create_trade_model(
  row: dict,
  *,
  run_id: str | None = None,
  label: str | None = None,
  report: dict | None = None,
  set_active: bool = True,
  build_report: bool = True,
  allow_duplicate_combo: bool = False,
) -> dict:
  """
  Create a trade model from a grid row.
  - Same grid_key (same combo) → reuse existing model unless allow_duplicate_combo.
  - Same label → auto-suffix « (2) », « (3) », …
  """
  fields = model_from_grid_row(row, run_id=run_id, label=label)
  name = fields.pop("label")
  grid_key = fields.get("grid_key") or row.get("key")

  if not allow_duplicate_combo and grid_key:
    existing = find_model_by_grid_key(grid_key)
    if existing:
      if label and label.strip():
        desired = label.strip()
        other = find_model_by_label(desired)
        store = load_models_store()
        for m in store["models"]:
          if m.get("id") != existing["id"]:
            continue
          if other and other.get("id") != existing["id"]:
            m["label"] = _unique_label(desired)
          else:
            m["label"] = desired
          m["label_custom"] = True
          existing = m
          break
        save_models_store(store)
      if set_active:
        set_active_trade_model(existing["id"])
      if build_report and not load_model_report(existing["id"]):
        try:
          from gui.analysis_support import start_model_report_job
          from gui.long_task_background import is_task_running
          if not is_task_running():
            start_model_report_job(existing)
        except Exception:
          pass
      return existing

  name = _unique_label(name)
  model = {
    **fields,
    "id": _new_id(name),
    "label": name,
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
  }
  store = load_models_store()
  store["models"].append(model)
  save_models_store(store)
  if report:
    save_model_report(model["id"], report)
  if set_active:
    set_active_trade_model(model["id"])
  if build_report and not report:
    try:
      from gui.analysis_support import start_model_report_job
      from gui.long_task_background import is_task_running
      if not is_task_running():
        start_model_report_job(model)
    except Exception:
      pass
  return model


def dedupe_trade_models(*, keep_ids: set[str] | None = None) -> dict:
  """
  Keep one model per grid_key.
  Preference: keep_ids > custom label «Best*» > earliest created_at.
  Then uniquify duplicate labels.
  """
  store = load_models_store()
  models = list(store.get("models") or [])
  keep_ids = keep_ids or set()
  by_key: dict[str, dict] = {}
  no_key: list[dict] = []
  removed: list[str] = []

  def _rank(m: dict) -> tuple:
    mid = m.get("id") or ""
    lab = (m.get("label") or "").lower()
    return (
      0 if mid in keep_ids else 1,
      0 if lab.startswith("best") else 1,
      str(m.get("created_at") or ""),
    )

  for m in models:
    gk = m.get("grid_key")
    if not gk:
      no_key.append(m)
      continue
    prev = by_key.get(gk)
    if not prev:
      by_key[gk] = m
      continue
    # lower rank tuple wins
    if _rank(m) < _rank(prev):
      removed.append(prev["id"])
      by_key[gk] = m
    else:
      removed.append(m["id"])

  kept = list(by_key.values()) + no_key
  renamed: list[dict] = []
  seen_labels: set[str] = set()
  for m in kept:
    lab = (m.get("label") or m.get("id") or "?").strip()
    low = lab.lower()
    if low in seen_labels:
      n = 2
      while f"{lab} ({n})".lower() in seen_labels:
        n += 1
      new_lab = f"{lab} ({n})"
      renamed.append({"id": m["id"], "from": lab, "to": new_lab})
      m["label"] = new_lab
      m["label_custom"] = True
      seen_labels.add(new_lab.lower())
    else:
      seen_labels.add(low)

  for mid in removed:
    path = model_report_path(mid)
    if path.exists():
      try:
        path.unlink()
      except OSError:
        pass

  store["models"] = kept
  save_models_store(store)

  active = load_active_model_id()
  if active in removed or (active and not get_model_by_id(active)):
    prefer = next((m for m in kept if m.get("id") in keep_ids), None)
    set_active_trade_model((prefer or (kept[0] if kept else {})).get("id"))

  return {"removed": removed, "renamed": renamed, "kept": len(kept)}


def delete_trade_model(model_id: str) -> bool:
  store = load_models_store()
  before = len(store["models"])
  store["models"] = [m for m in store["models"] if m.get("id") != model_id]
  if len(store["models"]) == before:
    return False
  save_models_store(store)
  path = model_report_path(model_id)
  if path.exists():
    path.unlink()
  if load_active_model_id() == model_id:
    remaining = store["models"]
    set_active_trade_model(remaining[0]["id"] if remaining else None)
  st.session_state.pop("active_trade_model", None)
  return True


def get_model_run_params(model: dict | None = None) -> dict:
  m = model or get_active_trade_model()
  if not m:
    from gui.app_settings import default_learning_era, get_settings
    s = get_settings()
    era = default_learning_era(s)
    trains = s.get("strategy_train_months") or [3, 6, 9]
    return {
      "train_months": trains[0] if trains else 6,
      "use_learning": True,
      "use_kb": True,
      "kb_profile": era["kb_profile"],
      "kb_snapshot": None,
      "oos_from": s.get("backtest_from"),
      "oos_to": s.get("backtest_to"),
      "spread_pips": float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    }
  return {
    "train_months": int(m.get("train_months", 6)),
    "use_learning": bool(m.get("use_kb", True)),
    "use_kb": bool(m.get("use_kb", True)),
    "kb_profile": m.get("kb_profile") or "default",
    "kb_snapshot": _normalize_snapshot(m.get("kb_snapshot")),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
    "spread_pips": float(m.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(m.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "trade_model_id": m.get("id"),
  }


def trade_model_to_workspace(m: dict | None = None) -> dict:
  m = m or get_active_trade_model()
  if not m:
    from gui.app_settings import default_learning_era, get_settings
    s = get_settings()
    era = default_learning_era(s)
    trains = s.get("strategy_train_months") or [3, 6, 9]
    return {
      "label": "Chưa chọn trade model",
      "kb_profile": era["kb_profile"],
      "kb_snapshot": None,
      "oos_from": s.get("backtest_from"),
      "oos_to": s.get("backtest_to"),
      "use_learning": True,
      "train_months": trains[0] if trains else 6,
    }
  return {
    "label": format_model_label(m),
    "kb_profile": m.get("kb_profile") or "default",
    "kb_snapshot": _normalize_snapshot(m.get("kb_snapshot")),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
    "use_learning": bool(m.get("use_kb", True)),
    "train_months": m.get("train_months", 6),
    "spread_pips": m.get("spread_pips", DEFAULT_SPREAD_PIPS),
    "slippage_pips": m.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    "trade_model_id": m.get("id"),
  }


def report_matches_model(report: dict, model: dict | None = None) -> bool:
  m = model or get_active_trade_model()
  if not m:
    return False
  cfg = report.get("config") or {}
  if cfg.get("trade_model_id") and m.get("id"):
    return cfg["trade_model_id"] == m["id"]
  from gui.workspace import report_matches_workspace
  return report_matches_workspace(report, trade_model_to_workspace(m))


def ensure_trade_models_loaded():
  load_models_store()
  get_active_trade_model()


def render_model_picker(*, key: str = "tm_pick", label: str = "Trade model") -> dict | None:
  models = list_trade_models()
  if not models:
    st.info("Chưa có trade model — tạo từ **Học → Grid Search**.")
    return None
  labels = [format_model_label(m) for m in models]
  id_by_label = {format_model_label(m): m["id"] for m in models}
  active = get_active_trade_model()
  active_id = active.get("id") if active else models[0]["id"]
  current = format_model_label(active) if active else labels[0]
  idx = labels.index(current) if current in labels else 0
  pick = st.selectbox(label, labels, index=idx, key=key)
  if id_by_label.get(pick) != active_id:
    set_active_trade_model(id_by_label[pick])
    st.rerun()
  return get_active_trade_model()
