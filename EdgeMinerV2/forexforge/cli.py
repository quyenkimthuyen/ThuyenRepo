"""ForexForge v2 CLI — ff backtest | learn | report | jobs."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from .contracts import CostModel, InstrumentSpec, JobKind, RunSpec
from .data_loader import load_eurusd_h1
from .jobs import run_sync, submit_job
from .leakage import LeakageError
from .paths import RESULTS_DIR, ensure_dirs
from .store import Store
from .wf_runner import execute_run


def _parse_date(s: str | None) -> date | None:
  if not s:
    return None
  return date.fromisoformat(s[:10])


def _add_common(p: argparse.ArgumentParser) -> None:
  p.add_argument("--pair", default="EUR/USD")
  p.add_argument("--tf", default="H1")
  p.add_argument("--spread", type=float, default=1.0)
  p.add_argument("--slippage", type=float, default=0.3)
  p.add_argument("--train-months", type=int, default=3)
  p.add_argument("--data-from", default="2022-01-01")
  p.add_argument("--data-to", default=None)
  p.add_argument("--label", default=None)
  p.add_argument("--bg", action="store_true", help="Run in background process; poll with ff jobs")
  p.add_argument("--quiet", action="store_true")


def cmd_backtest(args: argparse.Namespace) -> int:
  ensure_dirs()
  spec = RunSpec(
    kind=JobKind.BACKTEST,
    instrument=InstrumentSpec(pair=args.pair, timeframe=args.tf),
    cost=CostModel(spread_pips=args.spread, slippage_pips=args.slippage),
    train_months=args.train_months,
    use_kb=not args.no_kb,
    kb_profile=args.kb_profile if not args.no_kb else None,
    kb_epoch=int(args.kb_epoch) if args.kb_epoch and args.kb_epoch != "latest" else (
      "latest" if args.kb_epoch == "latest" else None
    ),
    oos_from=_parse_date(args.oos_from),
    oos_to=_parse_date(args.oos_to),
    data_from=_parse_date(args.data_from),
    data_to=_parse_date(args.data_to),
    holdout_months=args.holdout_months,
    label=args.label,
  )

  if args.bg:
    handle = submit_job(spec, background=True)
    print(f"queued job_id={handle.job_id}")
    return 0

  try:
    df = load_eurusd_h1(args.data_from, args.data_to)
    report = execute_run(df, spec, verbose=not args.quiet)
  except LeakageError as exc:
    print(f"BLOCKED: {exc}", file=sys.stderr)
    return 2

  store = Store()
  run_id = store.create_run(spec, status="done")
  rid = store.save_report(run_id, report)
  out = RESULTS_DIR / f"report_{rid}.json"
  out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

  o = report.overall_oos
  if o:
    print(f"report_id={rid}")
    print(f"trades={o.n_trades} WR={o.win_rate_pct}% RR={o.avg_rr} R={o.total_r} DD={o.max_drawdown_r}R")
  print(f"saved: {out}")
  return 0


def cmd_learn(args: argparse.Namespace) -> int:
  ensure_dirs()
  spec = RunSpec(
    kind=JobKind.LEARN,
    instrument=InstrumentSpec(pair=args.pair, timeframe=args.tf),
    cost=CostModel(spread_pips=args.spread, slippage_pips=args.slippage),
    train_months=args.train_months,
    use_kb=True,
    kb_profile=args.kb_profile,
    data_from=_parse_date(args.data_from),
    data_to=_parse_date(args.data_to or args.until_date),
    epochs=args.epochs,
    label=args.kb_name or args.label,
  )
  if args.bg:
    handle = submit_job(spec, background=True)
    print(f"queued job_id={handle.job_id}")
    return 0

  df = load_eurusd_h1(args.data_from, args.data_to or args.until_date)
  report = execute_run(df, spec, verbose=not args.quiet)
  store = Store()
  run_id = store.create_run(spec, status="done")
  rid = store.save_report(run_id, report)
  print(f"report_id={rid} profile={args.kb_profile} epochs={args.epochs}")
  for m in report.epoch_history:
    print(f"  ep{m['epoch']}: WR={m['win_rate_pct']}% R={m['total_r']} genomes={m['genomes_in_kb']}")
  return 0


def cmd_jobs(args: argparse.Namespace) -> int:
  store = Store()
  if args.job_id:
    run = store.get_run(args.job_id)
    ev = store.latest_event(args.job_id)
    print(json.dumps({"run": run, "latest_event": ev}, indent=2, default=str))
    return 0
  for r in store.list_runs(args.limit):
    print(f"{r['id']}  {r['status']:10}  {r['kind']:8}  {r.get('label') or ''}")
  return 0


def cmd_reports(args: argparse.Namespace) -> int:
  store = Store()
  if args.compare:
    ids = [x.strip() for x in args.compare.split(",") if x.strip()]
    rows = store.compare_reports(ids)
    print(json.dumps(rows, indent=2))
    return 0
  for r in store.list_reports(args.limit):
    kb = "ON" if r["use_kb"] else "OFF"
    print(
      f"{r['id']}  KB={kb:3}  "
      f"WR={r['win_rate_pct']}  RR={r['avg_rr']}  R={r['total_r']}  n={r['n_trades']}"
    )
  return 0


def cmd_paper(args: argparse.Namespace) -> int:
  from .paper_sim import run_paper_tick, load_journal
  mon = run_paper_tick(
    use_kb=not args.no_kb,
    kb_profile=args.kb_profile if not args.no_kb else None,
    spread_pips=args.spread,
    slippage_pips=args.slippage,
  )
  if mon.get("error"):
    print(mon["error"], file=sys.stderr)
    return 1
  print(
    f"week={mon.get('week_start')} trades={mon.get('week_trades_taken')} "
    f"WR={mon.get('week_wr')} R={mon.get('week_total_r')} tick={mon.get('tick_id')}"
  )
  print(f"journal_events={len(load_journal(20))}")
  return 0


def cmd_migrate(args: argparse.Namespace) -> int:
  from pathlib import Path
  from .migrate import migrate_from_edgeminer1
  stats = migrate_from_edgeminer1(Path(args.src), dry_run=args.dry_run)
  print(json.dumps(stats, indent=2))
  return 0 if not stats.get("errors") else 1


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(prog="ff", description="ForexForge v2 research CLI")
  sub = p.add_subparsers(dest="cmd", required=True)

  b = sub.add_parser("backtest", help="Walk-forward backtest")
  _add_common(b)
  b.add_argument("--no-kb", dest="no_kb", action="store_true", help="Disable KB (default)")
  b.add_argument("--kb", dest="no_kb", action="store_false", help="Enable KB")
  b.add_argument("--kb-profile", default="default")
  b.add_argument("--kb-epoch", default=None)
  b.add_argument("--oos-from", default=None)
  b.add_argument("--oos-to", default=None)
  b.add_argument("--holdout-months", type=int, default=0)
  b.set_defaults(func=cmd_backtest, no_kb=True)

  l = sub.add_parser("learn", help="Self-learning multi-epoch")
  _add_common(l)
  l.add_argument("--kb-profile", required=True)
  l.add_argument("--kb-name", default=None)
  l.add_argument("--until-date", default=None)
  l.add_argument("--epochs", type=int, default=3)
  l.set_defaults(func=cmd_learn)

  j = sub.add_parser("jobs", help="List / inspect jobs")
  j.add_argument("job_id", nargs="?", default=None)
  j.add_argument("--limit", type=int, default=20)
  j.set_defaults(func=cmd_jobs)

  r = sub.add_parser("reports", help="List / compare reports")
  r.add_argument("--limit", type=int, default=20)
  r.add_argument("--compare", default=None, help="Comma-separated report ids")
  r.set_defaults(func=cmd_reports)

  paper = sub.add_parser("paper", help="Paper tick (signal + cost-model fill)")
  paper.add_argument("--no-kb", action="store_true", default=True)
  paper.add_argument("--kb", dest="no_kb", action="store_false")
  paper.add_argument("--kb-profile", default="default")
  paper.add_argument("--spread", type=float, default=1.0)
  paper.add_argument("--slippage", type=float, default=0.3)
  paper.set_defaults(func=cmd_paper)

  mig = sub.add_parser("migrate", help="Migrate EdgeMiner1 JSON into v2 store")
  mig.add_argument("--src", default=r"C:\Work\ThuyenRepo\EdgeMiner1")
  mig.add_argument("--dry-run", action="store_true")
  mig.set_defaults(func=cmd_migrate)

  return p


def main(argv: list[str] | None = None) -> int:
  try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
  except Exception:
    pass
  parser = build_parser()
  args = parser.parse_args(argv)
  return args.func(args)


if __name__ == "__main__":
  sys.exit(main())
