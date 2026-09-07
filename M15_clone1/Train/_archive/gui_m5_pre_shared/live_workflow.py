"""Quy trình live — huấn luyện KB → Grid → Trade Model → Compare → Live Bridge."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

WORKFLOW_PATH = REPORT_DIR / "live_workflow.json"
COMPARE_ROOT = REPORT_DIR / "compare_trade"

_WORKFLOW_STEPS_STATIC: tuple[dict, ...] = (
  {
    "id": 1,
    "key": "train_kb",
    "title": "Huấn luyện bộ nhớ",
    "short": "① Học KB",
    "nav_page": "learning",
    "learning_tab": "train_kb",
  },
  {
    "id": 2,
    "key": "grid",
    "title": "Grid Search",
    "short": "② Grid",
    "nav_page": "learning",
    "learning_tab": "grid",
  },
  {
    "id": 3,
    "key": "pick",
    "title": "Tạo Trade Model",
    "short": "③ Model",
    "subtitle": "Lưu combo đã chọn",
    "detail": (
      "Tạo **Trade Model** từ Grid — dùng để phân tích (Trade Models) "
      "và chọn vào roster **MT5 Bridge**."
    ),
    "nav_page": "models",
    "learning_tab": None,
  },
  {
    "id": 4,
    "key": "compare",
    "title": "Compare Trade",
    "short": "④ Compare",
    "subtitle": "So nhiều model trên lịch sử",
    "detail": "Chạy **Compare Trade** (không EA) để đối chiếu model trước khi Live.",
    "nav_page": "compare_trade",
    "learning_tab": None,
  },
  {
    "id": 5,
    "key": "live",
    "title": "Live Bridge",
    "short": "⑤ Live",
    "subtitle": "Roster trên MT5 Bridge",
    "detail": "Chọn 1–5 model trên **MT5 Bridge**, Start Live · theo dõi Parity / Health.",
    "nav_page": "mt5_bridge",
    "learning_tab": None,
  },
)


def workflow_steps() -> tuple[dict, ...]:
  """Bước quy trình — subtitle/detail bước 1–2 lấy từ Cài đặt (không hardcode era)."""
  from gui.app_settings import load_settings, resolve_learning_eras
  from gui.grid_search_engine import expected_grid_count_from_settings

  settings = load_settings()
  eras = resolve_learning_eras(settings)
  loops = int(settings.get("learning_loops") or 4)
  n_eras = len(eras)
  expected = expected_grid_count_from_settings(settings)

  if eras:
    era_names = ", ".join(f"**{e['kb_profile']}**" for e in eras)
    era_labels = ", ".join(e["label"] for e in eras)
    train_subtitle = f"{n_eras} giai đoạn · {loops} vòng"
    train_detail = (
      f"Học {era_names} ({era_labels}) theo **Cài đặt** — "
      f"**bắt buộc trước Grid Search** ({loops} vòng/giai đoạn)."
    )
  else:
    train_subtitle = f"Chưa chọn giai đoạn · {loops} vòng"
    train_detail = (
      "Chọn giai đoạn học trong **Cài đặt**, rồi huấn luyện KB — "
      "**bắt buộc trước Grid Search**."
    )

  grid_subtitle = (
    f"{expected} combo theo Cài đặt" if expected else "Combo theo Cài đặt"
  )
  grid_detail = (
    "Chạy Grid Search sau khi bộ nhớ đã học đủ theo Cài đặt — chọn combo tốt nhất."
  )

  out: list[dict] = []
  for spec in _WORKFLOW_STEPS_STATIC:
    row = dict(spec)
    if row["id"] == 1:
      row["subtitle"] = train_subtitle
      row["detail"] = train_detail
    elif row["id"] == 2:
      row["subtitle"] = grid_subtitle
      row["detail"] = grid_detail
    out.append(row)
  return tuple(out)


def __getattr__(name: str):
  # ``from gui.live_workflow import WORKFLOW_STEPS`` resolves via this hook.
  if name == "WORKFLOW_STEPS":
    return workflow_steps()
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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


def load_workflow_state() -> dict:
  data = _read_json(WORKFLOW_PATH)
  if not isinstance(data, dict):
    data = {}
  data.setdefault("chosen_report_id", None)
  data.setdefault("chosen_profile_id", None)
  data.setdefault("paper_started_at", None)  # legacy field; unused
  data.setdefault("compare_started_at", None)
  data.setdefault("live_notes", "")
  data.setdefault("manual", {})
  return data


def save_workflow_state(state: dict):
  _write_json(WORKFLOW_PATH, state)


def stability_score(summary: dict) -> float:
  """Điểm ổn định — ưu tiên R/PF cao, sụt giảm thấp."""
  r = float(summary.get("total_r") or 0)
  dd = float(summary.get("max_drawdown_r") or 0)
  pf = float(summary.get("profit_factor") or 0)
  wr = float(summary.get("win_rate_pct") or 0)
  dd = max(dd, 0.5)
  base = (r * max(pf, 0.01)) / dd
  penalty = 0.0
  if r > 0 and dd > r * 0.35:
    penalty += (dd - r * 0.35) * 0.5
  if pf < 1.0:
    penalty += (1.0 - pf) * 5
  return round(base - penalty + min(wr, 55) * 0.05, 2)


def _report_entries():
  from gui.report_store import list_reports
  return list_reports()


def _split_reports(entries: list[dict]) -> tuple[list[dict], list[dict]]:
  off, on = [], []
  for e in entries:
    s = e.get("summary") or {}
    if s.get("kb_on"):
      on.append(e)
    else:
      off.append(e)
  return off, on


def rank_reports(entries: list[dict]) -> list[dict]:
  ranked = []
  for e in entries:
    s = dict(e.get("summary") or {})
    ranked.append({**e, "stability": stability_score(s)})
  ranked.sort(key=lambda x: x["stability"], reverse=True)
  return ranked


def apply_report_to_profile(report_id: str) -> dict:
  """Áp config từ báo cáo đã chọn → Trade Model."""
  from gui.report_store import load_report
  from gui.trade_model import create_trade_model

  report = load_report(report_id)
  if not report:
    return {"ok": False, "error": "Không tìm thấy báo cáo."}

  cfg = report.get("config") or {}
  o = report.get("overall_oos") or {}
  row = {
    "train_weeks": cfg.get("train_weeks"),
    "use_kb": bool(cfg.get("use_learning_kb")),
    "kb_profile": cfg.get("kb_profile"),
    "kb_snapshot": cfg.get("kb_snapshot"),
    "oos_from": cfg.get("oos_from"),
    "oos_to": cfg.get("oos_to"),
    "spread_pips": cfg.get("spread_pips"),
    "slippage_pips": cfg.get("slippage_pips"),
    "total_r": o.get("total_r"),
  }
  m = create_trade_model(row, label=f"Workflow {report_id}", report=report, set_active=True)

  state = load_workflow_state()
  state["chosen_report_id"] = report_id
  state["chosen_profile_id"] = m.get("id")
  save_workflow_state(state)
  return {"ok": True, "profile_id": m.get("id"), "label": m.get("label")}


def mark_paper_started():
  """Deprecated — Paper Monitor retired. No-op kept for old callers."""
  return


def mark_compare_started():
  state = load_workflow_state()
  if not state.get("compare_started_at"):
    state["compare_started_at"] = datetime.now(timezone.utc).isoformat()
    save_workflow_state(state)


def _has_compare_run() -> bool:
  latest = COMPARE_ROOT / "latest.json"
  if latest.exists():
    return True
  if not COMPARE_ROOT.is_dir():
    return False
  return any(p.is_dir() and (p / "run.json").exists() for p in COMPARE_ROOT.iterdir())


def _bridge_roster_ready() -> bool:
  try:
    from gui.trade_model import get_bridge_runtime_model_ids
    return bool(get_bridge_runtime_model_ids())
  except Exception:
    return False


_assess_cache: dict | None = None
_assess_cache_at: float = 0.0


def assess_workflow(*, force: bool = False) -> dict:
  """Trạng thái từng bước + gợi ý hành động (cache ~3s để tránh treo khi đổi trang)."""
  import time

  global _assess_cache, _assess_cache_at
  now = time.monotonic()
  if not force and _assess_cache is not None and (now - _assess_cache_at) < 3.0:
    return _assess_cache

  from gui.trade_model import get_active_trade_model
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run

  state = load_workflow_state()
  entries = _report_entries()
  r = grid_readiness()
  grid_data = load_latest_grid_run()
  has_grid = bool(grid_data and (grid_data.get("rows") or []))
  steps_spec = workflow_steps()

  step1_done = r["kb_complete"] or bool(state.get("manual", {}).get("1"))
  step2_done = has_grid or bool(state.get("manual", {}).get("2"))
  step3_done = bool(state.get("chosen_report_id")) or bool(state.get("manual", {}).get("3"))
  step4_done = bool(state.get("manual", {}).get("4")) or _has_compare_run()
  step5_done = bool(state.get("manual", {}).get("5")) or _bridge_roster_ready()

  ranked = rank_reports(entries)
  best = ranked[0] if ranked else None

  tm = get_active_trade_model()
  if tm:
    step3_done = True
  if state.get("chosen_profile_id") and tm and tm.get("id") == state["chosen_profile_id"]:
    step3_done = True

  steps = {}
  for spec in steps_spec:
    sid = spec["id"]
    if sid == 1:
      done = step1_done
      missing = len(r.get("missing_profiles") or [])
      under = len(r.get("under_trained") or [])
      if done:
        progress = f"{r['ready_combos']}/{r['expected_combos']} combo sẵn sàng"
      elif under or (r["ready_combos"] > 0 and not done):
        parts = []
        if under:
          parts.append(f"{under} giai đoạn chưa đủ vòng")
        if missing:
          parts.append(f"{missing} giai đoạn chưa học")
        progress = (
          f"{r['ready_combos']}/{r['expected_combos']} combo — "
          + ("; ".join(parts) if parts else "đang học KB")
        )
      elif missing:
        progress = f"Còn {missing} giai đoạn chưa học — mở Huấn luyện bộ nhớ"
      else:
        progress = "Chưa đủ vòng học theo Cài đặt"
    elif sid == 2:
      done = step2_done
      n = len((grid_data or {}).get("rows") or [])
      progress = f"{n} combo đã chạy" if n else "Chưa chạy Grid Search"
    elif sid == 3:
      done = step3_done
      if tm:
        progress = f"Trade model: {tm.get('label', tm.get('id', '—'))[:50]}"
      elif state.get("chosen_report_id"):
        chosen = next((e for e in entries if e["id"] == state["chosen_report_id"]), None)
        s = (chosen or {}).get("summary") or {}
        progress = f"Đã chọn · {s.get('total_r', '—')}R · DD {s.get('max_drawdown_r', '—')}R"
      elif has_grid:
        progress = "Chọn combo tốt → Tạo Trade Model"
      else:
        progress = "Chưa có kết quả Grid Search"
    elif sid == 4:
      done = step4_done
      if _has_compare_run():
        progress = "Đã có Compare Trade run"
      elif state.get("compare_started_at"):
        progress = f"Compare từ {state['compare_started_at'][:10]}"
      else:
        progress = "Chưa chạy Compare Trade"
    else:
      done = step5_done
      if _bridge_roster_ready():
        from gui.trade_model import get_bridge_runtime_model_ids
        n = len(get_bridge_runtime_model_ids())
        progress = state.get("live_notes") or f"Bridge roster · {n} model"
      else:
        progress = state.get("live_notes") or "Chọn roster trên MT5 Bridge rồi Start"

    steps[sid] = {
      "done": done,
      "progress": progress,
      "spec": spec,
    }

  current_step = next((s["id"] for s in steps_spec if not steps[s["id"]]["done"]), 5)
  if all(steps[s["id"]]["done"] for s in steps_spec):
    current_step = 5

  result = {
    "steps": steps,
    "current_step": current_step,
    "state": state,
    "ranked_reports": ranked[:8],
    "grid_ready": r["kb_complete"],
    "grid_rows": len((grid_data or {}).get("rows") or []),
    "best_report": best,
  }
  _assess_cache = result
  _assess_cache_at = now
  return result
