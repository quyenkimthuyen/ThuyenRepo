"""Expected genome thresholds vs current last-bar features for Live Now."""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

from live_config import RESULTS_DIR

BROKER_TZ_NAME = os.environ.get("EDGEMINER_BROKER_TIMEZONE", "Europe/Helsinki")
DISPLAY_TZ_NAME = os.environ.get("EDGEMINER_DISPLAY_TIMEZONE", "Asia/Ho_Chi_Minh")
DISPLAY_TZ_LABEL = "Giờ VN (UTC+7)"

_FEAT_CACHE: dict[tuple, dict[str, Any]] = {}
_FM_TAIL = 720
_CHART_BARS = 96
_CHART_TAIL = {
  "today": 720,
  "week": 720,
  "month": 2800,
  "all": 4200,
}

_LABEL = {
  "session_vwap_dist": "VWAP",
  "squeeze_break_up": "squeeze↑",
  "squeeze_break_dn": "squeeze↓",
  "macd_cross_up": "MACD↑",
  "macd_cross_dn": "MACD↓",
  "macd_hist": "MACDh",
  "price_vs_ema50": "EMA50",
  "price_vs_ema21": "EMA21",
  "ema_slope_21": "slope21",
  "ema_slope_8": "slope8",
  "roc_5": "ROC5",
  "atr_pct": "ATR%",
  "swing_strength": "swing",
  "structure_break_up": "brk↑",
  "structure_break_dn": "brk↓",
  "htf_trend": "HTF",
  "confluence_long": "PA↑",
  "confluence_short": "PA↓",
  "rsi": "RSI",
  "bb_pos": "BB",
}


def _read(path: Path) -> Any:
  if not path.is_file():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def load_week_strategy(model_id: str | None) -> dict[str, Any]:
  mid = str(model_id or "").strip()
  if not mid:
    return {}
  live = _read(RESULTS_DIR / "trade_models" / f"{mid}_live_weeks.json") or {}
  sched = _read(RESULTS_DIR / "trade_models" / f"{mid}_schedule.json") or {}
  try:
    from datetime import date, timedelta
    from strategy_mode import carry_forward_week_strategy

    today = date.today()
    week_start = str(today - timedelta(days=today.weekday()))
    hit = carry_forward_week_strategy(
      mid, week_start, schedule=sched, live_weeks=live,
    )
    if hit and isinstance(hit.get("strategy"), dict):
      return dict(hit["strategy"])
  except Exception:
    pass
  for payload in (live, sched):
    weekly = list((payload or {}).get("weekly") or [])
    if (
      weekly
      and isinstance(weekly[-1], dict)
      and isinstance(weekly[-1].get("strategy"), dict)
    ):
      return dict(weekly[-1]["strategy"])
  return {}


def _feat_label(name: str) -> str:
  return _LABEL.get(name, name)


def _fmt_num(value: float) -> str:
  av = abs(value)
  if av >= 10:
    return f"{value:.1f}"
  if av >= 1:
    return f"{value:.2f}".rstrip("0").rstrip(".")
  return f"{value:.3f}".rstrip("0").rstrip(".")


def _rule_parts(rule: dict) -> tuple[str, str, float, float]:
  feat = str(rule.get("feat") or rule.get("feature") or "")
  op = str(rule.get("op") or "")
  thr = float(rule.get("thr", rule.get("threshold", 0.0)) or 0.0)
  w = abs(float(rule.get("w", rule.get("weight", 0.0)) or 0.0))
  return feat, op, thr, w


def expect_text(rule: dict | None) -> str:
  if not rule:
    return "—"
  feat, op, thr, _ = _rule_parts(rule)
  lab = _feat_label(feat)
  if op == "eq1":
    return f"{lab}=1"
  if op == "lt":
    return f"{lab} < {_fmt_num(thr)}"
  if op == "gt":
    return f"{lab} > {_fmt_num(thr)}"
  return lab


def current_text(rule: dict | None, feats: dict[str, float]) -> str:
  if not rule:
    return "—"
  feat, op, _, _ = _rule_parts(rule)
  if feat not in feats:
    return "—"
  val = feats[feat]
  if op == "eq1":
    return "1" if val > 0.5 else "0"
  return _fmt_num(val)


def rule_hit(rule: dict | None, feats: dict[str, float]) -> bool:
  if not rule:
    return False
  feat, op, thr, _ = _rule_parts(rule)
  if feat not in feats:
    return False
  val = feats[feat]
  if not math.isfinite(val):
    return False
  if op == "eq1":
    return val > 0.5
  if op == "lt":
    return val < thr
  if op == "gt":
    return val > thr
  return False


def _heaviest(rules: list | None) -> dict | None:
  ranked = _sorted_rules(rules)
  return ranked[0] if ranked else None


def _sorted_rules(rules: list | None) -> list[dict]:
  out: list[dict] = []
  for raw in rules or []:
    if isinstance(raw, dict):
      out.append(raw)
  out.sort(key=lambda r: _rule_parts(r)[3], reverse=True)
  return out


def _min_rules(strat: dict | None) -> int:
  try:
    n = int((strat or {}).get("min_rules_match") or 1)
  except (TypeError, ValueError):
    n = 1
  return max(1, n)


def _side_line(side: str, rule: dict | None, feats: dict[str, float]) -> dict[str, Any]:
  if not rule:
    return {"side": side, "text": "—", "hit": False, "now": "—", "need": "—"}
  feat, op, thr, _ = _rule_parts(rule)
  lab = _feat_label(feat)
  now = current_text(rule, feats)
  hit = rule_hit(rule, feats)
  if op == "eq1":
    op_s, need = "=", "1"
  elif op == "lt":
    op_s, need = "<", _fmt_num(thr)
  elif op == "gt":
    op_s, need = ">", _fmt_num(thr)
  else:
    op_s, need = "?", "—"
  return {
    "side": side,
    "text": f"{lab} {now} {op_s} {need}",
    "hit": hit,
    "now": now,
    "need": need,
    "op": op_s,
    "feat": lab,
    "feat_key": feat,
    "thr": thr,
  }


_HARD_WHY = {
  "min_bars_between": "too close to last trade",
  "no_slots": "day slots full",
  "position_open": "already in a trade",
  "levels_unavailable": "no SL/TP",
  "risk_cap": "risk cap",
  "risk_cap_error": "risk cap error",
  "remine_gate_fail": "remined week blocked",
  "frozen_missing": "no frozen genome",
  "bar_not_in_series": "bar missing",
  "no_strategy": "no week strategy",
  "insufficient_train_data": "no train data",
  "no_oos_week": "no OOS week",
}

_HARD_WAIT = {
  "min_bars_between": "Gap",
  "no_slots": "Day",
  "position_open": "Hold",
  "levels_unavailable": "SL/TP",
  "risk_cap": "Risk",
  "risk_cap_error": "Risk",
  "remine_gate_fail": "Remine",
  "frozen_missing": "Frozen",
  "bar_not_in_series": "Bar",
  "no_strategy": "Strat",
  "insufficient_train_data": "Data",
  "no_oos_week": "OOS",
}


def _broker_hour(raw: Any) -> int | None:
  m = re.search(r"(?:^|[\sT])(\d{1,2}):\d{2}", str(raw or ""))
  if not m:
    return None
  try:
    hour = int(m.group(1))
  except (TypeError, ValueError):
    return None
  return hour if 0 <= hour <= 23 else None


def _session_pack(strat: dict | None, bar_time: Any) -> dict[str, Any]:
  strat = strat or {}
  try:
    start = int(strat.get("session_start_hour") if strat.get("session_start_hour") is not None else 7)
  except (TypeError, ValueError):
    start = 7
  try:
    end = int(strat.get("session_end_hour") if strat.get("session_end_hour") is not None else 20)
  except (TypeError, ValueError):
    end = 20
  on = bool(strat.get("session_filter"))
  hour = _broker_hour(bar_time)
  blocked: set[int] = set()
  for h in strat.get("blocked_hours") or []:
    try:
      blocked.add(int(h))
    except (TypeError, ValueError):
      continue
  ok = True
  if on and hour is not None:
    ok = start <= hour <= end and hour not in blocked
  if hour is not None:
    gate = f"{hour}/{start}-{end}"
  else:
    gate = f"—/{start}-{end}"
  return {
    "on": on,
    "ok": ok,
    "hour": hour,
    "start": start,
    "end": end,
    "gate": gate,
  }


def _rsi_chase_caps(strat: dict | None) -> tuple[float, float]:
  strat = strat or {}
  short_max = None
  for key in ("anti_chase_rsi_short_max", "anti_chase_fixed_rsi"):
    if strat.get(key) is None:
      continue
    try:
      short_max = float(strat.get(key))
      break
    except (TypeError, ValueError):
      continue
  if short_max is None:
    short_max = 100.0
  try:
    long_min = float(
      strat.get("anti_chase_rsi_long_min") if strat.get("anti_chase_rsi_long_min") is not None else 0.0
    )
  except (TypeError, ValueError):
    long_min = 0.0
  return short_max, long_min


def _chase_pack(strat: dict | None, feats: dict[str, float]) -> dict[str, Any]:
  strat = strat or {}
  on = bool(strat.get("anti_chase"))
  out = {"on": on, "buy_block": False, "sell_block": False, "buy_why": "", "sell_why": ""}
  if not on:
    return out
  rsi = feats.get("rsi")
  vwap = feats.get("session_vwap_dist")
  short_max, long_min = _rsi_chase_caps(strat)
  try:
    vwap_max = float(
      strat.get("anti_chase_vwap_short_max") if strat.get("anti_chase_vwap_short_max") is not None
      else (strat.get("anti_chase_fixed_vwap") if strat.get("anti_chase_fixed_vwap") is not None else 99.0)
    )
  except (TypeError, ValueError):
    vwap_max = 99.0
  logic = str(strat.get("anti_chase_logic") or "or").lower()
  rsi_ok = rsi is not None and math.isfinite(float(rsi))
  vwap_ok = vwap is not None and math.isfinite(float(vwap))
  rsi_chase_s = rsi_ok and float(rsi) >= short_max
  vwap_chase_s = vwap_ok and float(vwap) >= vwap_max
  if logic == "and":
    sell_block = bool(rsi_chase_s and vwap_chase_s)
  else:
    sell_block = bool(rsi_chase_s or (vwap_max < 90 and vwap_chase_s))
  buy_block = bool(rsi_ok and float(rsi) <= long_min)
  out["buy_block"] = buy_block
  out["sell_block"] = sell_block
  if sell_block:
    bits = []
    if rsi_chase_s:
      bits.append(f"RSI {_fmt_num(float(rsi))}≥{_fmt_num(short_max)}")
    if vwap_max < 90 and vwap_chase_s:
      bits.append(f"VWAP {_fmt_num(float(vwap))}≥{_fmt_num(vwap_max)}")
    out["sell_why"] = " · ".join(bits) or "chase"
  if buy_block:
    out["buy_why"] = f"RSI {_fmt_num(float(rsi))}≤{_fmt_num(long_min)}"
  return out


def _wait_pack(
  *,
  action: str | None,
  reason: str | None,
  buy: dict[str, Any],
  sell: dict[str, Any],
  session: dict[str, Any],
  chase: dict[str, Any],
  fire: dict[str, Any] | None = None,
  gap: dict[str, Any] | None = None,
) -> dict[str, Any]:
  rsn = str(reason or "").strip()
  act = str(action or "").upper()
  fire = fire or {}
  gap = gap or {}
  if act == "HOLD" or rsn == "position_open":
    return {"text": "Hold", "ok": False, "code": "hold"}
  if rsn == "signal" and act in ("BUY", "SELL", "LONG", "SHORT"):
    return {"text": "—", "ok": True, "code": "live"}
  if rsn in _HARD_WAIT:
    return {"text": _HARD_WAIT[rsn], "ok": False, "code": rsn}
  if session.get("on") and not session.get("ok"):
    hour = session.get("hour")
    return {
      "text": f"Sess {hour}h" if hour is not None else "Sess",
      "ok": False,
      "code": "session",
    }
  if sell.get("ready") and chase.get("sell_block"):
    return {"text": "Chase", "ok": False, "code": "chase"}
  if buy.get("ready") and chase.get("buy_block"):
    return {"text": "Chase", "ok": False, "code": "chase"}
  if (buy.get("ready") or sell.get("ready")) and gap.get("on") and not gap.get("ok"):
    return {"text": f"Gap {gap.get('text') or ''}".strip(), "ok": False, "code": "gap"}
  ready_side = "sell" if sell.get("ready") else ("buy" if buy.get("ready") else "")
  fp = fire.get(ready_side) if ready_side else None
  if ready_side and fp:
    if not fp.get("score_ok"):
      return {"text": "Score", "ok": False, "code": "score"}
    if not fp.get("ml_live"):
      return {"text": "ML≈", "ok": False, "code": "ml"}
    if not fp.get("ml_ok"):
      return {"text": "ML", "ok": False, "code": "ml"}
    return {"text": "—", "ok": True, "code": ""}
  return {"text": "—", "ok": True, "code": ""}


def _side_pack(side: str, rules: list | None, feats: dict[str, float], min_need: int) -> dict[str, Any]:
  lines = [_side_line(side, rule, feats) for rule in _sorted_rules(rules)]
  hit_labs = [str(x.get("feat") or "") for x in lines if x.get("hit") and x.get("feat")]
  miss_labs = [str(x.get("feat") or "") for x in lines if (not x.get("hit")) and x.get("feat")]
  n_hit = len(hit_labs)
  n_rules = len(lines)
  ready = n_hit >= min_need and bool(lines)
  heaviest = lines[0] if lines else _side_line(side, None, feats)
  return {
    "side": side,
    "lines": lines,
    "n_hit": n_hit,
    "n_rules": n_rules,
    "min_need": min_need,
    "gate": f"{n_hit}/{n_rules}" if n_rules else "—",
    "ready": ready,
    "hit_labs": hit_labs,
    "miss": miss_labs,
    "text": " · ".join(x["text"] for x in lines) if lines else "—",
    "hit": ready,
    "feat": heaviest.get("feat"),
    "now": heaviest.get("now"),
    "need": heaviest.get("need"),
    "op": heaviest.get("op"),
  }


def _side_why(name: str, pack: dict[str, Any]) -> str:
  if not pack.get("lines"):
    return f"{name} —"
  gate = pack.get("gate") or "—"
  need = pack.get("min_need") or 1
  if pack.get("ready"):
    return f"{name} {gate} hit (need {need})"
  miss = ", ".join(pack.get("miss") or []) or "no rules"
  return f"{name} {gate} miss {miss} (need {need})"


def explain_watch(
  *,
  action: str | None,
  reason: str | None,
  buy: dict[str, Any],
  sell: dict[str, Any],
  wait: dict[str, Any] | None = None,
  session: dict[str, Any] | None = None,
  chase: dict[str, Any] | None = None,
) -> str:
  rsn = str(reason or "").strip()
  if rsn in _HARD_WHY:
    return _HARD_WHY[rsn]
  act = str(action or "").upper()
  if act == "HOLD":
    return "holding open trade"
  if rsn == "signal" and act in ("BUY", "LONG"):
    labs = " + ".join(buy.get("hit_labs") or []) or "rules"
    return f"BUY in · {labs} ({buy.get('gate') or '?'})"
  if rsn == "signal" and act in ("SELL", "SHORT"):
    labs = " + ".join(sell.get("hit_labs") or []) or "rules"
    return f"SELL in · {labs} ({sell.get('gate') or '?'})"
  wait = wait or {}
  session = session or {}
  chase = chase or {}
  code = str(wait.get("code") or "")
  if code == "session":
    hour = session.get("hour")
    start = session.get("start")
    end = session.get("end")
    clock = f"{hour:02d}h" if isinstance(hour, int) else "—"
    return f"session {clock} · need {start}-{end} (BUY/SELL rules are not an order)"
  if code == "chase":
    if sell.get("ready") and chase.get("sell_block"):
      extra = chase.get("sell_why") or "chase"
      return f"SELL {sell.get('gate') or '?'} hit, chase {extra}"
    extra = chase.get("buy_why") or "chase"
    return f"BUY {buy.get('gate') or '?'} hit, chase {extra}"
  if code == "ml":
    side = "SELL" if sell.get("ready") else "BUY"
    gate = (sell if sell.get("ready") else buy).get("gate") or "?"
    fire = (wait or {}).get("fire_side") or {}
    ml = fire.get("ml_text") or "ML"
    return f"{side} {gate} hit, wait {ml}"
  if code == "score":
    side = "SELL" if sell.get("ready") else "BUY"
    gate = (sell if sell.get("ready") else buy).get("gate") or "?"
    fire = (wait or {}).get("fire_side") or {}
    sc = fire.get("score_text") or "score"
    return f"{side} {gate} hit, wait {sc}"
  if code == "gap":
    return f"too close · need {wait.get('text') or 'gap'}"
  if buy.get("ready") or sell.get("ready"):
    parts = [_side_why("BUY", buy), _side_why("SELL", sell)]
    if not wait.get("ok"):
      parts.append("wait ML/score/chase")
    return " · ".join(parts)
  return " · ".join([_side_why("BUY", buy), _side_why("SELL", sell)])


def _tf_minutes(timeframe: str | None) -> int:
  t = str(timeframe or "M15").upper().strip()
  if t.startswith("M") and t[1:].isdigit():
    return max(1, int(t[1:]))
  if t.startswith("H") and t[1:].isdigit():
    return max(1, int(t[1:]) * 60)
  return 15


def _weighted_rule_score(rules: list | None, feats: dict[str, float]) -> tuple[float, int]:
  score = 0.0
  n = 0
  for rule in _sorted_rules(rules):
    if not rule_hit(rule, feats):
      continue
    n += 1
    score += _rule_parts(rule)[3]
  return score, n


def _htf_mult(feats: dict[str, float], direction: int, strat: dict) -> tuple[float, float | None]:
  raw = feats.get("htf_trend")
  try:
    htf = float(raw) if raw is not None else None
  except (TypeError, ValueError):
    htf = None
  if htf is None or not math.isfinite(htf) or htf == 0.0:
    return 1.0, htf
  try:
    boost = float(strat.get("htf_align_boost") if strat.get("htf_align_boost") is not None else 1.12)
  except (TypeError, ValueError):
    boost = 1.12
  try:
    damp = float(strat.get("htf_counter_dampen") if strat.get("htf_counter_dampen") is not None else 0.88)
  except (TypeError, ValueError):
    damp = 0.88
  aligned = (direction == 1 and htf > 0) or (direction == -1 and htf < 0)
  return (boost if aligned else damp), htf


def _fire_side(
  *,
  strat: dict,
  feats: dict[str, float],
  side: str,
  dumped: dict | None,
  ml_live: bool = False,
) -> dict[str, Any]:
  dumped = dumped if isinstance(dumped, dict) else {}
  rules_key = "long_rules" if side == "buy" else "short_rules"
  direction = 1 if side == "buy" else -1
  pa_key = "confluence_long" if side == "buy" else "confluence_short"
  try:
    thr = float(strat.get("score_threshold") if strat.get("score_threshold") is not None else 0.6)
  except (TypeError, ValueError):
    thr = 0.6
  try:
    ml_min = float(strat.get("ml_prob_min") if strat.get("ml_prob_min") is not None else 0.4)
  except (TypeError, ValueError):
    ml_min = 0.4
  w, n = _weighted_rule_score(strat.get(rules_key), feats)
  if dumped.get("w") is not None:
    try:
      w = float(dumped["w"])
    except (TypeError, ValueError):
      pass
  if dumped.get("n") is not None:
    try:
      n = int(dumped["n"])
    except (TypeError, ValueError):
      pass
  htf_m, htf_raw = _htf_mult(feats, direction, strat)
  if dumped.get("htf") is not None:
    try:
      htf_m = float(dumped["htf"])
    except (TypeError, ValueError):
      pass
  try:
    pa = 0.35 * float(feats.get(pa_key) or 0.0)
  except (TypeError, ValueError):
    pa = 0.0
  if dumped.get("pa") is not None:
    try:
      pa = float(dumped["pa"])
    except (TypeError, ValueError):
      pass
  ml_live = bool(ml_live)
  try:
    ml = float(dumped["ml"]) if dumped.get("ml") is not None else 0.5
  except (TypeError, ValueError):
    ml = 0.5
    ml_live = False
  if dumped.get("score") is not None:
    try:
      combined = float(dumped["score"])
    except (TypeError, ValueError):
      combined = w * (0.5 + ml) * htf_m + pa
  else:
    combined = w * (0.5 + ml) * htf_m + pa
  score_ok = combined >= thr if dumped.get("score_ok") is None else bool(dumped.get("score_ok"))
  ml_ok = ml >= ml_min if dumped.get("ml_ok") is None else bool(dumped.get("ml_ok"))
  tag = "B" if side == "buy" else "S"
  return {
    "side": side,
    "w": w,
    "n": n,
    "ml": ml,
    "ml_live": ml_live,
    "htf": htf_m,
    "htf_raw": htf_raw,
    "pa": pa,
    "score": combined,
    "thr": thr,
    "ml_min": ml_min,
    "score_ok": score_ok,
    "ml_ok": ml_ok,
    "score_text": f"{tag} {_fmt_num(combined)}/{_fmt_num(thr)}",
    "ml_text": f"{tag} {_fmt_num(ml)}/{_fmt_num(ml_min)}" + ("" if ml_live else "≈"),
    "htf_text": f"{tag} {_fmt_num(htf_m)}" + (
      " +" if (htf_raw or 0) * direction > 0 else (" −" if htf_raw else "")
    ),
    "pa_text": f"{tag} {_fmt_num(pa)}",
  }


def _gap_pack(
  strat: dict | None,
  *,
  bar_time: Any,
  fills: list | None,
  timeframe: str | None,
) -> dict[str, Any]:
  strat = strat or {}
  try:
    need = int(strat.get("min_bars_between") or 0)
  except (TypeError, ValueError):
    need = 0
  if need <= 0:
    return {"on": False, "ok": True, "text": "—", "have": None, "need": 0}
  bar_dt = _parse_hit_time(bar_time)
  last_dt = None
  bar_day_key = bar_dt.strftime("%Y-%m-%d") if bar_dt else ""
  for fill in fills or []:
    raw = fill.get("time") if isinstance(fill, dict) else fill
    if isinstance(fill, dict):
      raw = fill.get("time") or fill.get("entry_time") or fill.get("bar_time")
    dt = _parse_hit_time(raw)
    if dt is None:
      continue
    if bar_day_key and dt.strftime("%Y-%m-%d") != bar_day_key:
      continue
    if last_dt is None or dt > last_dt:
      last_dt = dt
  if last_dt is None or bar_dt is None:
    return {"on": True, "ok": True, "text": f"—/{need}", "have": need, "need": need}
  minutes = max(0.0, (bar_dt - last_dt).total_seconds() / 60.0)
  have = int(round(minutes / _tf_minutes(timeframe)))
  ok = have >= need
  return {
    "on": True,
    "ok": ok,
    "text": f"{have}/{need}",
    "have": have,
    "need": need,
  }


def extra_gate_lines(strat: dict | None) -> dict[str, list[dict[str, Any]]]:
  """RSI/VWAP chase + HTF zero line — not always in genome rules."""
  strat = strat or {}
  by_feat: dict[str, list[dict[str, Any]]] = {}
  if strat.get("anti_chase"):
    rsi_s, rsi_l = _rsi_chase_caps(strat)
    if rsi_s < 99.5:
      by_feat.setdefault("rsi", []).append({
        "side": "S", "thr": rsi_s, "label": f"SELL RSI < {_fmt_num(rsi_s)}",
      })
    if rsi_l > 0.5:
      by_feat.setdefault("rsi", []).append({
        "side": "B", "thr": rsi_l, "label": f"BUY RSI > {_fmt_num(rsi_l)}",
      })
    try:
      vwap_m = float(strat.get("anti_chase_vwap_short_max") if strat.get("anti_chase_vwap_short_max") is not None else 99)
    except (TypeError, ValueError):
      vwap_m = 99.0
    if vwap_m < 90:
      by_feat.setdefault("session_vwap_dist", []).append({
        "side": "S", "thr": vwap_m, "label": f"SELL chase VWAP < {_fmt_num(vwap_m)}",
      })
  by_feat.setdefault("htf_trend", []).append({
    "side": "B", "thr": 0.0, "label": "HTF 0",
  })
  return by_feat


def format_watch_expect(
  strat: dict | None,
  feats: dict[str, float] | None,
  *,
  action: str | None = None,
  reason: str | None = None,
  bar_time: Any = None,
  dumped: dict | None = None,
  fills: list | None = None,
  timeframe: str | None = None,
) -> dict[str, Any]:
  """Every BUY/SELL rule vs last bar, plus session/chase/score/ML/gap gates."""
  strat = strat or {}
  feats = feats or {}
  dumped = dumped if isinstance(dumped, dict) else {}
  min_need = _min_rules(strat)
  buy = _side_pack("B", strat.get("long_rules"), feats, min_need)
  sell = _side_pack("S", strat.get("short_rules"), feats, min_need)
  session = _session_pack(strat, bar_time)
  chase = _chase_pack(strat, feats)
  buy_fire = _fire_side(
    strat=strat, feats=feats, side="buy", dumped=dumped.get("buy"),
    ml_live=bool(dumped.get("ml_live")),
  )
  sell_fire = _fire_side(
    strat=strat, feats=feats, side="sell", dumped=dumped.get("sell"),
    ml_live=bool(dumped.get("ml_live")),
  )
  fire = {"buy": buy_fire, "sell": sell_fire}
  gap = _gap_pack(strat, bar_time=bar_time, fills=fills, timeframe=timeframe)
  wait = _wait_pack(
    action=action, reason=reason, buy=buy, sell=sell, session=session, chase=chase,
    fire=fire, gap=gap,
  )
  wait["fire_side"] = sell_fire if sell.get("ready") else buy_fire
  parts_e: list[str] = []
  parts_c: list[str] = []
  for pack, tag in ((buy, "B"), (sell, "S")):
    for line in pack.get("lines") or []:
      if line.get("feat"):
        parts_e.append(f"{tag} {line['feat']} {line['op']} {line['need']}")
        parts_c.append(str(line.get("now") or "—"))
  why = explain_watch(
    action=action, reason=reason, buy=buy, sell=sell, wait=wait, session=session, chase=chase,
  )
  rsi = feats.get("rsi") if feats.get("rsi") is not None else dumped.get("rsi")
  htf_raw = feats.get("htf_trend") if feats.get("htf_trend") is not None else dumped.get("htf_trend")
  pa_l = feats.get("confluence_long") if feats.get("confluence_long") is not None else dumped.get("confluence_long")
  pa_s = feats.get("confluence_short") if feats.get("confluence_short") is not None else dumped.get("confluence_short")
  try:
    rsi_s = float(rsi) if rsi is not None else None
  except (TypeError, ValueError):
    rsi_s = None
  rsi_text = "RSI —"
  rsi_ok = False
  if rsi_s is not None:
    rsi_ok = True
    rsi_text = f"RSI {_fmt_num(rsi_s)}"
    if chase.get("on"):
      short_max, long_min = _rsi_chase_caps(strat)
      rsi_ok = (not chase.get("buy_block")) and (not chase.get("sell_block"))
      if short_max < 99.5:
        rsi_text = f"RSI {_fmt_num(rsi_s)}<{_fmt_num(short_max)}"
      elif long_min > 0.5:
        rsi_text = f"RSI {_fmt_num(rsi_s)}>{_fmt_num(long_min)}"
  try:
    htf_s = float(htf_raw) if htf_raw is not None else None
  except (TypeError, ValueError):
    htf_s = None
  if htf_s is None:
    htf_text = "HTF —"
    htf_ok = False
  elif htf_s > 0:
    htf_text = "HTF +"
    htf_ok = True
  elif htf_s < 0:
    htf_text = "HTF −"
    htf_ok = False
  else:
    htf_text = "HTF 0"
    htf_ok = False
  pa_ok = False
  try:
    if pa_l is not None and str(pa_l) != "None" and float(pa_l) > 0:
      pa_ok = True
  except (TypeError, ValueError):
    pass
  try:
    if pa_s is not None and str(pa_s) != "None" and float(pa_s) > 0:
      pa_ok = True
  except (TypeError, ValueError):
    pass
  return {
    "buy": buy,
    "sell": sell,
    "buy_lines": list(buy.get("lines") or []),
    "sell_lines": list(sell.get("lines") or []),
    "buy_gate": buy.get("gate") or "—",
    "sell_gate": sell.get("gate") or "—",
    "buy_ready": bool(buy.get("ready")),
    "sell_ready": bool(sell.get("ready")),
    "buy_text": buy.get("text") or "—",
    "sell_text": sell.get("text") or "—",
    "why": why,
    "min_rules": min_need,
    "session_gate": session.get("gate") or "—",
    "session_ok": bool(session.get("ok")),
    "session_on": bool(session.get("on")),
    "chase_on": bool(chase.get("on")),
    "chase_block": bool(
      (sell.get("ready") and chase.get("sell_block"))
      or (buy.get("ready") and chase.get("buy_block"))
    ),
    "wait": wait.get("text") or "—",
    "wait_ok": bool(wait.get("ok")),
    "wait_code": wait.get("code") or "",
    "score_buy": buy_fire.get("score_text") or "—",
    "score_sell": sell_fire.get("score_text") or "—",
    "score_ok": bool(buy_fire.get("score_ok") or sell_fire.get("score_ok")),
    "ml_buy": buy_fire.get("ml_text") or "—",
    "ml_sell": sell_fire.get("ml_text") or "—",
    "ml_ok": bool(buy_fire.get("ml_ok") or sell_fire.get("ml_ok")),
    "ml_live": bool(buy_fire.get("ml_live") or sell_fire.get("ml_live") or dumped.get("ml_live")),
    "gap": gap.get("text") or "—",
    "gap_ok": bool(gap.get("ok")),
    "gap_on": bool(gap.get("on")),
    "rsi_text": rsi_text,
    "rsi_ok": bool(rsi_ok),
    "htf_text": htf_text,
    "htf_ok": bool(htf_ok),
    "pa_buy": f"PA↑ {_fmt_num(float(pa_l))}" if pa_l is not None and str(pa_l) != "None" else "PA↑ —",
    "pa_sell": f"PA↓ {_fmt_num(float(pa_s))}" if pa_s is not None and str(pa_s) != "None" else "PA↓ —",
    "pa_ok": bool(pa_ok),
    "expect": " · ".join(parts_e) if parts_e else "—",
    "current": " · ".join(parts_c) if parts_c else "—",
    "hits": [bool(buy.get("ready")), bool(sell.get("ready"))],
    "hit": bool(buy.get("ready") or sell.get("ready")),
  }


def _features_from_file(bridge_dir: Path | None) -> dict[str, float]:
  if not bridge_dir:
    return {}
  data = _read(Path(bridge_dir) / "features.json") or {}
  raw = data.get("features") if isinstance(data, dict) else None
  if not isinstance(raw, dict):
    return {}
  out: dict[str, float] = {}
  for k, v in raw.items():
    try:
      fv = float(v)
    except (TypeError, ValueError):
      continue
    if math.isfinite(fv):
      out[str(k)] = fv
  return out


def _bars_to_frame(bars: list[dict]):
  import pandas as pd
  from mt5_bridge.history_sync import parse_broker_time

  rows = []
  index = []
  for bar in bars:
    try:
      index.append(parse_broker_time(bar.get("time") or bar.get("bar_time")))
      rows.append({
        "Open": float(bar["open"]),
        "High": float(bar["high"]),
        "Low": float(bar["low"]),
        "Close": float(bar["close"]),
        "Volume": float(bar.get("volume") or bar.get("tick_volume") or 0),
      })
    except (KeyError, TypeError, ValueError):
      continue
  if not rows:
    return None
  return pd.DataFrame(rows, index=pd.DatetimeIndex(index))


def _ensure_host(symbol: str, timeframe: str) -> None:
  from runtime_host import resolve_host_desk

  desk = str(resolve_host_desk(symbol, timeframe))
  if desk in sys.path:
    sys.path.remove(desk)
  sys.path.insert(0, desk)


def _chart_tail_for_period(period: str | None) -> int:
  p = (period or "today").lower().strip()
  return int(_CHART_TAIL.get(p, _FM_TAIL))


def chart_period_bounds(period: str | None, *, now=None) -> tuple[Any, Any]:
  """Same D/W/M window as Now radio / Session (local VN)."""
  from datetime import datetime, timedelta

  p = (period or "today").lower().strip()
  ts = now
  if ts is None:
    ts = datetime.now().astimezone()
  elif getattr(ts, "tzinfo", None) is None:
    local = datetime.now().astimezone().tzinfo
    ts = ts.replace(tzinfo=local) if local is not None else ts
  if p in ("all",):
    return None, None
  start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
  if p in ("today", "day"):
    return start, None
  if p in ("week", "this_week"):
    start = (ts - timedelta(days=ts.weekday())).replace(
      hour=0, minute=0, second=0, microsecond=0,
    )
    return start, None
  if p in ("month", "this_month"):
    start = ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, None
  return None, None


def _naive_in_bounds(value, start, end) -> bool:
  parsed = _parse_hit_time(value)
  if parsed is None:
    return start is None and end is None
  if start is not None:
    s = start.replace(tzinfo=None) if getattr(start, "tzinfo", None) else start
    s = _parse_hit_time(s) or s
    if parsed < s:
      return False
  if end is not None:
    e = end.replace(tzinfo=None) if getattr(end, "tzinfo", None) else end
    e = _parse_hit_time(e) or e
    if parsed >= e:
      return False
  return True


def slice_pack_to_period(
  pack: dict[str, Any],
  period: str | None,
  *,
  now=None,
) -> dict[str, Any]:
  """Keep bars whose VN wall time falls in the Now D/W/M/ALL window."""
  times = list(pack.get("times") or [])
  series = dict(pack.get("series") or {})
  if not times:
    return pack
  start, end = chart_period_bounds(period, now=now)
  if start is None and end is None:
    return pack
  keep = [
    i for i, t in enumerate(times)
    if _naive_in_bounds(broker_wall_to_display(t), start, end)
  ]
  if not keep:
    n = min(_CHART_BARS, len(times))
    keep = list(range(len(times) - n, len(times)))
  sliced_series = {}
  for name, vals in series.items():
    sliced_series[name] = [vals[i] for i in keep if i < len(vals)]
  return {
    **pack,
    "times": [times[i] for i in keep],
    "series": sliced_series,
  }


def period_fill_marks(
  trades: list[dict] | None,
  *,
  model_id: str | None,
  period: str = "today",
  now=None,
) -> list[dict[str, Any]]:
  start, end = chart_period_bounds(period, now=now)
  mid = str(model_id or "")
  out: list[dict[str, Any]] = []
  for t in trades or []:
    if mid and str(t.get("model_id") or "") != mid:
      continue
    if str(t.get("status") or "").upper() not in ("OPEN", "CLOSED"):
      continue
    entry = t.get("entry_time") or t.get("bar_time") or t.get("updated_at")
    vn = broker_wall_to_display(entry)
    if not _naive_in_bounds(vn, start, end):
      continue
    side = str(t.get("direction") or t.get("action") or "").upper()
    st = str(t.get("status") or "").upper()
    out.append({
      "time": entry,
      "exit_time": t.get("exit_time") if st == "CLOSED" else None,
      "side": side,
      "status": st,
      "result": _hit_result(t) if st == "CLOSED" else None,
    })
  out.sort(key=lambda h: str(h.get("time") or ""))
  return out


def _feature_pack_from_bars(
  bridge_dir: Path | None, symbol: str, timeframe: str,
  *,
  tail: int | None = None,
) -> dict[str, Any]:
  empty: dict[str, Any] = {"last": {}, "times": [], "series": {}}
  if not bridge_dir:
    return empty
  path = Path(bridge_dir) / "bars.json"
  if not path.is_file():
    return empty
  data = _read(path) or {}
  all_bars = list(data.get("bars") or [])
  if len(all_bars) < 80:
    return empty
  use_tail = max(80, int(tail) if tail else _FM_TAIL)
  last_t = str(all_bars[-1].get("time") or "")
  key = (str(path), last_t, symbol, timeframe, use_tail)
  cached = _FEAT_CACHE.get(key)
  if cached is not None:
    return cached
  bars = all_bars[-use_tail:]
  try:
    _ensure_host(symbol, timeframe)
    from feature_engine import FeatureMatrix
    from mt5_bridge.history_sync import utc_to_broker_time
    frame = _bars_to_frame(bars)
    if frame is None or len(frame) < 80:
      return empty
    fm = FeatureMatrix(frame, profile="current")
    last = fm.n - 1
    times = [utc_to_broker_time(ts) for ts in fm.index]
    last_map: dict[str, float] = {}
    series: dict[str, list] = {}
    for name, arr in (fm.features or {}).items():
      try:
        val = float(arr[last])
      except (TypeError, ValueError, IndexError):
        continue
      if math.isfinite(val):
        last_map[name] = val
      chunk = []
      for v in arr:
        try:
          fv = float(v)
        except (TypeError, ValueError):
          chunk.append(None)
          continue
        chunk.append(fv if math.isfinite(fv) else None)
      series[name] = chunk
  except Exception:
    return empty
  pack = {"last": last_map, "times": times, "series": series}
  if len(_FEAT_CACHE) > 8:
    _FEAT_CACHE.clear()
  _FEAT_CACHE[key] = pack
  return pack


def _features_from_bars(bridge_dir: Path | None, symbol: str, timeframe: str) -> dict[str, float]:
  return dict(_feature_pack_from_bars(bridge_dir, symbol, timeframe).get("last") or {})


def book_feature_pack(book: dict | None) -> dict[str, Any]:
  book = book or {}
  bdir = Path(str(book.get("bridge_dir") or "")) if book.get("bridge_dir") else None
  pack = _feature_pack_from_bars(
    bdir,
    str(book.get("symbol") or ""),
    str(book.get("timeframe") or ""),
  )
  dumped = _features_from_file(bdir)
  if dumped:
    last = dict(pack.get("last") or {})
    last.update(dumped)
    pack = {**pack, "last": last}
  return pack


def chart_feature_pack(book: dict | None, *, period: str = "today") -> dict[str, Any]:
  """Bars + features for the Now model chart, sliced to D/W/M/ALL."""
  book = book or {}
  bdir = Path(str(book.get("bridge_dir") or "")) if book.get("bridge_dir") else None
  pack = _feature_pack_from_bars(
    bdir,
    str(book.get("symbol") or ""),
    str(book.get("timeframe") or ""),
    tail=_chart_tail_for_period(period),
  )
  dumped = _features_from_file(bdir)
  if dumped:
    last = dict(pack.get("last") or {})
    last.update(dumped)
    pack = {**pack, "last": last}
  return slice_pack_to_period(pack, period)


def book_features(book: dict | None) -> dict[str, float]:
  return dict(book_feature_pack(book).get("last") or {})


def watch_expect_current(
  *,
  model_id: str | None,
  book: dict | None,
  action: str | None = None,
  reason: str | None = None,
  bar_time: Any = None,
  dumped: dict | None = None,
  fills: list | None = None,
  timeframe: str | None = None,
) -> dict[str, Any]:
  strat = load_week_strategy(model_id)
  feats = book_features(book)
  bar_time = bar_time or (book or {}).get("bar_time")
  timeframe = timeframe or (book or {}).get("timeframe") or "M15"
  return format_watch_expect(
    strat, feats, action=action, reason=reason, bar_time=bar_time,
    dumped=dumped, fills=fills, timeframe=timeframe,
  )


def collect_model_lines(
  strat: dict | None,
  *,
  selected: list | None = None,
) -> dict[str, list[dict[str, Any]]]:
  """Chart lines: heaviest per side, or the BUY/SELL rules ticked in Now."""
  by_feat: dict[str, list[dict[str, Any]]] = {}
  seen: set[tuple] = set()
  strat = strat or {}
  wanted: set[tuple] | None = None
  if selected:
    wanted = set()
    for item in selected:
      if not item or len(item) < 3:
        continue
      try:
        wanted.add((str(item[0]), str(item[1]), round(float(item[2]), 4)))
      except (TypeError, ValueError):
        continue
  for side, key in (("B", "long_rules"), ("S", "short_rules")):
    rules = _sorted_rules(strat.get(key))
    if wanted is None:
      top = _heaviest(strat.get(key))
      rules = [top] if top else []
    for rule in rules:
      feat, op, thr, _ = _rule_parts(rule)
      if not feat:
        continue
      thr_r = round(float(thr), 4)
      if wanted is not None and (feat, side, thr_r) not in wanted:
        continue
      sig = (feat, side, op, thr_r)
      if sig in seen:
        continue
      seen.add(sig)
      by_feat.setdefault(feat, []).append({
        "side": side,
        "op": op,
        "thr": float(thr),
        "label": f"{'BUY' if side == 'B' else 'SELL'} {expect_text(rule)}",
      })
  return by_feat


def _collect_watch_lines(model_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
  """feat_key → unique BUY/SELL threshold lines (heaviest rule per side)."""
  by_feat: dict[str, list[dict[str, Any]]] = {}
  seen: set[tuple] = set()
  for mid in model_ids:
    strat = load_week_strategy(mid)
    for side, key in (("B", "long_rules"), ("S", "short_rules")):
      rule = _heaviest(strat.get(key))
      if not rule:
        continue
      feat, op, thr, _ = _rule_parts(rule)
      if not feat:
        continue
      sig = (feat, side, op, round(float(thr), 4))
      if sig in seen:
        continue
      seen.add(sig)
      by_feat.setdefault(feat, []).append({
        "side": side,
        "op": op,
        "thr": float(thr),
        "label": f"{'BUY' if side == 'B' else 'SELL'} {expect_text(rule)}",
      })
  return by_feat


def _parse_hit_time(raw: Any):
  from datetime import datetime as _dt

  if raw is None:
    return None
  if hasattr(raw, "to_pydatetime"):
    try:
      raw = raw.to_pydatetime()
    except Exception:
      pass
  if isinstance(raw, _dt):
    return raw.replace(tzinfo=None) if raw.tzinfo else raw
  s = str(raw).strip()
  if not s:
    return None
  if len(s) >= 10 and s[4] == "." and s[7] == ".":
    s = s.replace(".", "-", 2)
  s = s.replace("T", " ").split("+")[0].replace("Z", "").strip()
  for fmt, n in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16)):
    try:
      return _dt.strptime(s[:n], fmt)
    except ValueError:
      continue
  try:
    return _dt.fromisoformat(s[:19])
  except ValueError:
    return None


def broker_wall_to_display(raw: Any):
  """Broker candle/fill wall clock → Vietnam local for Now charts."""
  parsed = _parse_hit_time(raw)
  if parsed is None:
    return raw
  try:
    from zoneinfo import ZoneInfo
    shown = parsed.replace(tzinfo=ZoneInfo(BROKER_TZ_NAME)).astimezone(
      ZoneInfo(DISPLAY_TZ_NAME),
    )
  except Exception:
    return parsed
  naive = shown.replace(tzinfo=None)
  if hasattr(raw, "tz_localize") or type(raw).__name__ == "Timestamp":
    try:
      import pandas as pd
      return pd.Timestamp(naive)
    except Exception:
      return naive
  return naive


def _hit_result(t: dict | None) -> str | None:
  """WIN / LOSS / BE from profit, R, or stored result."""
  if not t:
    return None
  try:
    p = float(t.get("profit"))
    if p > 1e-9:
      return "WIN"
    if p < -1e-9:
      return "LOSS"
  except (TypeError, ValueError):
    pass
  r_raw = t.get("r")
  if r_raw is None:
    r_raw = t.get("r_multiple")
  try:
    r = float(r_raw)
    if r > 1e-9:
      return "WIN"
    if r < -1e-9:
      return "LOSS"
    return "BE"
  except (TypeError, ValueError):
    pass
  res = str(t.get("result") or "").upper()
  return res if res in ("WIN", "LOSS", "BE") else None


def _times_to_display(times: list) -> list:
  return [broker_wall_to_display(t) for t in times]


def _hits_to_display(hit_times: list | None) -> list:
  out: list = []
  for h in hit_times or []:
    if isinstance(h, dict):
      raw = h.get("time") if h.get("time") is not None else h.get("entry_time")
      exit_raw = h.get("exit_time")
      row = {**h, "time": broker_wall_to_display(raw)}
      if exit_raw:
        row["exit_time"] = broker_wall_to_display(exit_raw)
      out.append(row)
    else:
      out.append(broker_wall_to_display(h))
  return out


def _hit_x_for_axis(raw: Any, times: list):
  """Place a fill on the chart x-axis; skip if outside the visible window."""
  if not times:
    return None
  parsed = _parse_hit_time(raw)
  if parsed is None:
    return None
  lo = _parse_hit_time(times[0])
  hi = _parse_hit_time(times[-1])
  if lo is not None and hi is not None and (parsed < lo or parsed > hi):
    return None
  sample = times[0]
  if isinstance(sample, str):
    span = 15 * 60
    if lo is not None and len(times) > 1:
      nxt = _parse_hit_time(times[1])
      if nxt is not None:
        span = max(60.0, abs((nxt - lo).total_seconds()))
    best = None
    best_d = None
    for t in times:
      pt = _parse_hit_time(t)
      if pt is None:
        continue
      d = abs((pt - parsed).total_seconds())
      if best_d is None or d < best_d:
        best, best_d = t, d
    if best is None or best_d is None or best_d > span:
      return None
    return best
  if hasattr(sample, "tz_localize") or type(sample).__name__ == "Timestamp":
    try:
      import pandas as pd
      return pd.Timestamp(parsed)
    except Exception:
      return parsed
  return parsed


def _hit_mark_label(raw: Any, side: str = "", *, close: bool = False) -> str:
  parsed = _parse_hit_time(raw)
  clock = parsed.strftime("%H:%M") if parsed is not None else ""
  if close:
    return f"X {clock}" if clock else "X"
  tag = "B" if side in ("BUY", "LONG") else ("S" if side in ("SELL", "SHORT") else "")
  if clock and tag:
    return f"{tag} {clock}"
  return clock or tag or "hit"


def _add_hit_vlines(fig, *, times: list, hit_times: list | None) -> None:
  """Open/close verticals plus a hold band colored by WIN (green) / LOSS (red)."""
  win_c, loss_c, be_c = "#0f766e", "#be123c", "#64748b"
  buy_c, sell_c = "#0f766e", "#be123c"
  win_fill, loss_fill, be_fill, open_fill = (
    "rgba(15, 118, 110, 0.18)",
    "rgba(190, 18, 60, 0.16)",
    "rgba(100, 116, 139, 0.12)",
    "rgba(148, 163, 184, 0.10)",
  )
  last_x = times[-1] if times else None
  seen_open: set[str] = set()
  seen_close: set[str] = set()
  for raw in hit_times or []:
    if isinstance(raw, dict):
      t_open = raw.get("time") or raw.get("entry_time") or raw.get("x")
      t_close = raw.get("exit_time")
      side = str(raw.get("side") or raw.get("direction") or "").upper()
      status = str(raw.get("status") or "").upper()
      result = _hit_result(raw)
    else:
      t_open, t_close, side, status, result = raw, None, "", "", None
    x0 = _hit_x_for_axis(t_open, times)
    if x0 is None:
      continue
    closed = bool(t_close) and status != "OPEN"
    x1 = None
    if closed:
      x1 = _hit_x_for_axis(t_close, times)
      if x1 is None:
        parsed = _parse_hit_time(t_close)
        lo = _parse_hit_time(times[0]) if times else None
        hi = _parse_hit_time(times[-1]) if times else None
        if parsed is not None and hi is not None and parsed > hi:
          x1 = last_x
        elif parsed is not None and lo is not None and parsed < lo:
          x1 = times[0]
    elif status == "OPEN":
      x1 = last_x
    if result == "WIN":
      color, fill = win_c, win_fill
    elif result == "LOSS":
      color, fill = loss_c, loss_fill
    elif result == "BE":
      color, fill = be_c, be_fill
    elif status == "OPEN":
      color = buy_c if side in ("BUY", "LONG") else (sell_c if side in ("SELL", "SHORT") else be_c)
      fill = open_fill
    else:
      color = buy_c if side in ("BUY", "LONG") else (sell_c if side in ("SELL", "SHORT") else be_c)
      fill = be_fill
    if x1 is not None and str(x0) != str(x1):
      fig.add_shape(
        type="rect",
        x0=x0, x1=x1, y0=0, y1=1,
        xref="x", yref="paper",
        fillcolor=fill,
        line=dict(width=0),
        layer="below",
      )
    k0 = f"o:{x0}"
    if k0 not in seen_open:
      seen_open.add(k0)
      fig.add_shape(
        type="line",
        x0=x0, x1=x0, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color=color, width=1.5, dash="dot"),
        layer="above",
      )
      fig.add_annotation(
        x=x0, y=1, xref="x", yref="paper",
        text=_hit_mark_label(t_open, side),
        showarrow=False,
        yshift=10,
        font=dict(size=10, color=color),
        xanchor="center",
        yanchor="bottom",
      )
    if closed and x1 is not None:
      k1 = f"c:{x1}"
      if k1 not in seen_close:
        seen_close.add(k1)
        fig.add_shape(
          type="line",
          x0=x1, x1=x1, y0=0, y1=1,
          xref="x", yref="paper",
          line=dict(color=color, width=1.5, dash="dash"),
          layer="above",
        )
        fig.add_annotation(
          x=x1, y=1, xref="x", yref="paper",
          text=_hit_mark_label(t_close, side, close=True),
          showarrow=False,
          yshift=22,
          font=dict(size=10, color=color),
          xanchor="center",
          yanchor="bottom",
        )


def _period_axis_formats(period: str | None) -> tuple[str, str]:
  p = (period or "today").lower().strip()
  if p in ("month", "this_month", "all"):
    return "%m-%d", "%m-%d %H:%M"
  if p in ("week", "this_week"):
    return "%a %H:%M", "%a %H:%M"
  return "%H:%M", "%H:%M"


def build_watch_figure(
  *,
  title: str,
  times: list,
  series: dict[str, list],
  lines_by_feat: dict[str, list[dict[str, Any]]],
  row_h: int = 104,
  hit_times: list | None = None,
  time_axis_title: str = "",
  period: str | None = None,
) -> Any:
  import plotly.graph_objects as go
  from plotly.subplots import make_subplots

  feats = [f for f in lines_by_feat if f in series and any(v is not None for v in series.get(f) or [])]
  if not feats or not times:
    return None
  n = len(feats)
  tickfmt, hoverx = _period_axis_formats(period)
  hover = "%{x|" + hoverx + "}<br>%{y:.3f}<extra>"
  fig = make_subplots(
    rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.045 if n > 1 else 0.08,
    subplot_titles=[_feat_label(f) for f in feats],
  )
  buy_c, sell_c, line_c = "#0f766e", "#be123c", "#2563eb"
  for i, feat in enumerate(feats, start=1):
    y = series.get(feat) or []
    fig.add_trace(
      go.Scatter(
        x=times, y=y, name=_feat_label(feat),
        mode="lines",
        line=dict(color=line_c, width=1.8),
        hovertemplate=hover + _feat_label(feat) + "</extra>",
        showlegend=(i == 1),
      ),
      row=i, col=1,
    )
    if y and y[-1] is not None:
      fig.add_trace(
        go.Scatter(
          x=[times[-1]], y=[y[-1]],
          mode="markers",
          marker=dict(color=line_c, size=8),
          name="now",
          showlegend=False,
          hovertemplate="now %{y:.3f}<extra></extra>",
        ),
        row=i, col=1,
      )
    for line in lines_by_feat.get(feat) or []:
      thr = line.get("thr")
      if thr is None or not times:
        continue
      color = buy_c if line.get("side") == "B" else sell_c
      fig.add_trace(
        go.Scatter(
          x=[times[0], times[-1]],
          y=[float(thr), float(thr)],
          mode="lines",
          line=dict(color=color, width=1.5, dash="dash"),
          name=str(line.get("label") or ""),
          hovertemplate=str(line.get("label") or "") + "<extra></extra>",
          showlegend=False,
        ),
        row=i, col=1,
      )
    fig.update_yaxes(
      showgrid=True, gridcolor="#e2e8f0", zeroline=True, zerolinecolor="#cbd5e1",
      tickfont=dict(size=10), row=i, col=1,
    )
  fig.update_layout(
    height=max(140, int(row_h) * n + 32),
    margin=dict(l=44, r=10, t=54 if hit_times else 28, b=24),
    title=dict(text=title, x=0, xanchor="left", font=dict(size=12)) if title else None,
    template="plotly_white",
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    hovermode="x unified",
    showlegend=False,
  )
  xaxis_kw: dict[str, Any] = {"tickfont": dict(size=10), "tickformat": tickfmt}
  if time_axis_title:
    xaxis_kw["title"] = dict(text=time_axis_title, font=dict(size=11))
  fig.update_xaxes(**xaxis_kw, row=n, col=1)
  _add_hit_vlines(fig, times=times, hit_times=hit_times)
  return fig


def watch_chart_figures(health: dict | None) -> list[tuple[str, Any]]:
  """One figure per Live book, features that models are watching."""
  out: list[tuple[str, Any]] = []
  for book in (health or {}).get("books") or []:
    mids = [str(m.get("model_id") or "") for m in (book.get("models") or []) if m.get("model_id")]
    lines = _collect_watch_lines(mids)
    if not lines:
      continue
    pack = chart_feature_pack(book, period="today")
    title = f"{book.get('symbol') or ''} {book.get('timeframe') or ''} · D"
    fig = build_watch_figure(
      title=title.strip(),
      times=_times_to_display(list(pack.get("times") or [])),
      series=dict(pack.get("series") or {}),
      lines_by_feat=lines,
      time_axis_title=DISPLAY_TZ_LABEL,
      period="today",
    )
    if fig is not None:
      out.append((title.strip(), fig))
  return out


def model_watch_figure(
  *,
  model_id: str | None,
  book: dict | None,
  title: str = "",
  hit_times: list | None = None,
  period: str = "today",
  selected: list | None = None,
) -> Any:
  """Indicator chart for one model's genome over the Now D/W/M/ALL window."""
  strat = load_week_strategy(model_id)
  lines = collect_model_lines(strat, selected=selected)
  if not lines:
    return None
  pack = chart_feature_pack(book, period=period)
  if hit_times is None:
    hit_times = []
    bdir = Path(str((book or {}).get("bridge_dir") or "")) if (book or {}).get("bridge_dir") else None
    if bdir is not None:
      try:
        from journal_view import load_trades
        hit_times = period_fill_marks(load_trades(bdir), model_id=model_id, period=period)
      except Exception:
        hit_times = []
  tag = {"today": "D", "week": "W", "month": "M", "all": "ALL"}.get(
    str(period or "today").lower(), str(period or "D").upper(),
  )
  axis = f"{DISPLAY_TZ_LABEL} · {tag}"
  return build_watch_figure(
    title=title,
    times=_times_to_display(list(pack.get("times") or [])),
    series=dict(pack.get("series") or {}),
    lines_by_feat=lines,
    row_h=96,
    hit_times=_hits_to_display(hit_times),
    time_axis_title=axis,
    period=period,
  )
