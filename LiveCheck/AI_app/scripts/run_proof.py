#!/usr/bin/env python3
"""Run AIEdge proof: protocol-locked mine vs TrainApp baseline (cost-stressed)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiapp.config import RESULTS, get_desk, list_desks, load_protocol  # noqa: E402
from aiapp.optimize.walkforward import run_desk_proof_wf  # noqa: E402


def _md(report: dict) -> str:
  s = report["summary"]
  lines = [
    "# AIEdge vs TrainApp — Proof Report (v2)",
    "",
    f"Generated: `{report['generated_at']}`",
    "",
    "## Verdict",
    "",
    f"**Fair WF claim:** **{s['proof_claim']}** "
    f"(AIEdge {s['aiedge_wins']} · TrainApp {s['trainapp_wins']} · tie {s['ties']})",
    "",
    f"Profitable desks (AIEdge test R>0): **{s.get('aiedge_profitable_desks', 0)}/{s.get('n_desks', 0)}**",
    "",
    "## Method",
    "",
    s["method"],
    "",
    "## Per desk",
    "",
  ]
  for c in report["desks"]:
    ai = (c.get("aiedge") or {}).get("test") or {}
    va = (c.get("aiedge") or {}).get("validate") or {}
    base = (c.get("trainapp_baseline") or {}).get("metrics") or {}
    pub = (c.get("trainapp_published_stressed") or {}).get("metrics") or {}
    dec = c.get("decision") or {}
    lines += [
      f"### {c['desk'].upper()} · {c.get('pair')} {c.get('tf')}",
      "",
      f"- **Winner (fair WF):** {dec.get('winner')} — {dec.get('reason')}",
      f"- AIEdge profitable: {dec.get('aiedge_profitable')} | "
      f"beats fair Total R: {dec.get('beats_fair_total_r')}",
      f"- AIEdge validate: R={va.get('total_r')} WR={va.get('win_rate_pct')} "
      f"DD={va.get('max_drawdown_r')} n={va.get('n_trades')}",
      f"- AIEdge test: R={ai.get('total_r')} WR={ai.get('win_rate_pct')} "
      f"RR={ai.get('avg_rr')} DD={ai.get('max_drawdown_r')} "
      f"n={ai.get('n_trades')} @ {c.get('aiedge_cost_spread_pips')} pip",
      f"- TrainApp-fair: R={base.get('total_r')} WR={base.get('win_rate_pct')} "
      f"DD={base.get('max_drawdown_r')}",
      f"- TrainApp published (cost-stressed, reference only): R={pub.get('total_r')} "
      f"DD={pub.get('max_drawdown_r')} | gap AI−pub={dec.get('vs_published_stressed_total_r')}",
      f"- AIEdge pick: `{(c.get('aiedge') or {}).get('param_key')}`",
      "",
    ]
  lines += [
    "## Fairness notes",
    "",
    "- Primary baseline = TrainApp-fair (same cost WF), not published overlapping-era grids.",
    "- AIEdge never uses TEST for selection.",
    "- Published stressed numbers are shown only as a reference gap to the app UI.",
    "",
  ]
  return "\n".join(lines)


def run(desk_ids: list[str], *, merge_existing: bool = True) -> dict:
  protocol = load_protocol()
  RESULTS.mkdir(parents=True, exist_ok=True)

  by_desk: dict[str, dict] = {}
  if merge_existing and (RESULTS / "proof_report.json").exists():
    try:
      prev = json.loads((RESULTS / "proof_report.json").read_text(encoding="utf-8"))
      for c in prev.get("desks") or []:
        if c.get("desk") and c.get("aiedge") and not c.get("error"):
          by_desk[str(c["desk"])] = c
      print(f"Loaded existing desks: {list(by_desk)}", flush=True)
    except Exception as exc:
      print(f"Could not merge previous proof: {exc}", flush=True)

  for desk_id in desk_ids:
    desk = get_desk(desk_id, protocol)
    print(f"=== AIEdge {desk.id} {desk.pair} {desk.tf} spread={desk.spread_pips} ===", flush=True)
    try:
      comp = run_desk_proof_wf(desk, protocol)
    except Exception as exc:
      print(f"  FAIL: {exc}", flush=True)
      comp = {
        "desk": desk.id,
        "pair": desk.pair,
        "tf": desk.tf,
        "error": str(exc),
        "decision": {"winner": "TrainApp", "reason": f"AIEdge failed: {exc}"},
        "aiedge": None,
        "trainapp_baseline": None,
      }
    by_desk[desk.id] = comp
    if comp.get("aiedge"):
      path = RESULTS / f"model_{desk.id}.json"
      path.write_text(json.dumps(comp["aiedge"], indent=2), encoding="utf-8")
      ai = comp["aiedge"].get("test") or {}
      print(
        f"  validate R={(comp['aiedge'].get('validate') or {}).get('total_r')} | "
        f"test R={ai.get('total_r')} WR={ai.get('win_rate_pct')} DD={ai.get('max_drawdown_r')} "
        f"score={ai.get('robust_score')}",
        flush=True,
      )
      print(
        f"  WINNER: {comp['decision']['winner']} — {comp['decision']['reason']}",
        flush=True,
      )

    # Incremental save after each desk
    comparisons = [by_desk[k] for k in ("e21", "g23", "e31", "g33") if k in by_desk]
    # also include any other desks
    for k, v in by_desk.items():
      if k not in ("e21", "g23", "e31", "g33"):
        comparisons.append(v)
    wins = sum(1 for c in comparisons if (c.get("decision") or {}).get("winner") == "AIEdge")
    losses = sum(1 for c in comparisons if (c.get("decision") or {}).get("winner") == "TrainApp")
    ties = len(comparisons) - wins - losses
    profitable = sum(
      1
      for c in comparisons
      if (c.get("decision") or {}).get("aiedge_profitable")
      or float((((c.get("aiedge") or {}).get("test") or {}).get("total_r") or 0)) > 0
    )
    report = {
      "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
      "system": "AIEdge-v2 WalkForward",
      "protocol": protocol.get("protocol") or {},
      "desks": comparisons,
      "summary": {
        "aiedge_wins": wins,
        "trainapp_wins": losses,
        "ties": ties,
        "n_desks": len(comparisons),
        "aiedge_profitable_desks": profitable,
        "proof_claim": (
          "AIEdge wins on locked protocol"
          if wins > losses
          else (
            "TrainApp wins on locked protocol"
            if losses > wins
            else "Inconclusive"
          )
        ),
        "method": (
          "AIEdge-v2: desk-aware preset search + select_score favoring absolute R under "
          "realistic spreads; soft-fallback never prefers thin (<min_trades) samples; "
          "M5 uses biweekly remine and no aggressive cost-gate. Primary baseline is "
          "TrainApp-fair WF at the same costs."
        ),
      },
    }
    (RESULTS / "proof_report.json").write_text(
      json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    (RESULTS / "PROOF.md").write_text(_md(report), encoding="utf-8")
    print(f"Saved partial proof ({len(comparisons)} desks)", flush=True)

  print("SUMMARY:", report["summary"], flush=True)
  return report


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desks", default="e21,g23,e31,g33")
  ap.add_argument("--no-merge", action="store_true")
  args = ap.parse_args()
  ids = [x.strip() for x in args.desks.split(",") if x.strip()]
  if ids == ["all"]:
    ids = [d.id for d in list_desks()]
  run(ids, merge_existing=not args.no_merge)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
