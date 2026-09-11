"""Paper HistoryFeed must rebase SL/TP onto fill entry (preserve planned risk/RR)."""
from __future__ import annotations

from execution import effective_rr, rebase_fill_levels


def test_rebase_prevents_march18_style_r_explosion():
  # Decision (spread-adjusted) vs raw open fill — pre-fix risk collapsed to 0.4 pip
  planned_entry, planned_sl, planned_tp = 1.15446, 1.15482, 1.15339
  fill = 1.15478
  old_risk = abs(fill - planned_sl)
  assert old_risk < 0.00005  # ~0.4 pip — the bug

  sl, tp, risk = rebase_fill_levels(
    direction=-1,
    fill_entry=fill,
    planned_entry=planned_entry,
    planned_sl=planned_sl,
    planned_tp=planned_tp,
    rr=3.0,
  )
  geom = effective_rr(planned_entry, planned_sl, planned_tp)
  assert abs(risk - abs(planned_entry - planned_sl)) < 1e-12
  assert abs(sl - (fill + risk)) < 1e-12
  # Geometry wins over genome rr=3 so TP-clip is not undone.
  assert abs(tp - (fill - risk * geom)) < 1e-12
  r = (fill - tp) / risk
  assert abs(r - geom) < 1e-9


def test_rebase_buy_uses_planned_geometry_not_genome_rr():
  sl, tp, risk = rebase_fill_levels(
    direction=1,
    fill_entry=1.10,
    planned_entry=1.0995,
    planned_sl=1.0985,
    planned_tp=1.1025,
    rr=3.0,
  )
  assert abs(risk - 0.001) < 1e-12
  assert abs(sl - 1.099) < 1e-12
  # planned RR = 0.003/0.001 = 3.0, so genome 3.0 matches geometry here
  assert abs(tp - 1.103) < 1e-12


def test_rebase_clip_tp_ignores_genome_rr():
  planned = 1.10000
  planned_sl = 1.09881  # ATR + 1 spread
  planned_tp = 1.10270  # ATR × 3 only (clip)
  fill = 1.10020
  sl, tp, risk = rebase_fill_levels(
    direction=1,
    fill_entry=fill,
    planned_entry=planned,
    planned_sl=planned_sl,
    planned_tp=planned_tp,
    rr=3.0,
  )
  geom = effective_rr(planned, planned_sl, planned_tp)
  assert geom < 2.8
  assert abs(risk - (planned - planned_sl)) < 1e-12
  assert abs(tp - (fill + risk * geom)) < 1e-12
  assert abs(tp - (fill + risk * 3.0)) > 1e-6
