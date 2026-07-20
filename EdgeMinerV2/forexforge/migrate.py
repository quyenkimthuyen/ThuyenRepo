"""One-shot migration: EdgeMiner1 JSON KB/reports → v2 SQLite + learning dirs."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .contracts import CostModel, InstrumentSpec, JobKind, MetricsPack, Report, RunSpec
from .logging_util import get_logger
from .paths import LEARNING_DIR, RESULTS_DIR, ensure_dirs
from .store import Store

log = get_logger("forexforge.migrate")


def migrate_from_edgeminer1(src_root: Path, *, dry_run: bool = False) -> dict:
  """
  Copy learning/ + import results/reports/*.json into SQLite.
  src_root: path to EdgeMiner1 (or EdgeMiner).
  """
  ensure_dirs()
  src_root = Path(src_root)
  stats = {"kb_copied": 0, "reports_imported": 0, "errors": []}

  src_learning = src_root / "learning"
  if src_learning.exists():
    dest = LEARNING_DIR
    if not dry_run:
      dest.mkdir(parents=True, exist_ok=True)
      for item in src_learning.iterdir():
        target = dest / item.name
        if item.is_dir():
          if target.exists():
            shutil.rmtree(target)
          shutil.copytree(item, target)
        else:
          shutil.copy2(item, target)
        stats["kb_copied"] += 1
    else:
      stats["kb_copied"] = sum(1 for _ in src_learning.rglob("*"))
    log.info("KB copy from %s -> %s (%s)", src_learning, dest, stats["kb_copied"])

  store = Store()
  reports_dir = src_root / "results" / "reports"
  candidates = []
  if reports_dir.exists():
    candidates.extend(sorted(reports_dir.glob("*.json")))
  legacy = src_root / "results" / "backtest_report.json"
  if legacy.exists():
    candidates.append(legacy)

  for path in candidates:
    if path.name == "index.json":
      continue
    try:
      data = json.loads(path.read_text(encoding="utf-8"))
      if "overall_oos" not in data and "epoch_history" not in data:
        continue
      if dry_run:
        stats["reports_imported"] += 1
        continue
      cfg = data.get("config") or {}
      spec = RunSpec(
        kind=JobKind.LEARN if "epoch_history" in data else JobKind.BACKTEST,
        instrument=InstrumentSpec(
          pair=cfg.get("pair", "EUR/USD"),
          timeframe=cfg.get("tf", "H1"),
        ),
        cost=CostModel(
          spread_pips=float(cfg.get("spread_pips", 1.0)),
          slippage_pips=float(cfg.get("slippage_pips", 0.3)),
        ),
        use_kb=bool(cfg.get("use_learning_kb")),
        kb_profile=cfg.get("kb_profile"),
        oos_from=cfg.get("oos_from"),
        oos_to=cfg.get("oos_to"),
        label=f"migrated:{path.stem}",
      )
      oos = data.get("overall_oos") or {}
      report = Report(
        spec=spec,
        data_range=data.get("data_range") or {},
        oos_start=data.get("oos_start"),
        overall_oos=MetricsPack(**oos) if oos else None,
        last_1_year=MetricsPack(**data["last_1_year"]) if data.get("last_1_year") else None,
        constraints_met=data.get("constraints_met") or {},
        weekly_log=data.get("weekly_log") or [],
        trades=[],  # keep migrate light; full trades stay in JSON copy
        holdout_forward=data.get("holdout_forward"),
        last_strategy=data.get("last_strategy"),
        epoch_history=data.get("epoch_history") or [],
        raw=data,
      )
      run_id = store.create_run(spec, status="done")
      store.save_report(run_id, report)
      dest_json = RESULTS_DIR / f"migrated_{path.stem}.json"
      shutil.copy2(path, dest_json)
      stats["reports_imported"] += 1
    except Exception as exc:
      log.exception("Migrate failed for %s", path)
      stats["errors"].append(f"{path.name}: {exc}")

  log.info("Migration done: %s", stats)
  return stats


def main():
  import argparse
  p = argparse.ArgumentParser(description="Migrate EdgeMiner1 artifacts into ForexForge v2")
  p.add_argument("--src", default=r"C:\Work\ThuyenRepo\EdgeMiner1")
  p.add_argument("--dry-run", action="store_true")
  args = p.parse_args()
  print(json.dumps(migrate_from_edgeminer1(Path(args.src), dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
  main()
