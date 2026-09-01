"""Paper HistoryFeed must rebase SL/TP onto fill entry (preserve planned risk/RR)."""
from __future__ import annotations

from typing import Optional, Tuple

from execution import rebase_levels


def rebase_paper_levels(
  *,
  action: str,
  fill_entry: float,
  planned_entry: float,
  planned_sl: float,
  planned_tp: float,
  rr: Optional[float] = None,
) -> Tuple[float, float, float]:
  """Return (sl, tp, risk) at fill_entry matching OOS geometry."""
  direction = 1 if action.upper() == "BUY" else -1
  if action.upper() not in ("BUY", "SELL"):
    raise ValueError(action)
  planned_risk = abs(planned_entry - planned_sl)
  if planned_risk <= 0:
    raise ValueError("planned_risk must be > 0")
  return rebase_levels(
    direction, fill_entry, planned_entry, planned_sl, planned_tp, rr,
  )


def test_rebase_prevents_march18_style_r_explosion():
  # Decision (spread-adjusted) vs raw open fill — pre-fix risk collapsed to 0.4 pip
  planned_entry, planned_sl, planned_tp = 1.15446, 1.15482, 1.15339
  fill = 1.15478
  old_risk = abs(fill - planned_sl)
  assert old_risk < 0.00005  # ~0.4 pip — the bug

  sl, tp, risk = rebase_paper_levels(
    action="SELL",
    fill_entry=fill,
    planned_entry=planned_entry,
    planned_sl=planned_sl,
    planned_tp=planned_tp,
    rr=3.0,
  )
  assert abs(risk - abs(planned_entry - planned_sl)) < 1e-12
  assert abs(sl - (fill + risk)) < 1e-12
  assert abs(tp - (fill - risk * 3.0)) < 1e-12
  # TP hit at old tp price would not apply; at rebased tp, R at tp == rr
  exit_at_tp = tp
  r = (fill - exit_at_tp) / risk
  assert abs(r - 3.0) < 1e-9


def test_rebase_buy_symmetric():
  sl, tp, risk = rebase_paper_levels(
    action="BUY",
    fill_entry=1.10,
    planned_entry=1.0995,
    planned_sl=1.0985,
    planned_tp=1.1025,
    rr=3.0,
  )
  assert abs(risk - 0.001) < 1e-12
  assert abs(sl - 1.099) < 1e-12
  assert abs(tp - 1.103) < 1e-12
