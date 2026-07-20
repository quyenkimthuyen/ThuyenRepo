"""Quy trình live — huấn luyện KB → Grid → Trade Model → paper → live."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

WORKFLOW_PATH = REPORT_DIR / "live_workflow.json"

WORKFLOW_STEPS: tuple[dict, ...] = (
  {
    "id": 1,
    "key": "train_kb",
    "title": "Huấn luyện bộ nhớ",
    "short": "① Học KB",
    "subtitle": "3 giai đoạn · 4 vòng",
    "detail": "Học **era_2022_2025**, **era_2023_2025**, **era_2024_2025** (theo Cài đặt) — **bắt buộc trước Grid Search**.",
    "nav_page": "learning",
    "learning_tab": "train_kb",
  },
  {
    "id": 2,
    "key": "grid",
    "title": "Grid Search",
    "short": "② Grid",
    "subtitle": "36 combo theo Cài đặt",
    "detail": "Chạy Grid Search sau khi bộ nhớ đã học — chọn combo tốt nhất.",
    "nav_page": "learning",
    "learning_tab": "grid",
  },
  {
    "id": 3,
    "key": "pick",
    "title": "Tạo Trade Model",
    "short": "③ Model",
    "subtitle": "Lưu combo đã chọn",
    "detail": "Tạo **Trade Model** từ kết quả Grid Search — dùng cho paper & phân tích.",
    "nav_page": "learning",
    "learning_tab": "models",
  },
  {
    "id": 4,
    "key": "paper",
    "title": "Paper vài tuần",
    "short": "④ Paper",
    "subtitle": "Đúng Trade Model đã chọn",
    "detail": "Giám sát paper ≥3 tuần — so với backtest.",
    "nav_page": "paper",
    "learning_tab": None,
  },
  {
    "id": 5,
    "key": "live",
    "title": "Live nhỏ → scale",
    "short": "⑤ Live",
    "subtitle": "Chỉ khi paper khớp backtest",
    "detail": "Micro lot, theo dõi chênh lệch thực tế trước khi tăng size.",
    "nav_page": "paper",
    "learning_tab": None,
  },
)


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
  data.setdefault("paper_started_at", None)
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
    "train_months": cfg.get("train_months"),
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
  state = load_workflow_state()
  if not state.get("paper_started_at"):
    state["paper_started_at"] = datetime.now(timezone.utc).isoformat()
    save_workflow_state(state)


def assess_workflow() -> dict:
  """Trạng thái từng bước + gợi ý hành động."""
  from gui.services import load_backtest_report
  from gui.trade_model import get_active_trade_model
  from gui.workspace import report_matches_workspace

  from gui.grid_search_engine import grid_readiness, load_latest_grid_run

  state = load_workflow_state()
  entries = _report_entries()
  r = grid_readiness()
  grid_data = load_latest_grid_run()
  has_grid = bool(grid_data and (grid_data.get("rows") or []))

  step1_done = r["kb_complete"] or bool(state.get("manual", {}).get("1"))
  step2_done = has_grid or bool(state.get("manual", {}).get("2"))
  step3_done = bool(state.get("chosen_report_id")) or bool(state.get("manual", {}).get("3"))
  step4_done = bool(state.get("manual", {}).get("4"))
  step5_done = bool(state.get("manual", {}).get("5"))

  paper_state = _read_json(REPORT_DIR / "paper_monitor_state.json")
  if state.get("paper_started_at") and paper_state:
    step4_done = step4_done or bool(state.get("manual", {}).get("4"))

  ranked = rank_reports(entries)
  best = ranked[0] if ranked else None

  tm = get_active_trade_model()
  if tm:
    step3_done = True
  if state.get("chosen_profile_id") and tm and tm.get("id") == state["chosen_profile_id"]:
    step3_done = True

  steps = {}
  for spec in WORKFLOW_STEPS:
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
      if state.get("paper_started_at"):
        progress = f"Paper từ {state['paper_started_at'][:10]}"
      elif paper_state:
        progress = "Paper đang chạy — đánh dấu khi đủ ≥3 tuần"
      else:
        progress = "Chưa bắt đầu paper"
    else:
      done = step5_done
      progress = state.get("live_notes") or "Chỉ khi paper khớp backtest"

    steps[sid] = {
      "done": done,
      "progress": progress,
      "spec": spec,
    }

  current_step = next((s["id"] for s in WORKFLOW_STEPS if not steps[s["id"]]["done"]), 5)
  if all(steps[s["id"]]["done"] for s in WORKFLOW_STEPS):
    current_step = 5

  return {
    "steps": steps,
    "current_step": current_step,
    "state": state,
    "ranked_reports": ranked[:8],
    "grid_ready": r["kb_complete"],
    "grid_rows": len((grid_data or {}).get("rows") or []),
    "best_report": best,
  }
