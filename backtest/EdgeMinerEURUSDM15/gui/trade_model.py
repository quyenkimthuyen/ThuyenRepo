"""Trade Model — mô hình giao dịch tạo từ Grid Search (Live · Simulate · phân tích)."""
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


def is_model_archived(m: dict | None) -> bool:
  return bool(m and m.get("archived"))


def list_trade_models(*, include_archived: bool = False) -> list[dict]:
  """Registry models. By default hide archived (research shelf)."""
  models = list(load_models_store().get("models") or [])
  if include_archived:
    return models
  return [m for m in models if not is_model_archived(m)]


def get_model_by_id(model_id: str) -> dict | None:
  for m in list_trade_models(include_archived=True):
    if m.get("id") == model_id:
      return m
  return None


def known_live_model_ids() -> set[str]:
  """Ids eligible for Bridge / Active (not archived)."""
  return {str(m["id"]) for m in list_trade_models(include_archived=False) if m.get("id")}


def bridge_ghost_model_ids() -> list[str]:
  """Bridge config ids missing from live store (deleted or archived)."""
  known = known_live_model_ids()
  ghosts: list[str] = []
  for mid in get_bridge_runtime_model_ids():
    if mid and mid not in known:
      ghosts.append(str(mid))
  return ghosts


def _prune_bridge_label_prefs(remaining_ids: list[str]) -> None:
  """Drop stale labels from UI prefs so multiselect does not revive ghosts."""
  try:
    from gui.ui_preferences import get_preference, set_preference
  except Exception:
    return
  try:
    labels = get_preference("mt5.bridge_model_labels")
  except Exception:
    labels = None
  if not isinstance(labels, list):
    return
  id_set = {str(x) for x in remaining_ids}
  keep: list[str] = []
  for lab in labels:
    m = None
    for row in list_trade_models(include_archived=False):
      if format_model_label(row) == lab and str(row.get("id")) in id_set:
        m = row
        break
    if m is not None:
      keep.append(lab)
  if keep != labels:
    try:
      set_preference("mt5.bridge_model_labels", keep)
    except Exception:
      pass


def prune_bridge_roster(
  *,
  remove_ids: set[str] | None = None,
  drop_unknown: bool = True,
) -> dict:
  """Remove deleted/archived/explicit ids from Bridge ``model_ids``.

  Returns ``{before, after, removed, error?}``.
  """
  remove_ids = {str(x) for x in (remove_ids or set()) if x}
  known = known_live_model_ids()
  try:
    from mt5_bridge.background import load_config, save_config
    from mt5_bridge.protocol import normalize_model_ids

    cfg = load_config()
    before = normalize_model_ids(cfg.get("model_ids"), fallback=cfg.get("model_id"))
    after: list[str] = []
    removed: list[str] = []
    for mid in before:
      mid_s = str(mid)
      if mid_s in remove_ids or (drop_unknown and mid_s not in known):
        removed.append(mid_s)
      elif mid_s not in after:
        after.append(mid_s)
    if removed or list(before) != after:
      save_config(
        model_id=after[0] if after else "",
        model_ids=after,
      )
    _prune_bridge_label_prefs(after)
    # Best-effort: rewrite bridge models.json roster if present
    try:
      from mt5_bridge.protocol import BRIDGE_DIR, BRIDGE_SIM_DIR, write_models_roster
      for bdir in (BRIDGE_DIR, BRIDGE_SIM_DIR):
        try:
          write_models_roster(after, bridge_dir=bdir)
        except Exception:
          pass
    except Exception:
      pass
    return {"before": list(before), "after": after, "removed": removed}
  except Exception as exc:
    return {"before": [], "after": [], "removed": [], "error": str(exc)}


def archive_trade_model(model_id: str) -> dict | None:
  """Shelf a research model: keep artifacts, hide from live lists, prune Bridge."""
  store = load_models_store()
  target = None
  for m in store.get("models") or []:
    if m.get("id") == model_id:
      target = m
      break
  if target is None:
    return None
  target["archived"] = True
  target["archived_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  save_models_store(store)
  prune_bridge_roster(remove_ids={str(model_id)})
  if load_active_model_id() == model_id:
    remaining = list_trade_models(include_archived=False)
    set_active_trade_model(remaining[0]["id"] if remaining else None)
  st.session_state.pop("active_trade_model", None)
  return target


def unarchive_trade_model(model_id: str) -> dict | None:
  """Restore archived model to live store lists (does not auto-add to Bridge)."""
  store = load_models_store()
  target = None
  for m in store.get("models") or []:
    if m.get("id") == model_id:
      target = m
      break
  if target is None:
    return None
  target["archived"] = False
  target.pop("archived_at", None)
  save_models_store(store)
  st.session_state.pop("active_trade_model", None)
  return target


def load_active_model_id() -> str | None:
  data = _read_json(ACTIVE_MODEL_PATH)
  if isinstance(data, dict) and data.get("id"):
    return data["id"]
  models = list_trade_models(include_archived=False)
  return models[0]["id"] if models else None


def save_active_model_id(model_id: str | None):
  if model_id:
    _write_json(ACTIVE_MODEL_PATH, {"id": model_id})
  elif ACTIVE_MODEL_PATH.exists():
    ACTIVE_MODEL_PATH.unlink()


def format_model_label(m: dict) -> str:
  if m.get("label_custom"):
    return m.get("label") or m.get("id", "?")
  # Prefer stored display label when present (promoted / renamed models)
  if m.get("label"):
    return str(m["label"])
  return build_trade_profile_label({
    "train_weeks": m.get("train_weeks"),
    "use_kb": m.get("use_kb", True),
    "kb_profile": m.get("kb_profile"),
    "kb_snapshot": m.get("kb_snapshot"),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
  })


def format_model_short(m: dict | None, *, max_len: int = 42) -> str:
  """Compact name for sidebar / roster tables."""
  if not m:
    return "?"
  name = str(m.get("label") or format_model_label(m) or m.get("id") or "?").strip()
  # Drop redundant "Breakthrough " prefix noise in dense UI
  if name.lower().startswith("breakthrough "):
    name = name[13:]
  if max_len and len(name) > max_len:
    return name[: max_len - 1] + "…"
  return name


def bridge_roster_display_rows(
  *,
  include_runtime: bool = True,
  prefer_sim: bool = False,
) -> list[dict]:
  """Rows for Bridge multi-model roster UI (sidebar / banner / checklist)."""
  from mt5_bridge.protocol import (
    resolve_live_bridge_dir,
    resolve_sim_bridge_dir,
    read_json,
    read_models_roster,
    status_path,
  )

  ids = get_bridge_runtime_model_ids()
  live_dir = resolve_live_bridge_dir()
  sim_dir = resolve_sim_bridge_dir()
  primary_dir = sim_dir if prefer_sim else live_dir
  alt_dir = live_dir if prefer_sim else sim_dir
  roster = read_models_roster(primary_dir) or read_models_roster(alt_dir) or {}
  magic_by_id = {
    str(r.get("id")): r.get("magic")
    for r in (roster.get("models") or [])
    if isinstance(r, dict) and r.get("id")
  }
  status = read_json(status_path(primary_dir)) or {}
  per = status.get("per_model") if isinstance(status.get("per_model"), dict) else {}
  if not per:
    alt_st = read_json(status_path(alt_dir)) or {}
    per = alt_st.get("per_model") if isinstance(alt_st.get("per_model"), dict) else {}

  rows = []
  for mid in ids:
    m = get_model_by_id(mid)
    resolved = resolve_model_total_r(m) if m else {}
    pm = per.get(mid) or {}
    rows.append({
      "id": mid,
      "name": format_model_short(m) if m else mid[:28],
      "label": format_model_label(m) if m else mid,
      "magic": magic_by_id.get(mid),
      "oos_r": resolved.get("value"),
      "oos_from": resolved.get("oos_from"),
      "oos_to": resolved.get("oos_to"),
      "last_action": pm.get("action") if include_runtime else None,
      "last_reason": (pm.get("reason") or "")[:40] if include_runtime else None,
      "strategy": (pm.get("strategy_name") or "")[:36] if include_runtime else None,
      "conditions_fp": pm.get("conditions_fp") if include_runtime else None,
      "model": m,
    })
  return rows


def resolve_model_total_r(
  m: dict | None,
  *,
  report: dict | None = None,
  load_report: bool = True,
) -> dict:
  """Canonical Total R for banners / sidebar (per Trade Model).

  Priority (because mỗi model có OOS / remine riêng):
  1. Report remine/backtest của **chính model đó** → ``overall_oos.total_r`` (nguồn ``oos``)
  2. KPI lúc tạo từ Grid → registry ``total_r`` (nguồn ``grid``)

  Không dùng ``backtest_report.json`` global trừ khi caller đã resolve report đúng model.
  """
  out = {
    "value": None,
    "source": None,  # "oos" | "grid" | None
    "oos_from": None,
    "oos_to": None,
  }
  if not m:
    return out
  out["oos_from"] = (str(m.get("oos_from") or "")[:10] or None)
  out["oos_to"] = (str(m.get("oos_to") or "")[:10] or None)

  rep = report
  if rep is None and load_report and m.get("id"):
    rep = load_model_report(m["id"])
  if rep:
    o = rep.get("overall_oos") or {}
    if o.get("total_r") is not None:
      try:
        out["value"] = float(o["total_r"])
        out["source"] = "oos"
        # Prefer report window if present
        cfg = rep.get("config") or {}
        rf = cfg.get("oos_from") or rep.get("oos_start")
        rt = cfg.get("oos_to")
        if rf:
          out["oos_from"] = str(rf)[:10]
        if rt:
          out["oos_to"] = str(rt)[:10]
        return out
      except (TypeError, ValueError):
        pass

  if m.get("total_r") is not None:
    try:
      out["value"] = float(m["total_r"])
      out["source"] = "grid"
    except (TypeError, ValueError):
      pass
  return out


def format_model_total_r_text(resolved: dict, *, signed: bool = True, bold: bool = False) -> str:
  """Human label: ``+69.41R OOS`` or ``+125.07R Grid``."""
  v = resolved.get("value")
  if v is None:
    return "—"
  src = resolved.get("source")
  tag = "OOS" if src == "oos" else ("Grid" if src == "grid" else "")
  num = f"{float(v):+.2f}R" if signed else f"{float(v):.2f}R"
  body = f"{num} {tag}".strip() if tag else num
  return f"**{body}**" if bold else body


def format_model_oneline(m: dict, *, report: dict | None = None) -> str:
  line = format_model_label(m)
  resolved = resolve_model_total_r(m, report=report, load_report=report is None)
  if resolved.get("value") is not None:
    line += f" · {format_model_total_r_text(resolved, bold=True)}"
  return line


def _mining_space_brief(ss: dict | None) -> str:
  """Compact mining knobs for compare tables."""
  ss = ss or {}
  bits: list[str] = []
  mode = ss.get("selection_mode")
  if mode and mode != "legacy":
    bits.append(str(mode))
  if ss.get("anti_chase"):
    rsi = ss.get("anti_chase_fixed_rsi", "?")
    piece = f"chase rsi<{rsi}"
    if ss.get("anti_chase_use_vwap") or ss.get("anti_chase_fixed_vwap") is not None:
      logic = "∨" if str(ss.get("anti_chase_logic") or "").lower() == "or" else "∧"
      piece += f"{logic}vwap<{ss.get('anti_chase_fixed_vwap', '?')}"
    bits.append(piece)
  rr = ss.get("rr_ratios")
  if rr:
    bits.append(f"RR{list(rr)}")
  tpw = ss.get("target_trades_per_week")
  if tpw is not None:
    bits.append(f"tpw*{tpw}")
  if ss.get("exit_modes_full_only"):
    bits.append("exit:full")
  return " · ".join(bits) if bits else "baseline"


OVERVIEW_HIGH_DD_R = 6.5


def desk_pair_code() -> str:
  """EUR / GBP / OTHER — drives overview default sort."""
  import re
  try:
    from mt5_bridge.protocol import INSTANCE_ID
    inst = str(INSTANCE_ID or "").upper()
    if "GBP" in inst or re.search(r"M15G\d", inst):
      return "GBP"
    if "EUR" in inst or re.search(r"M15E\d", inst):
      return "EUR"
  except Exception:
    pass
  try:
    from gui.services import load_data_meta
    pair = str((load_data_meta() or {}).get("pair") or "").upper()
    if "GBP" in pair:
      return "GBP"
    if "EUR" in pair:
      return "EUR"
  except Exception:
    pass
  return "EUR"


def _overview_badges(
  *,
  source: str | None,
  dd: float | None,
  wr: float | None,
  has_oos_block: bool,
  archived: bool = False,
) -> list[str]:
  """Badge tags: Archived / Live-ok / High-DD / Grid-only / Stale."""
  badges: list[str] = []
  if archived:
    badges.append("Archived")
  high_dd = dd is not None and float(dd) > OVERVIEW_HIGH_DD_R
  if high_dd:
    badges.append("High-DD")
  if (
    not archived
    and source == "oos"
    and has_oos_block
    and not high_dd
    and wr is not None
  ):
    badges.append("Live-ok")
  if source == "grid":
    badges.append("Grid-only")
  if source not in ("oos", "grid") or (source == "oos" and not has_oos_block):
    badges.append("Stale")
  order = ["Archived", "Live-ok", "High-DD", "Grid-only", "Stale"]
  return [b for b in order if b in badges]


def build_trade_models_compare_rows(
  models: list[dict] | None = None,
  *,
  active_id: str | None = None,
  bridge_ids: list[str] | None = None,
  sort_desk: str | None = None,
) -> list[dict]:
  """Rows for the Trade Models overview compare table (all models).

  Prefers each model's ``overall_oos`` report when present; falls back to
  registry Grid KPI fields so every stored model appears.
  """
  models = list(
    models if models is not None else list_trade_models(include_archived=True)
  )
  if active_id is None:
    active = get_active_trade_model()
    active_id = str(active["id"]) if active and active.get("id") else None
  if bridge_ids is None:
    bridge_ids = get_bridge_runtime_model_ids()
  bridge_set = {str(x) for x in (bridge_ids or []) if x}
  desk = (sort_desk or desk_pair_code()).upper()

  rows: list[dict] = []
  for m in models:
    mid = str(m.get("id") or "")
    if not mid:
      continue
    archived = is_model_archived(m)
    report = load_model_report(mid)
    oos = (report or {}).get("overall_oos") or {}
    resolved = resolve_model_total_r(m, report=report, load_report=False)

    def _num(*keys, default=None):
      for src in (oos, m):
        for k in keys:
          if src.get(k) is not None:
            try:
              return float(src[k])
            except (TypeError, ValueError):
              continue
      return default

    total_r = resolved.get("value")
    wr = _num("win_rate_pct", "win_rate")
    dd = _num("max_drawdown_r", "max_dd_r")
    pf = _num("profit_factor", "pf")
    n_trades = _num("n_trades", "trades")
    tpw = _num("trades_per_week")
    if n_trades is not None:
      try:
        n_trades = int(n_trades)
      except (TypeError, ValueError):
        pass

    roles: list[str] = []
    if active_id and mid == str(active_id) and not archived:
      roles.append("Active")
    if mid in bridge_set:
      roles.append("Bridge")
    role = " · ".join(roles) if roles else ""

    oos_from = (resolved.get("oos_from") or str(m.get("oos_from") or "")[:10] or "—")
    oos_to = (resolved.get("oos_to") or str(m.get("oos_to") or "")[:10] or "—")
    oos_win = f"{oos_from}→{oos_to}" if oos_from != "—" or oos_to != "—" else "—"

    src = resolved.get("source")
    # Emphasize OOS vs muted Grid in plain text (dataframe has no rich cells)
    if src == "oos":
      source_label = "● OOS"
    elif src == "grid":
      source_label = "○ Grid"
    else:
      source_label = "—"

    badges = _overview_badges(
      source=src,
      dd=dd,
      wr=wr,
      has_oos_block=bool(oos),
      archived=archived,
    )
    high_dd = dd is not None and float(dd) > OVERVIEW_HIGH_DD_R

    rows.append({
      "id": mid,
      "Badge": " · ".join(badges) if badges else "—",
      "Vai trò": role,
      "Model": format_model_short(m, max_len=48),
      "Total R": round(float(total_r), 2) if total_r is not None else None,
      "WR %": round(float(wr), 1) if wr is not None else None,
      "Max DD": round(float(dd), 2) if dd is not None else None,
      "PF": round(float(pf), 2) if pf is not None else None,
      "Lệnh": n_trades,
      "Tpw": round(float(tpw), 2) if tpw is not None else None,
      "Train": m.get("train_weeks"),
      "KB ep": m.get("kb_snapshot") if m.get("kb_snapshot") is not None else "latest",
      "OOS": oos_win,
      "Mining": _mining_space_brief(m.get("mining_search_space")),
      "Nguồn": source_label,
      "_label": format_model_label(m),
      "_source": src,
      "_high_dd": high_dd,
      "_has_oos": src == "oos",
      "_archived": archived,
      "_sort_r": float(total_r) if total_r is not None else float("-inf"),
      "_sort_wr": float(wr) if wr is not None else float("-inf"),
      "_sort_dd": float(dd) if dd is not None else float("inf"),
    })

  if desk == "GBP":
    # Prefer quality: high WR, low DD, then Total R
    rows.sort(
      key=lambda r: (
        -r.get("_sort_wr", float("-inf")),
        r.get("_sort_dd", float("inf")),
        -r.get("_sort_r", float("-inf")),
      )
    )
  else:
    rows.sort(key=lambda r: r.get("_sort_r", float("-inf")), reverse=True)
  return rows


def overview_row_visible(
  row: dict,
  *,
  show_all: bool,
  show_archived: bool = False,
  bridge_ids: list[str] | None = None,
) -> bool:
  """Default filter: hide archived, High-DD, non-OOS (Bridge ghosts still shown)."""
  if row.get("_archived") and not show_archived and not show_all:
    return False
  if show_all:
    return True
  bridge_set = {str(x) for x in (bridge_ids or []) if x}
  if row.get("id") in bridge_set:
    return True
  if row.get("_archived"):
    return False
  if row.get("_high_dd"):
    return False
  if not row.get("_has_oos"):
    return False
  return True


def model_report_path(model_id: str) -> Path:
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}.json"


def model_kb_off_report_path(model_id: str) -> Path:
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}_kb_off.json"


def model_remine_off_report_path(model_id: str) -> Path:
  """Walk-forward with strategy frozen after first OOS week (Remine OFF)."""
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}_remine_off.json"


def model_mining_baseline_report_path(model_id: str) -> Path:
  """Walk-forward with baseline mining space (same KB/train/OOS as model)."""
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}_mining_baseline.json"


def save_model_report(model_id: str, report: dict):
  payload = dict(report)
  cfg = dict(payload.get("config") or {})
  cfg["trade_model_id"] = model_id
  payload["config"] = cfg
  schedule_weekly = payload.pop("schedule_weekly", None)
  _write_json(model_report_path(model_id), payload)
  try:
    from trade_model_schedule import (
      build_schedule_payload,
      save_model_schedule,
      schedule_from_walk_forward_result,
    )
    if schedule_weekly:
      sched = build_schedule_payload(
        model_id=model_id,
        weekly_entries=list(schedule_weekly),
        config=cfg,
        data_fingerprint=(payload.get("data_source") or {}).get("fingerprint")
        or cfg.get("data_fingerprint"),
        overall=payload.get("overall_oos"),
        source="walk_forward",
      )
    else:
      payload_with = dict(payload)
      payload_with["schedule_weekly"] = report.get("schedule_weekly")
      sched = schedule_from_walk_forward_result(payload_with, model_id)
    if sched:
      save_model_schedule(model_id, sched)
  except Exception:
    pass


def save_model_kb_off_report(model_id: str, report: dict):
  payload = dict(report)
  cfg = dict(payload.get("config") or {})
  cfg["trade_model_id"] = model_id
  cfg["use_learning_kb"] = False
  cfg["kb_compare_role"] = "kb_off_baseline"
  payload["config"] = cfg
  _write_json(model_kb_off_report_path(model_id), payload)


def save_model_remine_off_report(model_id: str, report: dict):
  payload = dict(report)
  cfg = dict(payload.get("config") or {})
  cfg["trade_model_id"] = model_id
  cfg["remine_each_week"] = False
  cfg["remine_mode"] = "freeze_first"
  cfg["remine_compare_role"] = "remine_off_baseline"
  payload["config"] = cfg
  # Do not overwrite weekly remine schedule from a freeze run.
  payload.pop("schedule_weekly", None)
  _write_json(model_remine_off_report_path(model_id), payload)


def save_model_mining_baseline_report(model_id: str, report: dict):
  payload = dict(report)
  cfg = dict(payload.get("config") or {})
  cfg["trade_model_id"] = model_id
  cfg["mining_compare_role"] = "baseline_miner"
  payload["config"] = cfg
  _write_json(model_mining_baseline_report_path(model_id), payload)


def load_model_report(model_id: str | None = None) -> dict | None:
  mid = model_id or load_active_model_id()
  if not mid:
    return None
  return _read_json(model_report_path(mid))


def load_model_kb_off_report(model_id: str | None = None) -> dict | None:
  mid = model_id or load_active_model_id()
  if not mid:
    return None
  return _read_json(model_kb_off_report_path(mid))


def load_model_remine_off_report(model_id: str | None = None) -> dict | None:
  mid = model_id or load_active_model_id()
  if not mid:
    return None
  return _read_json(model_remine_off_report_path(mid))


def load_model_mining_baseline_report(model_id: str | None = None) -> dict | None:
  mid = model_id or load_active_model_id()
  if not mid:
    return None
  return _read_json(model_mining_baseline_report_path(mid))


def get_active_trade_model(*, force_reload: bool = False) -> dict | None:
  if force_reload:
    st.session_state.pop("active_trade_model", None)
  if "active_trade_model" in st.session_state:
    cached = st.session_state["active_trade_model"]
    if cached and not is_model_archived(cached):
      return cached
    st.session_state.pop("active_trade_model", None)
  mid = load_active_model_id()
  if not mid:
    return None
  m = get_model_by_id(mid)
  if m and is_model_archived(m):
    # Active file still points at archived shelf — fall through to live list
    live = list_trade_models(include_archived=False)
    if not live:
      return None
    m = live[0]
    save_active_model_id(m["id"])
  if m:
    st.session_state["active_trade_model"] = m
  return m


def set_active_trade_model(model_id: str | None) -> dict | None:
  if model_id:
    m = get_model_by_id(model_id)
    if not m:
      raise ValueError(f"Trade model `{model_id}` không tồn tại.")
    if is_model_archived(m):
      raise ValueError(
        f"Trade model `{model_id}` đang Archived — Restore trước khi đặt Active."
      )
    save_active_model_id(model_id)
    st.session_state["active_trade_model"] = m
    st.session_state.pop("backtest_report", None)
    # Do not rewrite Bridge roster from Active (analysis pointer only).
    try:
      from gui.workspace import save_workspace_file
      save_workspace_file(trade_model_to_workspace(m))
    except Exception:
      pass
    return m
  save_active_model_id(None)
  st.session_state.pop("active_trade_model", None)
  return None


def sync_active_model_into_runtime_configs() -> dict | None:
  """Deprecated no-op.

  Active Trade Model is analysis-only (Trade Models tabs). Bridge roster is
  chosen explicitly on MT5 Bridge and must not be overwritten by Active.
  Kept for import compatibility with older callers.
  """
  return get_active_trade_model()


def get_bridge_runtime_model_ids() -> list[str]:
  """Model ids selected for MT5 Bridge Live/Sim (multi-model roster)."""
  try:
    from mt5_bridge.background import load_config as bridge_load
    from mt5_bridge.protocol import normalize_model_ids

    cfg = bridge_load()
    return normalize_model_ids(cfg.get("model_ids"), fallback=cfg.get("model_id"))
  except Exception:
    return []


def render_shared_trade_model_banner(*, context: str = "shared") -> dict | None:
  """Show Bridge roster (runtime). Does not sync or display Active as runtime.

  ``context`` is kept for callers; Paper Monitor is retired — prefer
  ``live`` / ``simulate`` / ``shared``.
  """
  bridge_ids = get_bridge_runtime_model_ids()
  prefer_sim = context == "simulate"

  if len(bridge_ids) > 1:
    rows = bridge_roster_display_rows(
      include_runtime=True,
      prefer_sim=prefer_sim,
    )
    st.markdown(
      f"**Bridge đang chạy {len(rows)} Trade Model** · Risk %/lệnh chung · 1 lệnh mở / model"
    )
    table = []
    for i, r in enumerate(rows, 1):
      oos = f"{r['oos_r']:+.1f}R" if r.get("oos_r") is not None else "—"
      table.append({
        "#": i,
        "Model": r["name"],
        "Magic": r.get("magic") or "—",
        "OOS R": oos,
        "Last": r.get("last_action") or "—",
        "Reason": r.get("last_reason") or "—",
      })
    import pandas as pd
    st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    st.caption(
      "Roster runtime (Live/Sim). Đổi danh sách tại **MT5 Bridge → Trade Models** (multiselect). "
      "Active trong tab Trade Models chỉ để phân tích — không điều khiển Bridge."
    )
    return get_model_by_id(bridge_ids[0])

  if len(bridge_ids) == 1:
    m = get_model_by_id(bridge_ids[0])
    if m:
      label = format_model_label(m)
      resolved = resolve_model_total_r(m)
      bits = [f"**Bridge:** {label}"]
      if resolved.get("value") is not None:
        bits.append(format_model_total_r_text(resolved, bold=True))
      st.markdown(" · ".join(bits))
      st.caption(
        "Model trên MT5 Bridge (runtime). Phân tích model khác: tab **Trade Models** (Active)."
      )
      return m

  st.warning(
    "Chưa chọn roster Bridge — mở **MT5 Bridge** → tab Trade Models, chọn 1–5 model rồi Start."
  )
  return None


def model_from_grid_row(row: dict, *, run_id: str | None = None, label: str | None = None) -> dict:
  from gui.app_settings import canonical_kb_profile, default_learning_era
  from gui.services import load_data_meta
  tw = row.get("train_weeks", 6)
  kb = canonical_kb_profile(row.get("kb_profile")) or default_learning_era()["kb_profile"]
  ep = _normalize_snapshot(row.get("kb_snapshot"))
  auto_label = label or build_trade_profile_label({
    "train_weeks": tw,
    "use_kb": bool(row.get("use_kb", True)),
    "kb_profile": kb if row.get("use_kb") else None,
    "kb_snapshot": ep,
    "oos_from": row.get("oos_from"),
    "oos_to": row.get("oos_to"),
  })
  if label is None and row.get("total_r") is not None:
    auto_label += f" · {row.get('total_r', 0):+.1f}R"
  data_meta = load_data_meta()
  if (
    data_meta.get("source") != "mt5_ea"
    or data_meta.get("timeframe") != "M15"
    or not data_meta.get("fingerprint")
  ):
    raise RuntimeError("Không thể tạo Trade Model khi dữ liệu chưa được xác nhận từ MT5 EA.")
  return {
    "train_weeks": tw,
    "max_trades_per_day": 2,
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
    "feature_profile": row.get("feature_profile") or "current",
    "mining_search_space": row.get("mining_search_space"),
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
    "feature_schema": 3,
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


def _unique_label(desired: str, *, exclude_id: str | None = None) -> str:
  """Avoid identical display names: Best 3m, Best 3m (2), …"""
  base = (desired or "Trade model").strip() or "Trade model"
  existing: set[str] = set()
  for m in list_trade_models():
    if exclude_id and m.get("id") == exclude_id:
      continue
    existing.add((m.get("label") or "").strip().lower())
    existing.add(format_model_label(m).strip().lower())
  if base.lower() not in existing:
    return base
  n = 2
  while f"{base} ({n})".lower() in existing:
    n += 1
  return f"{base} ({n})"


def rename_trade_model(model_id: str, new_label: str) -> dict | None:
  """Set a custom display label. Keeps ``id`` stable for Live/Sim/journal links."""
  desired = (new_label or "").strip()
  if not desired:
    raise ValueError("Tên Trade Model không được trống.")
  store = load_models_store()
  target = None
  for m in store.get("models") or []:
    if m.get("id") == model_id:
      target = m
      break
  if target is None:
    return None
  name = _unique_label(desired, exclude_id=model_id)
  target["label"] = name
  target["label_custom"] = True
  save_models_store(store)
  return target


def reset_trade_model_label(model_id: str) -> dict | None:
  """Clear custom name and restore auto label from train/KB/OOS fields."""
  store = load_models_store()
  target = None
  for m in store.get("models") or []:
    if m.get("id") == model_id:
      target = m
      break
  if target is None:
    return None
  auto = build_trade_profile_label({
    "train_weeks": target.get("train_weeks"),
    "use_kb": target.get("use_kb", True),
    "kb_profile": target.get("kb_profile"),
    "kb_snapshot": target.get("kb_snapshot"),
    "oos_from": target.get("oos_from"),
    "oos_to": target.get("oos_to"),
  })
  target["label"] = _unique_label(auto, exclude_id=model_id)
  target["label_custom"] = False
  save_models_store(store)
  return target


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
      # Ensure older models get a KB pin when reused.
      try:
        from trade_model_kb_pin import ensure_model_kb_pin
        store = load_models_store()
        for m in store["models"]:
          if m.get("id") != existing["id"]:
            continue
          before = m.get("kb_fingerprint")
          ensure_model_kb_pin(m)
          if m.get("kb_fingerprint") != before:
            existing = m
            save_models_store(store)
          break
      except Exception:
        pass
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
  try:
    from trade_model_kb_pin import ensure_model_kb_pin
    ensure_model_kb_pin(model)
  except Exception:
    pass
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
    try:
      delete_model_artifacts(mid)
    except OSError:
      pass

  store["models"] = kept
  save_models_store(store)

  active = load_active_model_id()
  if active in removed or (active and not get_model_by_id(active)):
    prefer = next((m for m in kept if m.get("id") in keep_ids), None)
    set_active_trade_model((prefer or (kept[0] if kept else {})).get("id"))

  return {"removed": removed, "renamed": renamed, "kept": len(kept)}


def _model_id_from_artifact_name(name: str) -> str | None:
  if not name.endswith(".json"):
    return None
  stem = name[:-5]
  for suffix in ("_kb_off", "_remine_off", "_mining_baseline", "_kb_pin", "_live_weeks", "_schedule"):
    if stem.endswith(suffix):
      return stem[: -len(suffix)]
  return stem


def model_artifact_paths(model_id: str) -> list[Path]:
  paths = [
    model_report_path(model_id),
    model_kb_off_report_path(model_id),
    model_remine_off_report_path(model_id),
    model_mining_baseline_report_path(model_id),
  ]
  try:
    from trade_model_kb_pin import model_kb_pin_path
    paths.append(model_kb_pin_path(model_id))
  except Exception:
    pass
  try:
    from trade_model_schedule import model_live_weeks_path, model_schedule_path
    paths.extend([model_schedule_path(model_id), model_live_weeks_path(model_id)])
  except Exception:
    pass
  return paths


def delete_model_artifacts(model_id: str) -> list[str]:
  cleared: list[str] = []
  for path in model_artifact_paths(model_id):
    if path.exists():
      path.unlink()
      cleared.append(path.name)
  return cleared


def purge_orphan_model_artifacts() -> list[str]:
  """Xóa file artifact trên đĩa không còn model trong registry."""
  known = {m.get("id") for m in list_trade_models() if m.get("id")}
  cleared: list[str] = []
  if not MODELS_DIR.exists():
    return cleared
  orphan_ids: set[str] = set()
  for path in MODELS_DIR.glob("*.json"):
    mid = _model_id_from_artifact_name(path.name)
    if mid and mid not in known:
      orphan_ids.add(mid)
  for mid in sorted(orphan_ids):
    cleared.extend(delete_model_artifacts(mid))
  return cleared


def delete_trade_model(model_id: str) -> bool:
  store = load_models_store()
  before = len(store["models"])
  store["models"] = [m for m in store["models"] if m.get("id") != model_id]
  if len(store["models"]) == before:
    return False
  save_models_store(store)
  delete_model_artifacts(model_id)
  prune_bridge_roster(remove_ids={str(model_id)})
  if load_active_model_id() == model_id:
    remaining = list_trade_models(include_archived=False)
    set_active_trade_model(remaining[0]["id"] if remaining else None)
  st.session_state.pop("active_trade_model", None)
  return True


def get_model_run_params(model: dict | None = None) -> dict:
  """Canonical run params — delegates to mt5_bridge.models (same as Bridge)."""
  m = model or get_active_trade_model()
  if not m:
    from gui.app_settings import default_learning_era, get_settings
    s = get_settings()
    era = default_learning_era(s)
    trains = s.get("strategy_train_weeks") or [3, 6, 9]
    return {
      "train_weeks": trains[0] if trains else 6,
      "use_learning": True,
      "use_kb": True,
      "kb_profile": era["kb_profile"],
      "kb_snapshot": None,
      "oos_from": s.get("backtest_from"),
      "oos_to": s.get("backtest_to"),
      "spread_pips": float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
      "feature_profile": "current",
      "mining_search_space": None,
    }
  from mt5_bridge.models import get_model_run_params as bridge_run_params
  return bridge_run_params(m, m.get("id"))


def trade_model_to_workspace(m: dict | None = None) -> dict:
  m = m or get_active_trade_model()
  if not m:
    from gui.app_settings import default_learning_era, get_settings
    s = get_settings()
    era = default_learning_era(s)
    trains = s.get("strategy_train_weeks") or [3, 6, 9]
    return {
      "label": "Chưa chọn trade model",
      "kb_profile": era["kb_profile"],
      "kb_snapshot": None,
      "oos_from": s.get("backtest_from"),
      "oos_to": s.get("backtest_to"),
      "use_learning": True,
      "train_weeks": trains[0] if trains else 6,
    }
  return {
    "label": format_model_label(m),
    "kb_profile": m.get("kb_profile") or "default",
    "kb_snapshot": _normalize_snapshot(m.get("kb_snapshot")),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
    "use_learning": bool(m.get("use_kb", True)),
    "train_weeks": m.get("train_weeks", 6),
    "spread_pips": m.get("spread_pips", DEFAULT_SPREAD_PIPS),
    "slippage_pips": m.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    "feature_profile": (
      m.get("feature_profile")
      or ("legacy" if int(m.get("feature_schema") or 0) < 3 else "current")
    ),
    "mining_search_space": m.get("mining_search_space"),
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


def _space_fingerprint(space: dict | None) -> tuple:
  if not space:
    return ()
  return (
    tuple(tuple(x) if isinstance(x, list) else x for x in (space.get("session_ranges") or [])),
    tuple(space.get("min_bars_between") or []),
    tuple(space.get("max_hold_bars") or []),
  )


def report_search_space_matches_model(
  report: dict | None,
  model: dict | None = None,
) -> bool:
  """True if report mining space matches the Trade Model (session/spacing/hold)."""
  m = model or get_active_trade_model()
  if not report or not m:
    return False
  expected = m.get("mining_search_space")
  if not expected:
    return True
  actual = (report.get("config") or {}).get("mining_search_space")
  return _space_fingerprint(expected) == _space_fingerprint(actual)


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
