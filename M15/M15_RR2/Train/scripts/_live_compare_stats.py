"""Compute Live close stats for Trade vs TrainApp2 from on-disk journals."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

TRADE = Path(r"C:\Work\ThuyenRepo\LiveCheck\Trade")
TA2 = Path(r"C:\Work\ThuyenRepo\LiveCheck\TrainApp2")
TA1 = Path(r"C:\Work\ThuyenRepo\LiveCheck\TrainApp")


def _read(p: Path):
  if not p.is_file():
    return None
  return json.loads(p.read_text(encoding="utf-8"))


def summarize(rows: list[dict], *, label: str) -> dict:
  n = len(rows)
  wins = [r for r in rows if float(r.get("profit") or 0) > 0]
  losses = [r for r in rows if float(r.get("profit") or 0) < 0]
  flats = [r for r in rows if float(r.get("profit") or 0) == 0]
  gp = sum(float(r["profit"]) for r in wins)
  gl = abs(sum(float(r["profit"]) for r in losses))
  net = sum(float(r.get("profit") or 0) for r in rows)
  wr = (100.0 * len(wins) / n) if n else 0.0
  pf = (gp / gl) if gl else (float("inf") if gp else 0.0)
  sl = sum(1 for r in rows if str(r.get("reason") or "").lower() == "sl")
  tp = sum(1 for r in rows if str(r.get("reason") or "").lower() == "tp")
  by_day: dict[str, float] = defaultdict(float)
  by_model: dict[str, dict] = defaultdict(lambda: {"n": 0, "net": 0.0, "w": 0, "l": 0})
  for r in rows:
    day = str(r.get("time") or "")[:10].replace(".", "-")
    by_day[day] += float(r.get("profit") or 0)
    mid = str(r.get("model_id") or r.get("magic") or "?")
    by_model[mid]["n"] += 1
    by_model[mid]["net"] += float(r.get("profit") or 0)
    if float(r.get("profit") or 0) > 0:
      by_model[mid]["w"] += 1
    elif float(r.get("profit") or 0) < 0:
      by_model[mid]["l"] += 1
  avg_w = (gp / len(wins)) if wins else 0.0
  avg_l = (gl / len(losses)) if losses else 0.0
  return {
    "label": label,
    "n": n,
    "wins": len(wins),
    "losses": len(losses),
    "flats": len(flats),
    "wr": round(wr, 1),
    "pf": None if pf == float("inf") else round(pf, 2),
    "net": round(net, 2),
    "avg_win": round(avg_w, 2),
    "avg_loss": round(avg_l, 2),
    "sl": sl,
    "tp": tp,
    "by_day": {k: round(v, 2) for k, v in sorted(by_day.items())},
    "by_model": {
      k: {
        "n": v["n"],
        "net": round(v["net"], 2),
        "w": v["w"],
        "l": v["l"],
        "wr": round(100.0 * v["w"] / v["n"], 1) if v["n"] else 0,
      }
      for k, v in sorted(by_model.items(), key=lambda x: x[1]["net"])
    },
  }


def trade_deals() -> list[dict]:
  rows = []
  for name, sym in (
    ("bridge_live_eurusd_m15", "EURUSD"),
    ("bridge_live_gbpusd_m15", "GBPUSD"),
  ):
    data = _read(TRADE / "mt5" / name / "deals.json") or {}
    for d in data.get("deals") or []:
      rows.append({**d, "symbol": d.get("symbol") or sym})
  return rows


def trainapp2_from_comm() -> list[dict]:
  rows = []
  seen = set()
  for desk, log in (
    ("e21", TA2 / "runtime/e21/mt5/bridge_m15e21/comm_log.jsonl"),
    ("g23", TA2 / "runtime/g23/mt5/bridge_m15g23/comm_log.jsonl"),
  ):
    if not log.is_file():
      continue
    for line in log.read_text(encoding="utf-8").splitlines():
      if not line.strip():
        continue
      try:
        ev = json.loads(line)
      except json.JSONDecodeError:
        continue
      if ev.get("event") != "trade_closed":
        continue
      p = ev.get("payload") or {}
      ticket = p.get("ticket")
      if ticket in seen:
        continue
      seen.add(ticket)
      profit = p.get("profit")
      if profit is None:
        # R-only close; skip $ if missing
        profit = 0.0
      rows.append({
        "ticket": ticket,
        "model_id": p.get("model_id"),
        "magic": p.get("magic"),
        "type": p.get("direction"),
        "profit": float(profit or 0),
        "r": p.get("r"),
        "reason": p.get("reason"),
        "time": p.get("exit_time") or p.get("entry_time"),
        "symbol": p.get("symbol"),
        "result": p.get("result"),
        "mode": p.get("mode"),
        "desk": desk,
      })
  return rows


def trainapp1_trades() -> list[dict]:
  rows = []
  for desk, path in (
    ("e21", TA1 / "runtime/e21/mt5/bridge_m15e21/trades.json"),
    ("g23", TA1 / "runtime/g23/mt5/bridge_m15g23/trades.json"),
  ):
    data = _read(path) or {}
    trades = data.get("trades") if isinstance(data, dict) else data
    for t in trades or []:
      if str(t.get("status") or "").upper() != "CLOSED":
        continue
      rows.append({
        "ticket": t.get("ticket"),
        "model_id": t.get("model_id"),
        "magic": t.get("magic"),
        "type": t.get("direction"),
        "profit": float(t.get("profit") or 0),
        "r": t.get("r"),
        "reason": t.get("reason"),
        "time": t.get("exit_time") or t.get("entry_time"),
        "symbol": t.get("symbol"),
        "result": t.get("result"),
        "mode": t.get("mode"),
        "desk": desk,
      })
  return rows


def main():
  td = trade_deals()
  t2 = trainapp2_from_comm()
  t1 = trainapp1_trades()
  print("TRADE", json.dumps(summarize(td, label="Trade"), indent=2))
  print("TA2_COMM", json.dumps(summarize(t2, label="TrainApp2 comm"), indent=2))
  print("TA2_COMM_n", len(t2), "sample", t2[:8])
  print("TA1", json.dumps(summarize(t1, label="TrainApp v1"), indent=2))
  print("TA1_n", len(t1))
  # R stats for TA2
  rs = [float(r["r"]) for r in t2 if r.get("r") is not None]
  if rs:
    print("TA2_R_sum", round(sum(rs), 3), "n", len(rs), "avg", round(sum(rs)/len(rs), 3))


if __name__ == "__main__":
  main()
