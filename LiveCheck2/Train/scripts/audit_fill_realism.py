#!/usr/bin/env python
"""Đối chiếu mô hình khớp giá của backtest với cách MT5 khớp thật.

Ba việc, mỗi việc trả lời một câu hỏi khác nhau:

1. `spread` — spread thật XM theo giờ broker so với hằng số cấu hình. Đọc
   spread_points mà EA ghi vào bars.json, tức số của chính broker đang giao dịch.

2. `fill` — chạy cùng một bộ signal qua hai engine: `backtest_mined` hiện tại và
   một engine dựng theo đúng ngữ nghĩa MT5, rồi so từng lệnh. Ngữ nghĩa MT5:
   BUY vào ở Ask và SL/TP so với Bid; SELL vào ở Bid và SL/TP so với Ask; TP là
   limit nên khớp đúng giá, SL là stop nên khớp có trượt.

3. `rollover` — lệnh nào đang mở vắt qua giờ broker 00h, là giờ spread giãn
   nhiều nhất, và trong số đó lệnh SELL nào có SL nằm trong vùng mà spread thật
   đã đủ chạm nhưng spread cấu hình thì chưa.

  python scripts/audit_fill_realism.py --desk e21
  python scripts/audit_fill_realism.py --desk e21 --only spread
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))


def _bind(desk: str) -> dict:
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk)
  core_root = str(cfg["core_root"])
  if core_root not in sys.path:
    sys.path.insert(0, core_root)
  return cfg


# --------------------------------------------------------------------------- #
# 1. Spread thật của broker
# --------------------------------------------------------------------------- #

def audit_spread(desk: str, cfg: dict) -> dict:
  from config import DEFAULT_SPREAD_PIPS

  bridge = sorted(Path(cfg["runtime_root"], "mt5").glob("bridge_*/bars.json"))
  bridge = [p for p in bridge if "_sim" not in p.parent.name]
  if not bridge:
    print("  không tìm thấy bars.json của bridge — bỏ qua")
    return {}
  path = bridge[0]
  raw = json.loads(path.read_text(encoding="utf-8"))
  bars = raw.get("bars") if isinstance(raw, dict) else raw

  by_hour: dict[int, list[float]] = defaultdict(list)
  every: list[float] = []
  for b in bars:
    pts = b.get("spread_points")
    if pts is None:
      continue
    pips = float(pts) / 10.0
    every.append(pips)
    stamp = str(b.get("time") or b.get("bar_time") or "")
    try:
      hour = int(stamp.split(" ")[1].split(":")[0])
    except (IndexError, ValueError):
      continue
    by_hour[hour].append(pips)

  if not every:
    print("  bars.json không có spread_points — bỏ qua")
    return {}

  cfgd = float(DEFAULT_SPREAD_PIPS)
  srt = sorted(every)

  def pct(p: float) -> float:
    return srt[min(len(srt) - 1, int(p * len(srt)))]

  worst = max(by_hour, key=lambda h: st.median(by_hour[h]))
  over = sum(1 for x in every if x > cfgd)

  print(f"  nguồn: {path.relative_to(ROOT)} · {len(every)} bar · giờ broker")
  print(f"  cấu hình spread_pips = {cfgd}")
  print(f"  thật: median={pct(.5):.1f} mean={st.fmean(every):.2f} p90={pct(.9):.1f} "
        f"p99={pct(.99):.1f} max={max(every):.1f}")
  print(f"  tỷ lệ bar vượt cấu hình: {over / len(every) * 100:.1f}%")
  print(f"  giờ tệ nhất: broker {worst:02d}h · median={st.median(by_hour[worst]):.1f} "
        f"({st.median(by_hour[worst]) / cfgd:.1f}× cấu hình)")
  quiet = [h for h in by_hour if h != worst]
  quiet_med = st.median([st.median(by_hour[h]) for h in quiet])
  print(f"  23 giờ còn lại: median={quiet_med:.1f} ({quiet_med / cfgd:.2f}× cấu hình)")
  return {
    "configured": cfgd,
    "median": pct(.5),
    "p90": pct(.9),
    "worst_hour": worst,
    "worst_hour_median": st.median(by_hour[worst]),
    "quiet_median": quiet_med,
    "by_hour": {h: st.median(v) for h, v in sorted(by_hour.items())},
  }


# --------------------------------------------------------------------------- #
# 2. Engine khớp giá — cùng hợp đồng với backtest_mined
# --------------------------------------------------------------------------- #

def _legacy_mid_entry(raw, direction, spread_pips, slippage_pips):
  """Quy ước mid cũ (trước 2026-08-31): lệch nửa spread quanh Bid."""
  from execution import slippage_price, spread_price
  half = spread_price(spread_pips) * 0.5
  slip = slippage_price(slippage_pips)
  return raw + (half + slip) if int(direction) == 1 else raw - (half + slip)


def _legacy_double_charge_exit(level, direction, spread_pips, slippage_pips):
  """Giá ra cũ: trừ thêm nửa spread + slip lên mức SL/TP đã gồm spread."""
  from execution import slippage_price, spread_price
  half = spread_price(spread_pips) * 0.5
  slip = slippage_price(slippage_pips)
  delta = half + slip
  return level - delta if int(direction) == 1 else level + delta


def backtest_live_faithful(
  fm, strat, signals, start_idx, end_idx, spread_pips, slippage_pips,
  *, live_entry: bool = True, live_exit: bool = True,
):
  """Cùng ngữ nghĩa Bid/Ask với `backtest_mined`.

  Cờ `live_entry` / `live_exit` tắt từng phần để so với quy ước mid cũ
  (nửa spread + phí ra hai lần) — chỉ dùng cho phép đo lịch sử, không phải
  engine chạy live.
  """
  from strategy_miner import Trade, _is_chase_entry, backtest_mined
  from execution import (
    hit_sl_tp, manage_quote_high, manage_quote_low, market_exit_price,
    plan_levels,
  )
  from mt5_bridge.history_sync import utc_to_broker_time

  if live_entry and live_exit:
    return backtest_mined(
      fm, strat, signals, start_idx, end_idx,
      spread_pips=spread_pips, slippage_pips=slippage_pips,
    )

  if end_idx is None:
    end_idx = fm.n
  o, h, l, c, atr_v = fm.open, fm.high, fm.low, fm.close, fm.atr

  trades: list = []
  i = max(start_idx, fm.warmup)
  in_trade = False
  direction = entry_fill = sl = tp = risk = 0.0
  entry_idx = trail_active = 0.0
  per_day: dict[str, int] = {}

  while i < end_idx - 1:
    if in_trade:
      qh = manage_quote_high(h[i], int(direction), spread_pips)
      ql = manage_quote_low(l[i], int(direction), spread_pips)
      if strat.exit_mode in ("trail", "hybrid") and not trail_active:
        act = strat.trail_activate_r
        if direction == 1 and qh >= entry_fill + risk * act:
          trail_active = 1.0
          sl = max(sl, qh - risk * strat.trail_distance_r)
        elif direction == -1 and ql <= entry_fill - risk * act:
          trail_active = 1.0
          sl = min(sl, ql + risk * strat.trail_distance_r)

      reason, fill_px = hit_sl_tp(
        int(direction), h[i], l[i], sl, tp, spread_pips, slippage_pips,
      )
      hit_sl = reason == "sl"
      hit_tp = reason == "tp"
      exit_fill = fill_px
      timeout = (i - entry_idx) >= strat.max_hold_bars
      if hit_sl or hit_tp or timeout:
        close_reason = "tp" if hit_tp else ("trail" if trail_active and hit_sl else "sl")
        if not hit_sl and not hit_tp:
          close_reason = "timeout"
          exit_fill = market_exit_price(
            c[i], int(direction), spread_pips, slippage_pips,
          )
        if not live_exit:
          exit_fill = _legacy_double_charge_exit(
            float(exit_fill), int(direction), spread_pips, slippage_pips,
          )
        pnl_r = (exit_fill - entry_fill) * direction / risk if risk > 0 else 0.0
        trades.append(Trade(
          fm.index[int(entry_idx)], fm.index[i], int(direction),
          entry_fill, float(exit_fill), sl, tp, pnl_r * risk * 10000, pnl_r, close_reason,
        ))
        in_trade = False
        trail_active = 0.0
      i += 1
      continue

    sig = signals[i]
    if sig != 0:
      av = atr_v[i]
      if np.isnan(av) or av <= 0:
        i += 1
        continue
      if _is_chase_entry(fm, strat, i, int(sig)):
        i += 1
        continue
      entry_idx = i + 1
      if entry_idx >= end_idx:
        break
      day = utc_to_broker_time(fm.index[entry_idx]).strftime("%Y-%m-%d")
      if per_day.get(day, 0) >= strat.max_trades_per_day:
        i += 1
        continue

      direction = float(sig)
      if live_entry:
        entry_fill, sl, tp, risk = plan_levels(
          o[entry_idx], int(direction), av, strat.atr_mult_sl, strat.rr_ratio,
          spread_pips, slippage_pips,
        )
      else:
        entry_fill = _legacy_mid_entry(
          o[entry_idx], int(direction), spread_pips, slippage_pips,
        )
        from execution import atr_stop_distance
        risk = atr_stop_distance(av, strat.atr_mult_sl, spread_pips)
        if direction == 1:
          sl, tp = entry_fill - risk, entry_fill + risk * strat.rr_ratio
        else:
          sl, tp = entry_fill + risk, entry_fill - risk * strat.rr_ratio
      in_trade = True
      trail_active = 0.0
      per_day[day] = per_day.get(day, 0) + 1
      i = entry_idx
      continue
    i += 1

  return trades


def _load_oos(oos_from: str, oos_to: str):
  from data_loader import load_eurusd_m15
  from feature_engine import FeatureMatrix
  import pandas as pd

  df = load_eurusd_m15("2024-01-01")
  fm = FeatureMatrix(df)
  i0 = int(df.index.searchsorted(pd.Timestamp(oos_from)))
  i1 = int(df.index.searchsorted(pd.Timestamp(oos_to)))
  return fm, df, i0, i1


def _synthetic_strategy(atr_mult: float, rr: float, spacing: int):
  """Strategy không luật, chỉ giữ các tham số điều khiển mức SL/TP.

  Phép đo này so hai engine khớp giá trên *cùng* một bộ signal, nên nguồn signal
  không đi vào kết quả — chênh lệch chỉ đến từ số học khớp giá. Dùng signal tổng
  hợp thay vì mine lại vừa bỏ được nhiễu genome khỏi phép đo, vừa khỏi phải chạy
  lại tiến trình mine tốn CPU.
  """
  from strategy_miner import MinedStrategy

  return MinedStrategy(
    atr_mult_sl=atr_mult, rr_ratio=rr, max_hold_bars=96,
    min_bars_between=spacing, max_trades_per_day=4,
    session_filter=False, exit_mode="full", anti_chase=False,
  )


def _synthetic_signals(n: int, i0: int, i1: int, spacing: int):
  """Long/short xen kẽ, cách nhau `spacing` bar, chỉ trong cửa sổ OOS."""
  sig = np.zeros(n, dtype=np.int8)
  side = 1
  for k in range(i0, i1, spacing):
    sig[k] = side
    side = -side
  return sig


def audit_fill(desk: str, cfg: dict, args) -> dict:
  from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
  from execution import PIP
  from strategy import compute_metrics
  from strategy_miner import backtest_mined

  spread, slip = float(DEFAULT_SPREAD_PIPS), float(DEFAULT_SLIPPAGE_PIPS)
  fm, df, i0, i1 = _load_oos(args.oos_from, args.oos_to)
  atr_oos = fm.atr[i0:i1]
  atr_oos = atr_oos[~np.isnan(atr_oos)]
  atr_med = float(np.median(atr_oos)) / PIP
  print(f"  cửa sổ {args.oos_from} → {args.oos_to} · {i1 - i0} bar · "
        f"ATR median {atr_med:.2f} pip · spread {spread} slip {slip}")
  print()

  # Dải tham số đúng bằng dải mà 4 preset e21 đang quét.
  grid = [(a, r) for a in (1.05, 1.2, 1.35) for r in (2.6, 2.8, 3.2)]
  rows = []
  for atr_mult, rr in grid:
    strat = _synthetic_strategy(atr_mult, rr, args.spacing)
    sig = _synthetic_signals(fm.n, i0, i1, args.spacing)
    cur = backtest_mined(fm, strat, sig, i0, i1, spread_pips=spread, slippage_pips=slip)
    # Bậc thang để tách nguyên nhân: mirror ≈ engine hiện tại, rồi sửa từng phần.
    mirror = backtest_live_faithful(
      fm, strat, sig, i0, i1, spread, slip, live_entry=False, live_exit=False)
    exit_only = backtest_live_faithful(
      fm, strat, sig, i0, i1, spread, slip, live_entry=False, live_exit=True)
    liv = backtest_live_faithful(fm, strat, sig, i0, i1, spread, slip)
    mc, mm, me, ml = (compute_metrics(x) for x in (cur, mirror, exit_only, liv))
    if not mc["n_trades"] or not ml["n_trades"]:
      continue
    row = {
      "atr_mult": atr_mult, "rr": rr,
      "cur_n": mc["n_trades"], "cur_wr": mc["win_rate"] * 100, "cur_r": mc["total_r"],
      "mirror_r": mm["total_r"],
      "liv_n": ml["n_trades"], "liv_wr": ml["win_rate"] * 100, "liv_r": ml["total_r"],
      "gap_total": mc["total_r"] - ml["total_r"],
      "gap_exit": mm["total_r"] - me["total_r"],
      "gap_entry": me["total_r"] - ml["total_r"],
      "r_per_trade_gap": (mc["total_r"] - ml["total_r"]) / max(1, mc["n_trades"]),
    }
    rows.append(row)
    print(f"  ATR×{atr_mult} RR{rr}: hiện tại n={mc['n_trades']:>3} "
          f"WR={mc['win_rate']*100:5.2f}% R={mc['total_r']:+8.2f}   "
          f"đúng-live n={ml['n_trades']:>3} WR={ml['win_rate']*100:5.2f}% "
          f"R={ml['total_r']:+8.2f}   lệch R={row['gap_total']:+7.2f} "
          f"({row['r_per_trade_gap']:+.4f}R/lệnh)  "
          f"[phí ra 2 lần {row['gap_exit']:+6.2f} · neo giá vào {row['gap_entry']:+6.2f}]")

  if rows:
    dr = [r["gap_total"] for r in rows]
    dw = [r["cur_wr"] - r["liv_wr"] for r in rows]
    dpt = [r["r_per_trade_gap"] for r in rows]
    de = [r["gap_exit"] for r in rows]
    da = [r["gap_entry"] for r in rows]
    mism = max(abs(r["cur_r"] - r["mirror_r"]) for r in rows)
    print()
    print(f"  kiểm tra: engine mô phỏng lệch engine thật tối đa {mism:.2f} R "
          f"(0 nghĩa là mô phỏng đúng)")
    print(f"  lệch tổng R (hiện tại − đúng-live) qua {len(rows)} cấu hình: "
          f"mean={st.fmean(dr):+.2f} min={min(dr):+.2f} max={max(dr):+.2f}")
    print(f"  lệch mỗi lệnh: mean={st.fmean(dpt):+.4f}R "
          f"min={min(dpt):+.4f} max={max(dpt):+.4f}")
    print(f"  lệch WR (điểm): mean={st.fmean(dw):+.2f} min={min(dw):+.2f} max={max(dw):+.2f}")
    print()
    print("  tách nguyên nhân (tổng R):")
    print(f"    tính phí spread hai lần khi ra: mean={st.fmean(de):+.2f} "
          f"min={min(de):+.2f} max={max(de):+.2f}")
    print(f"    neo giá vào theo mid thay vì Ask/Bid: mean={st.fmean(da):+.2f} "
          f"min={min(da):+.2f} max={max(da):+.2f}")
  return {"atr_median_pips": atr_med, "rows": rows}


# --------------------------------------------------------------------------- #
# 3. Rủi ro giữ lệnh vắt qua giờ rollover
# --------------------------------------------------------------------------- #

def audit_rollover(desk: str, cfg: dict, args, spread_info: dict) -> dict:
  from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
  from execution import PIP
  from mt5_bridge.history_sync import utc_to_broker_time
  from strategy_miner import backtest_mined

  if not spread_info:
    print("  cần số liệu spread — bỏ qua")
    return {}
  worst_h = int(spread_info["worst_hour"])
  real = float(spread_info["worst_hour_median"])
  cfgd = float(DEFAULT_SPREAD_PIPS)
  gap = (real - cfgd) * PIP
  if gap <= 0:
    print("  giờ tệ nhất không rộng hơn cấu hình — không có rủi ro")
    return {}

  spread, slip = cfgd, float(DEFAULT_SLIPPAGE_PIPS)
  fm, df, i0, i1 = _load_oos(args.oos_from, args.oos_to)
  strat = _synthetic_strategy(1.2, 2.8, args.spacing)
  sig = _synthetic_signals(fm.n, i0, i1, args.spacing)
  trades = backtest_mined(fm, strat, sig, i0, i1, spread_pips=spread, slippage_pips=slip)

  broker_hours = np.array([utc_to_broker_time(t).hour for t in fm.index])
  idx = fm.index
  spans = exposed = flip = 0
  for t in trades:
    a = int(idx.searchsorted(t.entry_time))
    b = int(idx.searchsorted(t.exit_time))
    hrs = broker_hours[a:b + 1]
    if worst_h not in set(hrs.tolist()):
      continue
    spans += 1
    if t.direction != -1:
      continue
    exposed += 1
    # SELL: SL đối chiếu Ask. Với spread thật rộng hơn, Ask cao hơn `gap`, nên
    # mọi bar mà high + real_spread >= SL nhưng high + cfg_spread < SL là bar
    # backtest cho sống mà live đã cắt.
    for k in range(a, min(b + 1, len(idx))):
      if broker_hours[k] != worst_h:
        continue
      ask_cfg = fm.high[k] + cfgd * PIP
      ask_real = fm.high[k] + real * PIP
      if ask_cfg < t.sl <= ask_real:
        flip += 1
        break

  print(f"  giờ rollover = broker {worst_h:02d}h · spread thật {real:.1f} vs cấu hình {cfgd:.1f} pip")
  print(f"  lệnh giữ vắt qua giờ đó: {spans}/{len(trades)} "
        f"({spans / max(1, len(trades)) * 100:.0f}%) — max_hold={strat.max_hold_bars} bar "
        f"= {strat.max_hold_bars * 15 / 60:.0f} giờ")
  print(f"  trong đó SELL (SL đối chiếu Ask): {exposed}")
  print(f"  SELL mà backtest cho sống nhưng spread thật đã chạm SL: {flip}")
  return {"trades": len(trades), "spans": spans, "sell_exposed": exposed, "flipped": flip}


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", default="e21")
  ap.add_argument("--spacing", type=int, default=40,
                  help="Khoảng cách bar giữa hai signal tổng hợp")
  ap.add_argument("--oos-from", default="2026-01-01")
  ap.add_argument("--oos-to", default="2026-08-28")
  ap.add_argument("--only", default="", help="spread | fill | rollover")
  args = ap.parse_args()

  cfg = _bind(args.desk)
  only = args.only.strip()
  out: dict = {}

  if only in ("", "spread", "rollover"):
    print("=== 1. Spread thật của broker vs cấu hình ===")
    out["spread"] = audit_spread(args.desk, cfg)
    print()
  if only in ("", "fill"):
    print("=== 2. Engine hiện tại vs engine đúng-live (cùng bộ signal) ===")
    out["fill"] = audit_fill(args.desk, cfg, args)
    print()
  if only in ("", "rollover"):
    print("=== 3. Lệnh giữ vắt qua giờ spread giãn ===")
    out["rollover"] = audit_rollover(args.desk, cfg, args, out.get("spread") or {})
    print()

  dest = ROOT / "reports" / f"fill_realism_{args.desk}.json"
  dest.parent.mkdir(parents=True, exist_ok=True)
  dest.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
  print(f"Đã ghi {dest}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
