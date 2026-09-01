#!/usr/bin/env python3
"""Report the e21 optimisation config and check the GUI shows the same thing.

The round table in ``scripts/pipeline_m15_tune.py`` is the source of truth; the
GUI reads ``app_settings.json``, which the pipeline only rewrites once a round
actually starts. Between edits those two drift apart, so a run can be launched
while Settings still displays the previous era/preset/OOS window.

``--sync-gui`` pushes a round into Settings through the pipeline's own
``_apply_fine_settings`` (no duplicated logic) and prunes the era catalog down to
that round's eras, which ``merge_learning_eras_into_catalog`` cannot do since it
only ever adds.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env  # noqa: E402

W = 78


def rule(ch: str = "-") -> str:
  return ch * W


def head(title: str) -> None:
  print(f"\n{rule('=')}\n{title}\n{rule('=')}")


def load_pipeline():
  path = ROOT / "scripts" / "pipeline_m15_tune.py"
  spec = importlib.util.spec_from_file_location("pipeline_m15_tune", path)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return mod


def oos_weeks(rnd: dict) -> float:
  return (
    datetime.fromisoformat(rnd["oos_to"]) - datetime.fromisoformat(rnd["oos_from"])
  ).days / 7.0


def report_data(cfg) -> None:
  import config
  import data_loader

  head("1. DỮ LIỆU")
  meta_path = Path(cfg["runtime_root"]) / "data" / "mt5_eurusd_m15_meta.json"
  if meta_path.exists():
    import json
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    print(f"  parquet      : {meta.get('bars')} bar · "
          f"{meta.get('start')} → {meta.get('end')}")
    print(f"  broker       : {meta.get('broker')} · gap_count={meta.get('gap_count')}")
  print(f"  start_date   : {config.DEFAULT_START_DATE}  (desks/e21.yaml)")
  df = data_loader.load_eurusd_m15(config.DEFAULT_START_DATE)
  print(f"  nạp vào train: {len(df)} bar · {df.index[0]} → {df.index[-1]}")


def report_filter(mod) -> float:
  head("2. NGƯỠNG DUYỆT MODEL")
  f = mod.FILTER_WR55
  print(f"  WR > {f['wr_gt']}   RR > {f['rr_gt']}   Total R > {f['total_r_gt']}   "
        f"MaxDD < {f['max_dd_lt']}   n >= {f['n_ge']}")
  ev = (f["wr_gt"] + 0.01) / 100.0 * f["rr_gt"] - (1 - (f["wr_gt"] + 0.01) / 100.0)
  print(f"\n  Ba ngưỡng không độc lập. Đạt WR>55 tại RR>2.5 đã ấn định:")
  print(f"    EV = 0.55 x 2.5 - 0.45 = {ev:.3f} R/trade")
  print(f"    => Total R > {f['total_r_gt']:.0f} tương đương n >= "
        f"{f['total_r_gt'] / ev:.0f} trade")
  return ev


def report_rounds(mod, ev: float) -> None:
  from mining_presets import PRESETS

  head("3. CÁC ROUND SẼ CHẠY")
  total = 0
  for i, rnd in enumerate(mod.E21_WR50_ROUNDS, 1):
    # Mirrors gui/grid_search_engine.build_grid: weeks × presets × (kb_profiles ×
    # epochs), with include_kb_off=False. Each era is one kb_profile, so eras
    # multiply the round — section 5 cross-checks this against the engine.
    n_combo = (
      len(rnd["weeks"]) * len(rnd["presets"]) * rnd["epochs"] * len(rnd["era_keys"])
    )
    total += n_combo
    wk = oos_weeks(rnd)
    need_n = rnd["filter_q"]["total_r_gt"] / ev
    need_tpw = need_n / wk
    floors = {p: float(PRESETS[p].get("min_trades_per_week") or 0.0)
              for p in rnd["presets"]}
    caps = {p: int(PRESETS[p].get("max_trades_per_day") or 0) for p in rnd["presets"]}
    print(f"\n  ROUND {i} — {n_combo} combo   (reset_kb={rnd['reset_kb']})")
    eras = {e["key"]: e for e in (rnd.get("catalog_eras") or [])}
    print(f"    era học    : {len(rnd['era_keys'])} giai đoạn (nhân vào số combo)")
    for k in rnd["era_keys"]:
      e = eras.get(k)
      if not e:
        print(f"      - {k:<12}(THIẾU trong catalog_eras)")
        continue
      months = (
        datetime.fromisoformat(e["learn_until"])
        - datetime.fromisoformat(e["learn_from"])
      ).days / 30.44
      print(f"      - {k:<12}{e['learn_from']} → {e['learn_until']}  "
            f"({months:.1f} tháng)  KB={e['kb_profile']}")
    print(f"    OOS        : {rnd['oos_from']} → {rnd['oos_to']}  ({wk:.1f} tuần)")
    print(f"    weeks      : {rnd['weeks']}     epochs: 1..{rnd['epochs']}")
    print(f"    cần        : n >= {need_n:.0f}  =>  tpw >= {need_tpw:.2f}")
    print(f"    {'preset':<20}{'sàn tpw':>9}{'lệnh/ngày':>11}   đủ tần suất?")
    for p in rnd["presets"]:
      ok = "có" if floors[p] >= need_tpw else "KHÔNG (miner sẽ dừng dưới ngưỡng)"
      print(f"    {p:<20}{floors[p]:>9.1f}{caps[p]:>11}   {ok}")
  print(f"\n  TỔNG: {total} combo")


def report_search_space(mod) -> None:
  from mining_presets import PRESETS

  head("4. KHÔNG GIAN TÌM KIẾM MỖI LẦN REMINE")
  # One list drives both the count and the display so they cannot drift: every key
  # here is enumerated by the miner, min_bars_between and session_ranges included
  # (strategy_miner ~L1372). Cross-check with scripts/audit_mining_space.py.
  keys = ["rr_ratios", "atr_multipliers", "session_ranges", "score_thresholds",
          "ml_probability_thresholds", "min_rules_matches", "min_bars_between"]
  seen: set[str] = set()
  total = 0
  for rnd in mod.E21_WR50_ROUNDS:
    for p in rnd["presets"]:
      if p in seen:
        continue
      seen.add(p)
      sp = PRESETS[p]
      size = 1
      for k in keys:
        v = sp.get(k)
        if isinstance(v, (list, tuple)) and v:
          size *= len(v)
      total += size
      print(f"\n  {p}  ({size} tổ hợp/remine · "
            f"veto_aware={sp.get('anti_chase_score_with_veto')} · "
            f"mode={sp.get('selection_mode')})")
      for k in keys:
        if k in sp:
          print(f"    {k:<28}{sp[k]}")
      print(f"    {'anti_chase RSI / VWAP':<28}"
            f"{sp.get('anti_chase_fixed_rsi')} / {sp.get('anti_chase_fixed_vwap')}")
      print(f"    {'force_side':<28}{sp.get('force_side')}")
  print(f"\n  TỔNG {len(seen)} preset: {total} tổ hợp mỗi (tuần train × epoch)")


def gui_expectations(mod, round_no: int) -> dict:
  from gui.app_settings import TRAIN_WEEK_OPTIONS

  rnd = mod.E21_WR50_ROUNDS[round_no - 1]
  allowed = set(TRAIN_WEEK_OPTIONS)
  weeks = [w for w in rnd["weeks"] if w in allowed] or list(rnd["weeks"])
  return {
    "strategy_train_weeks": weeks,
    "mining_presets": list(rnd["presets"]),
    "learning_era_keys": list(rnd["era_keys"]),
    "learning_loops": int(rnd["epochs"]),
    "backtest_from": rnd["oos_from"],
    "backtest_to": rnd["oos_to"],
  }


def report_gui(mod, round_no: int) -> int:
  from gui.app_settings import load_settings

  head(f"5. ĐỐI CHIẾU GUI  (Settings vs ROUND {round_no})")
  s = load_settings()
  want = gui_expectations(mod, round_no)
  bad = 0
  for key, expect in want.items():
    got = s.get(key)
    same = list(got) == list(expect) if isinstance(expect, list) else got == expect
    if not same:
      bad += 1
    print(f"  [{'OK ' if same else 'LỆCH'}] {key}")
    if not same:
      print(f"         GUI  : {got}")
      print(f"         phải : {expect}")

  rnd = mod.E21_WR50_ROUNDS[round_no - 1]
  want_eras = {e["key"]: e for e in (rnd.get("catalog_eras") or [])}
  catalog = {e["key"]: e for e in (s.get("learning_eras") or [])}
  for key, era in want_eras.items():
    got = catalog.get(key)
    if not got:
      bad += 1
      print(f"  [LỆCH] era '{key}' chưa có trong catalog GUI")
      continue
    for fld in ("learn_from", "learn_until", "oos_from", "oos_to", "kb_profile"):
      if str(got.get(fld) or "")[:10] != str(era.get(fld) or "")[:10]:
        bad += 1
        print(f"  [LỆCH] era '{key}'.{fld}: GUI={got.get(fld)} phải={era.get(fld)}")
  stale = [k for k in catalog if k not in want_eras]
  if stale:
    bad += 1
    print(f"  [LỆCH] catalog GUI còn era không dùng: {stale}")

  # Ground truth for the combo count: ask the engine that actually builds the grid
  # instead of trusting the formula in section 3. Only meaningful once the KB
  # profiles exist, since build_grid drops profiles that cannot cover the OOS.
  want_combo = (
    len(rnd["weeks"]) * len(rnd["presets"]) * rnd["epochs"] * len(rnd["era_keys"])
  )
  try:
    from gui.grid_search_engine import build_grid_from_settings
    specs, _ = build_grid_from_settings(s)
    got_combo = len(specs)
  except Exception as exc:  # engine needs runtime state the report must not create
    print(f"  [ skip ] không dựng được grid để đối chiếu: {exc}")
  else:
    if got_combo == want_combo:
      print(f"  [OK ] số combo engine dựng = {got_combo}")
    else:
      print(f"  [ chú ý ] engine dựng {got_combo} combo, công thức tính "
            f"{want_combo}. Lệch này là bình thường khi KB chưa học "
            f"(build_grid bỏ profile chưa phủ được OOS).")

  print(f"\n  => {'khớp hoàn toàn' if bad == 0 else f'{bad} điểm lệch'}")
  return bad


def sync_gui(mod, round_no: int) -> None:
  from gui.app_settings import load_settings, save_settings, _sanitize_settings

  head(f"ĐỒNG BỘ GUI THEO ROUND {round_no}")
  mod._MODE = "wr50"
  mod._FILLBOOK_ROUND = round_no
  mod._apply_fine_settings("e21")

  # merge_learning_eras_into_catalog only ever adds, so drop the eras this round
  # does not use — otherwise Settings keeps offering windows we deleted.
  rnd = mod.E21_WR50_ROUNDS[round_no - 1]
  keep = {e["key"] for e in (rnd.get("catalog_eras") or [])}
  s = load_settings()
  before = [e["key"] for e in (s.get("learning_eras") or [])]
  s["learning_eras"] = [e for e in (s.get("learning_eras") or []) if e["key"] in keep]
  s["learning_era_keys"] = [k for k in rnd["era_keys"] if k in keep]
  save_settings(_sanitize_settings(s))
  dropped = [k for k in before if k not in keep]
  if dropped:
    print(f"  đã bỏ era khỏi catalog: {dropped}")
  print("  đã ghi app_settings.json")


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", default="e21")
  ap.add_argument("--round", type=int, default=1)
  ap.add_argument("--sync-gui", action="store_true")
  args = ap.parse_args()

  cfg = apply_desk_env(args.desk)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)

  mod = load_pipeline()
  n_rounds = len(mod.E21_WR50_ROUNDS)
  if not 1 <= args.round <= n_rounds:
    print(f"--round phải trong 1..{n_rounds}")
    return 2

  print(rule("="))
  print(f"CẤU HÌNH TỐI ƯU e21 · EUR/USD M15 · "
        f"{datetime.now():%Y-%m-%d %H:%M}")
  print(rule("="))

  report_data(cfg)
  ev = report_filter(mod)
  report_rounds(mod, ev)
  report_search_space(mod)

  if args.sync_gui:
    sync_gui(mod, args.round)
  bad = report_gui(mod, args.round)

  if bad and not args.sync_gui:
    print("\n  Chạy lại với --sync-gui để GUI hiển thị đúng cấu hình sẽ chạy.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
