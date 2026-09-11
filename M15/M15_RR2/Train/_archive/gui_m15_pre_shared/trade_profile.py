"""Trade Profile — gom mọi setting trade vào một profile có thể chọn / tạo nhiều."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from kb_profiles import DEFAULT_PROFILE_ID, get_profile
from run_backtest import REPORT_DIR

PROFILES_PATH = REPORT_DIR / "trade_profiles.json"
ACTIVE_PATH = REPORT_DIR / "active_trade_profile.json"

DEFAULT_PROFILE_ID_TP = "default_best_oos"

DEFAULT_TRADE_PROFILE = {
  "id": DEFAULT_PROFILE_ID_TP,
  "label": "Học 6 tháng · Giai đoạn 2024 · vòng 3 · Kiểm chứng 2025–2026",
  "is_default": True,
  "train_months": 6,
  "use_kb": True,
  "kb_profile": "era_2024",
  "kb_snapshot": 3,
  "oos_from": "2025-01-01",
  "oos_to": "2026-12-31",
  "spread_pips": DEFAULT_SPREAD_PIPS,
  "slippage_pips": DEFAULT_SLIPPAGE_PIPS,
  "strategy_note": "crossover_mut (pre-v4 best, ~+99R train window compare)",
  "source": "default",
  "grid_run_id": None,
  "backtest_total_r": None,
}


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
  slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", label.lower()).strip("_")[:32]
  return f"{slug or 'profile'}_{uuid.uuid4().hex[:8]}"


def _normalize_snapshot(val) -> int | None:
  if val is None or val in ("latest", "Latest", ""):
    return None
  try:
    return int(val)
  except (TypeError, ValueError):
    return None


def _profile_for_store(tp: dict) -> dict:
  """Bản lưu file — bỏ field derive từ kb_profile."""
  out = dict(tp)
  out.pop("learn_from", None)
  out.pop("learn_until", None)
  if "kb_snapshot" in out:
    out["kb_snapshot"] = _normalize_snapshot(out["kb_snapshot"])
  return out


def load_profiles_store() -> dict:
  data = _read_json(PROFILES_PATH)
  if not data or not isinstance(data, dict):
    return {"profiles": [dict(DEFAULT_TRADE_PROFILE)]}
  profiles = data.get("profiles") or []
  if not any(p.get("id") == DEFAULT_PROFILE_ID_TP for p in profiles):
    profiles.insert(0, dict(DEFAULT_TRADE_PROFILE))
  return {"profiles": profiles}


def save_profiles_store(store: dict):
  _write_json(PROFILES_PATH, store)


def list_trade_profiles() -> list[dict]:
  return load_profiles_store()["profiles"]


def get_profile_by_id(profile_id: str) -> dict | None:
  for p in list_trade_profiles():
    if p.get("id") == profile_id:
      return p
  return None


def find_profile_by_label(label: str) -> dict | None:
  """Tìm profile theo tên hiển thị (không phân biệt hoa thường)."""
  key = (label or "").strip().casefold()
  if not key:
    return None
  for p in list_trade_profiles():
    if (p.get("label") or "").strip().casefold() == key:
      return p
  return None


def suggest_unique_profile_label(label: str) -> str:
  """Gợi ý tên không trùng — thêm (2), (3)…"""
  base = (label or "").strip() or "Profile"
  if not find_profile_by_label(base):
    return base
  n = 2
  while find_profile_by_label(f"{base} ({n})"):
    n += 1
  return f"{base} ({n})"


def load_active_profile_id() -> str:
  data = _read_json(ACTIVE_PATH)
  if isinstance(data, dict) and data.get("id"):
    return data["id"]
  return DEFAULT_PROFILE_ID_TP


def save_active_profile_id(profile_id: str):
  _write_json(ACTIVE_PATH, {"id": profile_id})


def _sync_tp_form_widgets(tp: dict):
  """Đồng bộ widget form sidebar với profile (gọi TRƯỚC khi render widget)."""
  from gui.kb_epoch_ui import cumulative_to_label
  from kb_profiles import DEFAULT_PROFILE_ID, is_legacy_kb_profile

  st.session_state["tp_train"] = int(tp.get("train_months", 6))
  st.session_state["tp_kb"] = bool(tp.get("use_kb", True))
  pid = tp.get("kb_profile") or DEFAULT_PROFILE_ID
  kb_label = _kb_profile_label_for_id(None if is_legacy_kb_profile(pid) else pid)
  if kb_label:
    st.session_state["tp_kb_pid"] = kb_label
  st.session_state["tp_oos_f"] = tp.get("oos_from") or ""
  st.session_state["tp_oos_t"] = tp.get("oos_to") or ""
  st.session_state["tp_spread"] = float(tp.get("spread_pips", DEFAULT_SPREAD_PIPS))
  st.session_state["tp_slip"] = float(tp.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS))
  st.session_state.pop("tp_kb_epoch", None)
  snap = _normalize_snapshot(tp.get("kb_snapshot"))
  if pid and tp.get("use_kb", True):
    label = cumulative_to_label(pid, snap)
    if label:
      st.session_state["tp_kb_epoch"] = label
  st.session_state["_tp_form_synced_id"] = tp.get("id")


def _invalidate_tp_form_sync():
  st.session_state.pop("_tp_form_synced_id", None)


def _kb_profile_choices(current_id: str | None = None) -> tuple[list[str], dict[str, str]]:
  """Nhãn hiển thị → ID profile bộ nhớ (chỉ giai đoạn era — bỏ Bộ nhớ chung cũ)."""
  from gui.components import _profile_label
  from kb_profiles import is_legacy_kb_profile, list_era_profiles

  if is_legacy_kb_profile(current_id):
    current_id = None
  profiles = list_era_profiles()
  options = {_profile_label(p): p["id"] for p in profiles}
  if current_id and current_id not in options.values():
    from gui.glossary import format_memory_profile
    orphan = f"{format_memory_profile(current_id)} (không còn trong kho)"
    options = {orphan: current_id, **options}
  return list(options.keys()), options


def _kb_profile_label_for_id(profile_id: str | None) -> str | None:
  labels, id_map = _kb_profile_choices(profile_id)
  if not labels:
    return None
  for label, pid in id_map.items():
    if pid == profile_id:
      return label
  return labels[0]


def format_trade_profile_label(tp: dict) -> str:
  """Tên ngắn cho dropdown — luôn theo quy ước thống nhất."""
  from gui.glossary import build_trade_profile_label
  if tp.get("label_custom"):
    return tp["label"]
  return build_trade_profile_label(tp)


def format_trade_profile_oneline(tp: dict) -> str:
  """Một dòng gọn cho header / card."""
  from gui.glossary import format_profile_oneline
  return format_profile_oneline(tp)


def get_profile_run_params() -> dict:
  """Tham số chạy backtest / paper — luôn lấy từ profile active."""
  tp = get_active_trade_profile()
  return {
    "train_months": int(tp.get("train_months", 6)),
    "use_learning": bool(tp.get("use_kb", True)),
    "use_kb": bool(tp.get("use_kb", True)),
    "kb_profile": tp.get("kb_profile") or "default",
    "kb_snapshot": _normalize_snapshot(tp.get("kb_snapshot")),
    "oos_from": tp.get("oos_from"),
    "oos_to": tp.get("oos_to"),
    "spread_pips": float(tp.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(tp.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
  }


def render_profile_card(*, show_hint: bool = True, container=None):
  """Hiển thị profile đang dùng — read-only trên các trang con."""
  container = container or st
  tp = get_active_trade_profile()
  note = f" · _{tp['strategy_note']}_" if tp.get("strategy_note") else ""
  hint = " · _Đổi ở sidebar trái._" if show_hint else ""
  container.info(f"📋 {format_trade_profile_oneline(tp)}{note}{hint}")


# Preset nhanh khi chỉnh profile (không đổi profile đang chọn — chỉ ghi đè field)
QUICK_SETUPS = [
  ("Mặc định tốt nhất (6T · Giai đoạn 2024)", {
    "train_months": 6, "use_kb": True, "kb_profile": "era_2024", "kb_snapshot": 3,
    "oos_from": "2025-01-01", "oos_to": "2026-12-31",
    "spread_pips": 1.0, "slippage_pips": 0.3,
    "strategy_note": "crossover_mut (pre-v4 best, ~+99R train window compare)",
  }),
  ("Không dùng bộ nhớ", {
    "train_months": 6, "use_kb": False, "kb_profile": None, "kb_snapshot": None,
    "oos_from": "2025-01-01", "oos_to": "2026-12-31",
  }),
  ("Học ngắn 3 tháng", {"train_months": 3}),
]


def format_trade_profile_summary(tp: dict) -> str:
  line = format_trade_profile_oneline(tp)
  if tp.get("backtest_total_r") is not None:
    line += f" · Backtest **{tp['backtest_total_r']:+.2f}R**"
  return line


def _sync_profile_label(tp: dict) -> dict:
  """Cập nhật label lưu file theo quy ước mới (trừ tên tùy chỉnh)."""
  if not tp.get("label_custom"):
    tp["label"] = format_trade_profile_label(tp)
  return tp


def _enrich_from_kb_profile(tp: dict) -> dict:
  out = dict(tp)
  p = get_profile(out.get("kb_profile") or DEFAULT_PROFILE_ID)
  if p:
    if p.get("trained_from"):
      out["learn_from"] = p["trained_from"]
    if p.get("trained_to"):
      out["learn_until"] = p["trained_to"]
  return out


def get_active_trade_profile(*, force_reload: bool = False) -> dict:
  if force_reload:
    st.session_state.pop("active_trade_profile", None)
  if "active_trade_profile" in st.session_state:
    return st.session_state["active_trade_profile"]
  pid = load_active_profile_id()
  tp = dict(get_profile_by_id(pid) or DEFAULT_TRADE_PROFILE)
  tp["kb_snapshot"] = _normalize_snapshot(tp.get("kb_snapshot"))
  tp = _enrich_from_kb_profile(tp)
  st.session_state["active_trade_profile"] = tp
  return tp


def migrate_trade_profile_labels():
  """Đồng bộ tên profile đã lưu với quy ước mới."""
  store = load_profiles_store()
  changed = False
  for i, p in enumerate(store["profiles"]):
    if p.get("label_custom"):
      continue
    new_label = format_trade_profile_label(p)
    if p.get("label") != new_label:
      store["profiles"][i] = {**p, "label": new_label}
      changed = True
  if changed:
    save_profiles_store(store)
    st.session_state.pop("active_trade_profile", None)


def ensure_trade_profiles_loaded():
  load_profiles_store()
  migrate_trade_profile_labels()
  if not ACTIVE_PATH.exists():
    save_active_profile_id(DEFAULT_PROFILE_ID_TP)
  get_active_trade_profile()


def set_active_trade_profile(profile_id: str | None = None, **fields) -> dict:
  nullable = {"kb_profile", "kb_snapshot", "strategy_note", "grid_run_id", "backtest_total_r"}
  if profile_id:
    tp = dict(get_profile_by_id(profile_id) or DEFAULT_TRADE_PROFILE)
    _invalidate_tp_form_sync()
  else:
    tp = dict(get_active_trade_profile())

  for k, v in fields.items():
    if k in nullable or v is not None:
      tp[k] = v

  if "kb_snapshot" in tp:
    tp["kb_snapshot"] = _normalize_snapshot(tp["kb_snapshot"])

  tp = _enrich_from_kb_profile(tp)
  if not tp.get("label") or not tp.get("label_custom"):
    tp = _sync_profile_label(tp)

  stored = _profile_for_store(tp)
  store = load_profiles_store()
  updated = False
  for i, p in enumerate(store["profiles"]):
    if p.get("id") == stored.get("id"):
      store["profiles"][i] = stored
      updated = True
      break
  if not updated:
    store["profiles"].append(stored)
  save_profiles_store(store)

  save_active_profile_id(stored["id"])
  st.session_state.pop("active_trade_profile", None)
  st.session_state.pop("backtest_report", None)
  tp = _enrich_from_kb_profile(dict(stored))
  st.session_state["active_trade_profile"] = tp
  _invalidate_tp_form_sync()

  from gui.workspace import save_workspace_file, sync_workspace_pickers
  ws = trade_profile_to_workspace(tp)
  st.session_state["active_workspace"] = ws
  save_workspace_file(ws)
  sync_workspace_pickers(ws)
  return tp


def create_trade_profile(
  label: str,
  *,
  from_profile: dict | None = None,
  allow_duplicate_label: bool = False,
  **fields,
) -> dict:
  label = (label or "").strip()
  if not label:
    raise ValueError("Tên profile không được để trống.")
  existing = find_profile_by_label(label)
  if existing and not allow_duplicate_label:
    hint = suggest_unique_profile_label(label)
    raise ValueError(
      f"Đã có profile tên «{label}». Chọn tên khác (gợi ý: «{hint}»)."
    )

  base = _profile_for_store(dict(from_profile or get_active_trade_profile()))
  base.pop("is_default", None)
  tp = {
    **base,
    "id": _new_id(label),
    "label": label,
    "label_custom": True,
    "is_default": False,
    **fields,
  }
  if "kb_snapshot" in tp:
    tp["kb_snapshot"] = _normalize_snapshot(tp["kb_snapshot"])
  store = load_profiles_store()
  store["profiles"].append(_profile_for_store(tp))
  save_profiles_store(store)
  return _enrich_from_kb_profile(tp)


def delete_trade_profile(profile_id: str, *, cleanup: bool = True) -> dict:
  """
  Xóa trade profile và (tuỳ chọn) dữ liệu backtest liên quan.
  Trả về {ok, deleted, error, switched_to_default}.
  """
  result: dict = {
    "ok": False,
    "profile_id": profile_id,
    "deleted": [],
    "error": None,
    "switched_to_default": False,
  }
  if profile_id == DEFAULT_PROFILE_ID_TP:
    result["error"] = "Không thể xóa profile mặc định."
    return result

  tp = get_profile_by_id(profile_id)
  if not tp:
    result["error"] = "Profile không tồn tại."
    return result

  if cleanup:
    result["deleted"] = _cleanup_trade_profile_data(tp)

  was_active = load_active_profile_id() == profile_id

  store = load_profiles_store()
  before = len(store["profiles"])
  store["profiles"] = [p for p in store["profiles"] if p.get("id") != profile_id]
  if len(store["profiles"]) == before:
    result["error"] = "Profile không tồn tại trong kho."
    return result
  save_profiles_store(store)

  if was_active:
    save_active_profile_id(DEFAULT_PROFILE_ID_TP)
    result["switched_to_default"] = True
  _clear_session_for_profile(tp, was_active)

  result["ok"] = True
  return result


def report_belongs_to_trade_profile(report: dict, tp: dict) -> bool:
  """Báo cáo backtest có thuộc trade profile này không."""
  cfg = report.get("config") or {}
  pid = tp.get("id")
  if pid and cfg.get("trade_profile_id"):
    return cfg["trade_profile_id"] == pid
  from gui.workspace import report_matches_workspace
  return report_matches_workspace(report, trade_profile_to_workspace(tp))


def preview_trade_profile_cleanup(profile_id: str) -> dict:
  """Liệt kê file/dữ liệu sẽ bị xóa (không xóa thật)."""
  tp = get_profile_by_id(profile_id)
  if not tp:
    return {"items": [], "summary": "Không tìm thấy profile.", "profile_label": ""}
  items = _collect_profile_artifacts(tp)
  return {
    "items": items,
    "summary": _format_cleanup_summary(items),
    "profile_label": format_trade_profile_label(tp),
  }


def _format_cleanup_summary(items: list[dict]) -> str:
  if not items:
    return "Không có dữ liệu backtest đã lưu cho profile này."
  parts = []
  for it in items:
    n = it.get("count", 1)
    parts.append(f"{it['label']}" + (f" ({n})" if n > 1 else ""))
  return " · ".join(parts)


def _collect_profile_artifacts(tp: dict) -> list[dict]:
  """Danh sách artifact liên quan profile (để preview / xóa)."""
  from gui.workspace import workspace_report_path

  items: list[dict] = []
  ws = trade_profile_to_workspace(tp)
  ws_path = workspace_report_path(ws)
  if ws_path.exists():
    items.append({"kind": "workspace_report", "path": str(ws_path), "label": "Backtest profile (cache)"})

  main = REPORT_DIR / "backtest_report.json"
  main_report = _read_json(main)
  if main_report and report_belongs_to_trade_profile(main_report, tp):
    items.append({"kind": "global_backtest", "path": str(main), "label": "Backtest chung (backtest_report.json)"})

  try:
    from gui.report_store import list_reports, load_report
    archived = []
    for entry in list_reports():
      rep = load_report(entry["id"])
      if rep and report_belongs_to_trade_profile(rep, tp):
        archived.append(entry["id"])
    if archived:
      items.append({
        "kind": "archived_reports",
        "ids": archived,
        "count": len(archived),
        "label": "Báo cáo trong kho so sánh",
      })
  except Exception:
    pass

  grid_run_id = tp.get("grid_run_id")
  if grid_run_id:
    grid_path = REPORT_DIR / "grid_search" / f"{grid_run_id}.json"
    if grid_path.exists():
      items.append({"kind": "grid_run", "path": str(grid_path), "label": f"Grid run `{grid_run_id}`"})

  return items


def _cleanup_trade_profile_data(tp: dict) -> list[str]:
  """Xóa file backtest / báo cáo gắn với profile. Trả về danh sách mô tả đã xóa."""
  deleted: list[str] = []
  for item in _collect_profile_artifacts(tp):
    kind = item.get("kind")
    if kind == "workspace_report" or kind == "global_backtest" or kind == "grid_run":
      path = Path(item["path"])
      if path.exists():
        path.unlink()
        deleted.append(item["label"])
    elif kind == "archived_reports":
      from gui.report_store import delete_report
      for rid in item.get("ids") or []:
        if delete_report(rid):
          deleted.append(f"Báo cáo `{rid}`")
  return deleted


def _clear_session_for_profile(tp: dict, was_active: bool):
  """Dọn session Streamlit khi xóa profile."""
  st.session_state.pop("active_trade_profile", None)
  st.session_state.pop("_tp_form_synced_id", None)
  if was_active:
    st.session_state.pop("backtest_report", None)
    st.session_state.pop("lab_kb_compare", None)
    st.session_state.pop("_synced_job_id", None)
    return
  report = st.session_state.get("backtest_report")
  if report and report_belongs_to_trade_profile(report, tp):
    st.session_state.pop("backtest_report", None)
    st.session_state.pop("lab_kb_compare", None)


def profile_from_grid_row(row: dict, *, run_id: str | None = None, label: str | None = None) -> dict:
  tm = row.get("train_months", 6)
  kb = row.get("kb_profile") or "era_2024"
  ep = _normalize_snapshot(row.get("kb_snapshot"))
  from gui.glossary import build_trade_profile_label
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
  return {
    "train_months": tm,
    "use_kb": bool(row.get("use_kb", True)),
    "kb_profile": kb if row.get("use_kb") else None,
    "kb_snapshot": ep,
    "oos_from": row.get("oos_from"),
    "oos_to": row.get("oos_to"),
    "spread_pips": row.get("spread_pips", DEFAULT_SPREAD_PIPS),
    "slippage_pips": row.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    "backtest_total_r": row.get("total_r"),
    "source": "grid_search",
    "grid_run_id": run_id,
    "label": auto_label,
    "strategy_note": get_active_trade_profile().get("strategy_note"),
  }


def apply_grid_row_to_active(row: dict, *, run_id: str | None = None) -> dict:
  fields = profile_from_grid_row(row, run_id=run_id)
  label = fields.pop("label")
  return set_active_trade_profile(label=label, **fields)


def apply_grid_row_as_new_profile(row: dict, *, run_id: str | None = None, label: str | None = None) -> dict:
  fields = profile_from_grid_row(row, run_id=run_id, label=label)
  label = fields.pop("label")
  tp = create_trade_profile(label, **fields)
  return set_active_trade_profile(profile_id=tp["id"])


def trade_profile_to_workspace(tp: dict | None = None) -> dict:
  """Map trade profile → workspace dict (tương thích code cũ)."""
  tp = tp or get_active_trade_profile()
  return {
    "label": format_trade_profile_label(tp),
    "kb_profile": tp.get("kb_profile") or DEFAULT_PROFILE_ID,
    "kb_snapshot": _normalize_snapshot(tp.get("kb_snapshot")),
    "oos_from": tp.get("oos_from"),
    "oos_to": tp.get("oos_to"),
    "use_learning": bool(tp.get("use_kb", True)),
    "train_months": tp.get("train_months", 6),
    "spread_pips": tp.get("spread_pips", DEFAULT_SPREAD_PIPS),
    "slippage_pips": tp.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    "strategy_note": tp.get("strategy_note"),
    "learn_from": tp.get("learn_from"),
    "learn_until": tp.get("learn_until"),
    "trade_profile_id": tp.get("id"),
  }


def workspace_fields_to_trade_profile(**fields) -> dict:
  mapping = {
    "use_learning": "use_kb",
    "use_kb": "use_kb",
  }
  out = {}
  for k, v in fields.items():
    if v is None:
      continue
    out[mapping.get(k, k)] = v
  return out


def render_sidebar_trade_profiles():
  """Sidebar — chọn profile + chỉnh gọn."""
  from gui.glossary import HELP

  st.sidebar.markdown("**Cấu hình giao dịch**")
  st.sidebar.caption("Gom mọi tham số backtest & paper vào một profile.")
  profiles = list_trade_profiles()
  active = get_active_trade_profile()
  active_id = active.get("id")

  labels = [format_trade_profile_label(p) for p in profiles]
  id_by_label = {format_trade_profile_label(p): p["id"] for p in profiles}
  current_label = format_trade_profile_label(active)
  idx = labels.index(current_label) if current_label in labels else 0

  pick_label = st.sidebar.selectbox(
    "Profile",
    labels,
    index=idx,
    key="tp_sidebar_pick",
    label_visibility="collapsed",
  )
  if id_by_label.get(pick_label) != active_id:
    set_active_trade_profile(profile_id=id_by_label[pick_label])
    st.session_state.pop("backtest_report", None)
    st.rerun()

  active = get_active_trade_profile()
  st.sidebar.caption(format_trade_profile_oneline(active))

  if st.session_state.get("_tp_form_synced_id") != active_id:
    _sync_tp_form_widgets(active)

  with st.sidebar.expander("Chỉnh / tạo profile", expanded=False):
    st.caption("Preset nhanh:")
    for i, (title, fields) in enumerate(QUICK_SETUPS):
      if st.button(title, key=f"tp_quick_{i}", use_container_width=True):
        set_active_trade_profile(**fields, source="preset")
        st.session_state.pop("backtest_report", None)
        st.toast(f"Đã áp dụng: {title}")
        st.rerun()

    st.divider()
    new_label = st.text_input("Tên profile mới", key="tp_new_label", placeholder="VD: Paper 3m")
    if st.button("＋ Tạo bản sao", key="tp_clone", use_container_width=True):
      name = new_label.strip() or f"{format_trade_profile_label(active)} (copy)"
      try:
        tp = create_trade_profile(name, from_profile=active)
      except ValueError as e:
        st.error(str(e))
      else:
        set_active_trade_profile(profile_id=tp["id"])
        st.toast(f"Đã tạo `{name}`")
        st.rerun()

    with st.form("tp_edit_form", clear_on_submit=False):
      st.markdown("**Tùy chỉnh profile**")
      train_opts = [2, 3, 4, 6, 12]
      train_m = st.selectbox(
        "Cửa sổ học (tháng)", train_opts, key="tp_train",
        help=HELP["train_months"],
      )
      use_kb = st.checkbox("Dùng bộ nhớ kinh nghiệm", key="tp_kb", help=HELP["kb_on"])
      kb_labels, kb_id_map = _kb_profile_choices(active.get("kb_profile"))
      if active.get("kb_profile") == "default" or (
        active.get("use_kb") and active.get("kb_profile") in (None, "", "default")
      ):
        st.caption(
          "⚠️ Profile đang dùng **Bộ nhớ chung** (cũ) — nên chọn **Giai đoạn 20xx** bên dưới."
        )
      if not kb_labels:
        st.caption("Chưa có giai đoạn bộ nhớ — tạo ở **Bộ nhớ & học**.")
        kb_pid = None
      else:
        kb_label = st.selectbox(
          "Giai đoạn bộ nhớ",
          kb_labels,
          key="tp_kb_pid",
          help="Chọn giai đoạn đã học — VD: Giai đoạn 2024, Bộ nhớ chung.",
          disabled=not use_kb,
        )
        kb_pid = kb_id_map.get(kb_label) if use_kb else None
        if use_kb and kb_pid:
          p = get_profile(kb_pid)
          if p:
            st.caption(
              f"Học: **{p.get('trained_from') or '?'} → {p.get('trained_to') or '?'}** · "
              f"{p.get('epochs', 0)} vòng học"
            )
      oos_f = st.text_input("Kiểm chứng từ", key="tp_oos_f", help=HELP["oos"])
      oos_t = st.text_input("Kiểm chứng đến", key="tp_oos_t", help=HELP["oos"])
      c1, c2 = st.columns(2)
      with c1:
        spread = st.number_input("Chênh lệch (pip)", 0.0, 3.0, step=0.1, key="tp_spread", help=HELP["spread"])
      with c2:
        slip = st.number_input("Trượt giá (pip)", 0.0, 2.0, step=0.1, key="tp_slip", help=HELP["slippage"])

      snap = None
      if use_kb and kb_pid:
        from gui.kb_epoch_ui import kb_epoch_picker
        snap = kb_epoch_picker("tp", kb_pid, show_table=False)

      submitted = st.form_submit_button("💾 Lưu profile", type="primary", use_container_width=True)

    if submitted:
      set_active_trade_profile(
        train_months=int(train_m),
        use_kb=bool(use_kb),
        kb_profile=kb_pid if use_kb else None,
        kb_snapshot=snap if use_kb else None,
        oos_from=oos_f.strip() or None,
        oos_to=oos_t.strip() or None,
        spread_pips=float(spread),
        slippage_pips=float(slip),
        source="manual",
      )
      st.session_state.pop("backtest_report", None)
      st.toast("Đã lưu cấu hình giao dịch")
      st.rerun()

    if st.button("↺ Mặc định", key="tp_reset_default", use_container_width=True):
      set_active_trade_profile(profile_id=DEFAULT_PROFILE_ID_TP)
      st.rerun()

    st.divider()
    deletable = [p for p in profiles if not p.get("is_default")]
    if deletable:
      st.markdown("**Xóa profile**")
      del_map = {format_trade_profile_label(p): p["id"] for p in deletable}
      del_label = st.selectbox(
        "Chọn profile cần xóa",
        list(del_map.keys()),
        key="tp_del_pick",
      )
      del_id = del_map[del_label]
      preview = preview_trade_profile_cleanup(del_id)
      if preview.get("items"):
        st.caption(f"Sẽ xóa: **{preview['summary']}**")
      else:
        st.caption("Chỉ xóa cấu hình — chưa có backtest lưu riêng cho profile này.")
      confirm = st.checkbox(
        "Tôi hiểu — xóa không khôi phục được",
        key="tp_del_confirm",
      )
      if st.button(
        "🗑 Xóa profile & dữ liệu liên quan",
        type="secondary",
        use_container_width=True,
        key="tp_delete",
        disabled=not confirm,
      ):
        outcome = delete_trade_profile(del_id, cleanup=True)
        if outcome.get("ok"):
          n = len(outcome.get("deleted") or [])
          msg = f"Đã xóa profile"
          if n:
            msg += f" + {n} mục dữ liệu"
          if outcome.get("switched_to_default"):
            msg += " · chuyển về profile mặc định"
          st.toast(msg)
          _invalidate_tp_form_sync()
          st.rerun()
        else:
          st.error(outcome.get("error") or "Không xóa được profile.")
