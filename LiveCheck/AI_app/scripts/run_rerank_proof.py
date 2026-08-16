#!/usr/bin/env python3
"""Instant proof: AIEdge cost-aware re-rank vs TrainApp filter policy (same grid)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiapp.compare.harness import decide_winner  # noqa: E402
from aiapp.config import RESULTS, get_desk, load_protocol  # noqa: E402
from aiapp.optimize.rerank import (  # noqa: E402
  select_from_trainapp_grid,
  trainapp_filter_policy_baseline,
)


def main() -> int:
  protocol = load_protocol()
  RESULTS.mkdir(parents=True, exist_ok=True)
  desks = []
  for desk_id in ("e21", "g23", "e31", "g33"):
    desk = get_desk(desk_id, protocol)
    print(f"=== rerank {desk.id} ===", flush=True)
    try:
      ai = select_from_trainapp_grid(desk)
      base = trainapp_filter_policy_baseline(desk)
      dec = decide_winner(ai.get("test") or {}, base)
      print(
        f"  winner={dec['winner']} AIEdge R={ai['test'].get('total_r')} "
        f"TrainApp R={base['metrics'].get('total_r')}",
        flush=True,
      )
      desks.append(
        {
          "desk": desk.id,
          "pair": desk.pair,
          "tf": desk.tf,
          "aiedge": ai,
          "trainapp_baseline": base,
          "decision": dec,
        }
      )
    except Exception as exc:
      print(f"  FAIL {exc}", flush=True)
      desks.append(
        {
          "desk": desk.id,
          "error": str(exc),
          "decision": {"winner": "TrainApp", "reason": str(exc)},
        }
      )

  wins = sum(1 for d in desks if (d.get("decision") or {}).get("winner") == "AIEdge")
  losses = sum(1 for d in desks if (d.get("decision") or {}).get("winner") == "TrainApp")
  report = {
    "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "system": "AIEdge-CostAwareReRank",
    "desks": desks,
    "summary": {
      "aiedge_wins": wins,
      "trainapp_wins": losses,
      "proof_claim": (
        "AIEdge wins cost-aware re-rank"
        if wins > losses
        else ("TrainApp wins" if losses > wins else "Inconclusive")
      ),
      "method": (
        "Same TrainApp grid rows. AIEdge ranks by spread-stressed robust_score; "
        "TrainApp baseline uses user filter WR>50 RR>2.5 R>100 DD<10 else best Total R. "
        "Both evaluated after identical cost stress."
      ),
    },
  }
  (RESULTS / "rerank_proof.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
  lines = [
    "# AIEdge Cost-Aware Re-Rank Proof",
    "",
    f"Generated: `{report['generated_at']}`",
    "",
    report["summary"]["method"],
    "",
    f"**Claim:** **{report['summary']['proof_claim']}** (AIEdge {wins} · TrainApp {losses})",
    "",
  ]
  for d in desks:
    if d.get("error"):
      lines += [f"### {d['desk']}", "", f"Error: {d['error']}", ""]
      continue
    ai = (d.get("aiedge") or {}).get("test") or {}
    base = (d.get("trainapp_baseline") or {}).get("metrics") or {}
    dec = d.get("decision") or {}
    lines += [
      f"### {d['desk'].upper()}",
      "",
      f"- Winner: {dec.get('winner')} — {dec.get('reason')}",
      f"- AIEdge stressed: R={ai.get('total_r')} score={ai.get('robust_score')} DD={ai.get('max_drawdown_r')}",
      f"- TrainApp stressed: R={base.get('total_r')} score={base.get('robust_score')} DD={base.get('max_drawdown_r')}",
      "",
    ]
  (RESULTS / "RERANK_PROOF.md").write_text("\n".join(lines), encoding="utf-8")
  print("SUMMARY", report["summary"], flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
