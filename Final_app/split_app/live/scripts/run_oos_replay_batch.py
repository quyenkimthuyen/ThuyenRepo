#!/usr/bin/env python3
"""Batch Linux replay for full OOS window across all enabled Live books."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from books import group_models_by_book  # noqa: E402
from live_config import RESULTS_DIR  # noqa: E402
from package_store import load_roster  # noqa: E402

OOS_FROM = os.environ.get("LIVE_REPLAY_FROM") or "2026-01-01"
OOS_TO = os.environ.get("LIVE_REPLAY_TO") or "2026-08-07"
PY = sys.executable
REPLAY = LIVE / "scripts" / "run_linux_replay_inline.py"
SEED = LIVE / "scripts" / "seed_mt5_cache.py"
OUT = RESULTS_DIR / "replay_oos_batch.json"


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
  roster = load_roster()
  enabled = [m for m in (roster.get("models") or []) if m.get("enabled")]
  groups = group_models_by_book(enabled)
  if not groups:
    print("No enabled models", flush=True)
    return 1

  results = {"started_at": _now(), "oos_from": OOS_FROM, "oos_to": OOS_TO, "books": []}
  print(f"==== OOS batch replay {OOS_FROM} → {OOS_TO} · {len(groups)} books ====", flush=True)

  for (sym, tf), rows in groups.items():
    print(f"\n## Seed {sym} {tf}", flush=True)
    subprocess.run([PY, str(SEED), "--symbol", sym, "--timeframe", tf], cwd=str(SPLIT), check=False)

    print(f"## Replay {sym} {tf} · models={[r.get('label') for r in rows]}", flush=True)
    t0 = datetime.now().timestamp()
    rc = subprocess.run(
      [
        PY, "-u", str(REPLAY),
        "--symbol", sym, "--timeframe", tf,
        "--from", OOS_FROM, "--to", OOS_TO,
        "--delay-ms", "0",
        "--seed",
        "--progress-every", "25",
      ],
      cwd=str(SPLIT),
    ).returncode
    elapsed = round(datetime.now().timestamp() - t0, 1)
    last = {}
    last_path = RESULTS_DIR / "replay_last.json"
    if last_path.exists():
      try:
        last = json.loads(last_path.read_text(encoding="utf-8"))
      except Exception:
        last = {}
    entry = {
      "symbol": sym,
      "timeframe": tf,
      "rc": rc,
      "elapsed_sec": elapsed,
      "summary": last,
    }
    results["books"].append(entry)
    # per-book archive
    arch = RESULTS_DIR / f"replay_oos_{sym.lower()}_{tf.lower()}.json"
    arch.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"## Done {sym} {tf} rc={rc} elapsed={elapsed}s fills={last.get('n_fills')}", flush=True)

  results["finished_at"] = _now()
  OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(f"\nWrote {OUT}", flush=True)
  ok = all(b.get("rc") == 0 for b in results["books"])
  return 0 if ok else 1


if __name__ == "__main__":
  raise SystemExit(main())
