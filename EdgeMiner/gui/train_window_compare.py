"""So sánh train window (3 / 6 / 12 tháng) — KB ON vs OFF."""
from __future__ import annotations

import json
from pathlib import Path

from run_backtest import REPORT_DIR

COMPARE_PATH = REPORT_DIR / "train_window_compare.json"

TRAIN_MONTHS_OPTIONS = [3, 6, 12]

DEFAULT_SPEC = {
  "oos_from": "2025-01-01",
  "oos_to": "2026-12-31",
  "kb_profile": "era_2024",
}


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


def result_key(train_months: int, use_kb: bool) -> str:
  return f"{train_months}m_{'kb_on' if use_kb else 'kb_off'}"


def load_train_window_cache() -> dict | None:
  return _read_json(COMPARE_PATH)


def save_train_window_cache(
  reports: dict[str, dict],
  *,
  oos_from: str,
  oos_to: str,
  kb_profile: str,
  train_months_list: list[int],
):
  from datetime import datetime, timezone
  payload = {
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "oos_from": oos_from,
    "oos_to": oos_to,
    "kb_profile": kb_profile,
    "train_months_list": train_months_list,
    "reports": reports,
  }
  _write_json(COMPARE_PATH, payload)


def run_train_window_matrix(
  train_months_list: list[int] | None = None,
  *,
  oos_from: str | None = None,
  oos_to: str | None = None,
  kb_profile: str | None = None,
  on_progress=None,
) -> dict[str, dict]:
  """Chạy grid: mỗi train_months × KB ON/OFF."""
  from gui.services import execute_backtest

  train_months_list = train_months_list or TRAIN_MONTHS_OPTIONS
  oos_from = oos_from or DEFAULT_SPEC["oos_from"]
  oos_to = oos_to or DEFAULT_SPEC["oos_to"]
  kb_profile = kb_profile or DEFAULT_SPEC["kb_profile"]

  jobs = []
  for tm in train_months_list:
    jobs.append((tm, False))
    jobs.append((tm, True))

  reports: dict[str, dict] = {}
  for i, (tm, use_kb) in enumerate(jobs):
    label = f"Train {tm}m · {'KB ON' if use_kb else 'KB OFF'}"
    if on_progress:
      on_progress(i + 1, len(jobs), label)
    key = result_key(tm, use_kb)
    reports[key] = execute_backtest(
      use_learning=use_kb,
      train_months=tm,
      kb_profile=kb_profile if use_kb else "default",
      oos_from=oos_from,
      oos_to=oos_to,
      archive=True,
      archive_label=f"{label} · {kb_profile if use_kb else '-'} · OOS {oos_from}→{oos_to}",
      sync_workspace=False,
    )

  save_train_window_cache(
    reports,
    oos_from=oos_from,
    oos_to=oos_to,
    kb_profile=kb_profile,
    train_months_list=train_months_list,
  )
  return reports


def metrics_table(reports: dict[str, dict], train_months_list: list[int]) -> list[dict]:
  rows = []
  for tm in train_months_list:
    off = reports.get(result_key(tm, False))
    on = reports.get(result_key(tm, True))
    o_off = (off or {}).get("overall_oos", {})
    o_on = (on or {}).get("overall_oos", {})
    rows.append({
      "Train (tháng)": tm,
      "KB OFF · Lệnh": o_off.get("n_trades", "—"),
      "KB OFF · WR%": o_off.get("win_rate_pct", "—"),
      "KB OFF · R": o_off.get("total_r", "—"),
      "KB OFF · DD": o_off.get("max_drawdown_r", "—"),
      "KB ON · Lệnh": o_on.get("n_trades", "—"),
      "KB ON · WR%": o_on.get("win_rate_pct", "—"),
      "KB ON · R": o_on.get("total_r", "—"),
      "KB ON · DD": o_on.get("max_drawdown_r", "—"),
      "Δ R (ON−OFF)": (
        round(o_on["total_r"] - o_off["total_r"], 2)
        if o_off.get("total_r") is not None and o_on.get("total_r") is not None else "—"
      ),
    })
  return rows


def best_combo(reports: dict[str, dict], train_months_list: list[int]) -> tuple[str, float] | None:
  best_key, best_r = None, None
  for tm in train_months_list:
    for use_kb in (False, True):
      key = result_key(tm, use_kb)
      rep = reports.get(key)
      if not rep:
        continue
      r = rep.get("overall_oos", {}).get("total_r")
      if r is None:
        continue
      if best_r is None or r > best_r:
        best_r = float(r)
        best_key = key
  if best_key is None:
    return None
  return best_key, best_r
