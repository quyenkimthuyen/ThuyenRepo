"""Audit a desk's mining presets for redundant search space.

Why this exists: a preset is only worth its own grid slot when it explores
something no sibling does. The miner treats the two kinds of knob differently
(cores/m15/strategy_miner.py):

  * list knobs  - rr_ratios, atr_multipliers, score_thresholds,
    ml_probability_thresholds, min_rules_matches, min_bars_between,
    session_ranges. Every value is enumerated inside one mining run, so a knob
    that differs only here needs no preset of its own - widen the list instead.
  * scalar knobs - selection_mode, anti_chase_fixed_rsi, anti_chase_fixed_vwap,
    max_trades_per_day, min_trades_per_week, force_side. The miner reads a single
    value, so these can only be explored by adding a preset.

The scalars split further, and the split matters for judging redundancy:

  * identity  - selection_mode, the anti-chase caps, force_side. These decide
    what kind of setup the preset hunts.
  * frequency - max_trades_per_day, min_trades_per_week. These decide how often
    it may fire. A LOWER floor is more permissive, so a preset with a lower floor
    accepts a superset of genomes - it is not automatically dominated.

So the report separates two verdicts. A pair is a plain duplicate when identity
and frequency both match and one's lists are contained in the other's. A pair is
redundant-for-this-objective when identity matches and the lists are contained,
and the only thing the smaller one adds is permission to accept genomes below
--need-tpw, since those can never reach the Total R bar anyway. The second is
what justified cutting the e21 lineup from 8 presets to 4 on 2026-08-31.

--need-tpw comes from the filter arithmetic: WR>55 at RR>2.5 pins EV at 0.925R
per trade, so Total R>100 means n>=108, which over a 34.1-week OOS is 3.17/week.

Usage:
  python scripts/audit_mining_space.py                 # active (curated) presets
  python scripts/audit_mining_space.py --all           # every preset in the family
  python scripts/audit_mining_space.py --desk e21 --prefix eur_r100_
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252.
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

IDENTITY_KEYS = (
  "selection_mode",
  "anti_chase_fixed_rsi",
  "anti_chase_fixed_vwap",
  "force_side",
)
FREQ_KEYS = (
  "max_trades_per_day",
  "min_trades_per_week",
)
SCALAR_KEYS = IDENTITY_KEYS + FREQ_KEYS
LIST_KEYS = (
  "rr_ratios",
  "atr_multipliers",
  "score_thresholds",
  "ml_probability_thresholds",
  "min_rules_matches",
  "min_bars_between",
  "session_ranges",
)


def _load(desk: str):
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk)
  sys.path.insert(0, str(cfg["core_root"]))
  import mining_presets as mp
  from strategy_miner import mining_search_space_from_dict

  return mp, mining_search_space_from_dict


def _values(space, key) -> set:
  raw = getattr(space, key, None) or ()
  return {tuple(v) if isinstance(v, (list, tuple)) else v for v in raw}


def _combos(space) -> int:
  total = 1
  for key in LIST_KEYS:
    total *= max(1, len(_values(space, key)))
  return total


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", default="e21")
  ap.add_argument("--prefix", default="eur_r100_")
  ap.add_argument(
    "--all",
    action="store_true",
    help="audit every preset with the prefix, not just the curated/active list",
  )
  ap.add_argument(
    "--need-tpw",
    type=float,
    default=3.17,
    help="trades/week the Total R bar requires; floors below this cannot pass",
  )
  args = ap.parse_args()

  mp, to_space = _load(args.desk)
  if args.all:
    names = [n for n in mp.PRESETS if n.startswith(args.prefix)]
  else:
    names = list(mp.list_curated_presets(args.desk))
  if not names:
    print(f"Không có preset nào khớp (desk={args.desk}, prefix={args.prefix})")
    return 1

  spaces = {n: to_space(mp.get_preset(n)) for n in names}

  print(f"MINING SPACE AUDIT · desk={args.desk} · {len(names)} preset")
  print()
  print("1) SCALAR — chỉ khám phá được bằng preset riêng")
  head = (
    f'{"preset":<24}{"selection_mode":<21}{"rsi":>6}{"vwap":>6}'
    f'{"/ngày":>7}{"sàn tpw":>9}{"combo":>8}'
  )
  print(head)
  print("-" * len(head))
  for name in names:
    sp = spaces[name]
    print(
      f"{name:<24}{str(sp.selection_mode):<21}"
      f"{float(sp.anti_chase_fixed_rsi):>6.0f}{float(sp.anti_chase_fixed_vwap):>6.1f}"
      f"{int(sp.max_trades_per_day):>7}{float(sp.min_trades_per_week):>9.2f}"
      f"{_combos(sp):>8}"
    )

  ident = {n: tuple(getattr(spaces[n], k) for k in IDENTITY_KEYS) for n in names}
  freq = {n: tuple(getattr(spaces[n], k) for k in FREQ_KEYS) for n in names}

  print()
  print("2) TRÙNG LẶP")
  dupes: list[tuple[str, str]] = []
  dominated: list[tuple[str, str]] = []
  for a, b in itertools.permutations(names, 2):
    if ident[a] != ident[b]:
      continue
    if not all(_values(spaces[a], k) <= _values(spaces[b], k) for k in LIST_KEYS):
      continue
    diff = [k for k in LIST_KEYS if _values(spaces[a], k) != _values(spaces[b], k)]
    where = ", ".join(diff) or "không gian list giống hoàn toàn"
    if freq[a] == freq[b]:
      dupes.append((a, b))
      print(f"   TRÙNG HẲN : {a} ⊆ {b}  ({where})")
    elif float(spaces[a].min_trades_per_week) < args.need_tpw:
      dominated.append((a, b))
      print(
        f"   DƯ THỪA   : {a} ⊆ {b}  ({where}); phần thêm của {a} chỉ là sàn "
        f"{float(spaces[a].min_trades_per_week):.2f} < {args.need_tpw} tpw nên "
        f"không thể chạm mốc Total R"
      )
    else:
      print(
        f"   GIỮ       : {a} ⊆ {b} về list nhưng sàn "
        f"{float(spaces[a].min_trades_per_week):.2f} vẫn ≥ {args.need_tpw} tpw — "
        f"{a} nhận thêm genome mà {b} loại"
      )
  if not dupes and not dominated:
    print("   Không có preset nào dư thừa so với preset khác. ✓")

  print()
  print(f"2b) KHẢ NĂNG CHẠM MỐC — cần tpw ≥ {args.need_tpw}")
  for name in names:
    floor = float(spaces[name].min_trades_per_week)
    verdict = "có" if floor >= args.need_tpw else "KHÔNG — chỉ dùng để chẩn đoán"
    print(f"   {name:<24}sàn {floor:>5.2f}   {verdict}")

  print()
  print("3) ĐỘ PHỦ TỪNG TRỤC LIST (hợp của tất cả preset)")
  for key in LIST_KEYS:
    union: set = set()
    per = []
    for name in names:
      vals = _values(spaces[name], key)
      union |= vals
      per.append(len(vals))
    shared = "chung" if len(set(per)) == 1 else "khác nhau"
    print(f"   {key:<26}{sorted(union)}  ({shared})")

  total = sum(_combos(spaces[n]) for n in names)
  print()
  print(f"4) CHI PHÍ — {total} tổ hợp cho mỗi (tuần train × epoch) trên cả {len(names)} preset")

  return 1 if (dupes or dominated) else 0


if __name__ == "__main__":
  raise SystemExit(main())
