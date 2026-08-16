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
    "# AIEdge vs TrainApp — Proof Report",
    "",
    f"Generated: `{report['generated_at']}`",
    "",
    "## Method",
    "",
    s["method"],
    "",
    f"**Claim:** **{s['proof_claim']}** "
    f"(AIEdge {s['aiedge_wins']} · TrainApp {s['trainapp_wins']} · tie {s['ties']})",
    "",
    "## Per desk",
    "",
  ]
  for c in report["desks"]:
    ai = (c.get("aiedge") or {}).get("test") or {}
    va = (c.get("aiedge") or {}).get("validate") or {}
    base = (c.get("trainapp_baseline") or {}).get("metrics") or {}
    raw = (c.get("trainapp_baseline") or {}).get("metrics_raw") or {}
    dec = c.get("decision") or {}
    lines += [
      f"### {c['desk'].upper()} · {c.get('pair')} {c.get('tf')}",
      "",
      f"- **Winner:** {dec.get('winner')} — {dec.get('reason')}",
      f"- AIEdge validate (selection): R={va.get('total_r')} WR={va.get('win_rate_pct')} "
      f"DD={va.get('max_drawdown_r')} score={va.get('robust_score')}",
      f"- AIEdge test (once): R={ai.get('total_r')} WR={ai.get('win_rate_pct')} "
      f"RR={ai.get('avg_rr')} DD={ai.get('max_drawdown_r')} score={ai.get('robust_score')} "
      f"n={ai.get('n_trades')} @ spread {c.get('aiedge_cost_spread_pips')} pip",
      f"- TrainApp-fair (same cost WF): R={base.get('total_r')} WR={base.get('win_rate_pct')} "
      f"DD={base.get('max_drawdown_r')} score={base.get('robust_score')}",
      f"- AIEdge pick: `{(c.get('aiedge') or {}).get('param_key')}`",
      f"- TrainApp recipe: `{(c.get('trainapp_baseline') or {}).get('label')}`",
      "",
    ]
  lines += [
    "## Fairness notes",
    "",
    "- Both sides: identical spreads, identical TEST calendar, causal weekly remine.",
    "- AIEdge never uses TEST for selection (VALIDATE only).",
    "- TrainApp-fair = fixed recommended preset (not the optimistic published grid).",
    "- Published TrainApp rows trained on overlapping 2025-2026 eras are protocol-invalid.",
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
    report = {
      "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
      "system": "AIEdge-v1 WalkForward",
      "protocol": protocol.get("protocol") or {},
      "desks": comparisons,
      "summary": {
        "aiedge_wins": wins,
        "trainapp_wins": losses,
        "ties": ties,
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
          "Both systems use the same causal weekly walk-forward miner and the same "
          "realistic desk spreads on the locked TEST window. TrainApp-fair uses the "
          "fixed recommended recipe (elite_or_quality, 6w). AIEdge selects preset×train_weeks "
          "(+ optional cost-gate) on VALIDATE only, then runs TEST once. Published TrainApp "
          "grids that mined on overlapping 2025-2026 eras are excluded as protocol-invalid."
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
