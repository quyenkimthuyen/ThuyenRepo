#!/usr/bin/env python3
"""Generate MT5 EA that replays walk-forward signal calendar (app-parity backtest)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "mt5" / "frozen" / "best_3m_wf_schedule.json"
OUT_MQ5 = ROOT / "mt5" / "Experts" / "ForgeBest3m_WF.mq5"


def parse_ts(s: str) -> datetime:
  # "2025-01-06 10:00:00" or with tz
  s = s.replace("T", " ").split("+")[0].split(".")[0].strip()
  return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def gen_ea(schedule: dict) -> str:
  meta = schedule.get("meta") or {}
  signals = schedule.get("signals") or []
  n = len(signals)

  # Pack parallel arrays
  lines_y, lines_mo, lines_d, lines_h, lines_mi = [], [], [], [], []
  lines_dir, lines_atr, lines_rr = [], [], []
  lines_exit, lines_tact, lines_tdist, lines_hold = [], [], [], []

  exit_map = {"full": 0, "hybrid": 1, "trail": 2, "partial": 3}

  for sig in signals:
    t = parse_ts(sig["t"])
    lines_y.append(str(t.year))
    lines_mo.append(str(t.month))
    lines_d.append(str(t.day))
    lines_h.append(str(t.hour))
    lines_mi.append(str(t.minute))
    lines_dir.append(str(int(sig["d"])))
    lines_atr.append(f'{float(sig["atr_m"]):.8f}')
    lines_rr.append(f'{float(sig["rr"]):.4f}')
    lines_exit.append(str(exit_map.get(str(sig.get("exit") or "hybrid"), 1)))
    lines_tact.append(f'{float(sig.get("trail_act") or 1.8):.4f}')
    lines_tdist.append(f'{float(sig.get("trail_dist") or 0.6):.4f}')
    lines_hold.append(str(int(sig.get("max_hold") or 36)))

  def arr(name: str, typ: str, vals: list[str], per_line: int = 12) -> str:
    if not vals:
      return f"const int {name}_N = 0;\n"
    chunks = []
    for i in range(0, len(vals), per_line):
      chunks.append(", ".join(vals[i:i + per_line]))
    body = ",\n  ".join(chunks)
    return f"const int {name}_N = {len(vals)};\nconst {typ} {name}[{len(vals)}] = {{\n  {body}\n}};\n"

  overall = meta.get("overall") or {}
  header = f"""//+------------------------------------------------------------------+
//| ForgeBest3m_WF.mq5                                               |
//| Walk-forward signal calendar EA (app-parity backtest)            |
//| Source: Best 3m · KB {meta.get('kb_profile')} ep{meta.get('kb_epoch')} · train {meta.get('train_months')}m |
//| Python export total_r={overall.get('total_r')} WR={overall.get('win_rate_pct')}% n={overall.get('n_trades')} |
//|                                                                  |
//| Mode: On each new H1 bar, if bar[1] matches a scheduled signal,  |
//| enter at current open with that week's ATR/RR/exit params.       |
//| This reproduces app walk-forward entries (with ML) for the OOS   |
//| window. Outside the calendar, no new trades (safety).            |
//+------------------------------------------------------------------+
#property copyright "EdgeMiner2 WF export"
#property version   "2.00"

#include <Trade/Trade.mqh>

input double InpRiskPct = 1.0;
input ulong  InpMagic   = 20260723;
input int    InpSlipPoints = 30;
// App schedule uses canonical UTC-normalized MT5 bars. XM server is often GMT+2/+3.
input int    InpSignalTZOffsetHours = 0;

CTrade trade;
datetime g_last_bar = 0;
int      g_sig_cursor = 0;
int      g_entry_bars_held = 0;
double   g_risk = 0;
int      g_exit_mode = 1;
double   g_trail_act = 1.8;
double   g_trail_dist = 0.6;
int      g_max_hold = 36;

"""

  arrays = "\n".join([
    arr("SIG_Y", "int", lines_y),
    arr("SIG_MO", "int", lines_mo),
    arr("SIG_D", "int", lines_d),
    arr("SIG_H", "int", lines_h),
    arr("SIG_MI", "int", lines_mi),
    arr("SIG_DIR", "int", lines_dir),
    arr("SIG_ATR", "double", lines_atr),
    arr("SIG_RR", "double", lines_rr),
    arr("SIG_EXIT", "int", lines_exit),
    arr("SIG_TACT", "double", lines_tact),
    arr("SIG_TDIST", "double", lines_tdist),
    arr("SIG_HOLD", "int", lines_hold),
  ])

  body = r'''
int OnInit()
{
   trade.SetExpertMagicNumber((int)InpMagic);
   trade.SetDeviationInPoints(InpSlipPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   Print("ForgeBest3m_WF loaded | signals=", SIG_Y_N,
         " | export R≈", ''' + str(overall.get("total_r", 0)) + r''');
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {}

int PositionsByMagic()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionSelectByTicket(PositionGetTicket(i))) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      n++;
   }
   return n;
}

int FindSignalIndex(datetime t)
{
   // Compare broker bar time against canonical UTC schedule + broker offset
   datetime key = t - InpSignalTZOffsetHours * 3600;
   MqlDateTime dt;
   TimeToStruct(key, dt);
   for(int i = MathMax(0, g_sig_cursor - 2); i < SIG_Y_N; i++)
   {
      if(SIG_Y[i] == dt.year && SIG_MO[i] == dt.mon && SIG_D[i] == dt.day &&
         SIG_H[i] == dt.hour && SIG_MI[i] == dt.min)
      {
         g_sig_cursor = i;
         return i;
      }
      datetime st = StringToTime(StringFormat("%04d.%02d.%02d %02d:%02d", SIG_Y[i], SIG_MO[i], SIG_D[i], SIG_H[i], SIG_MI[i]));
      if(st > key + 7 * 24 * 3600)
         break;
   }
   return -1;
}

double AtrAt(int shift)
{
   int bars = 120;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_H1, 0, bars, rates) < bars)
      return 0;
   double atr = rates[bars - 1].high - rates[bars - 1].low;
   double alpha = 1.0 / 14.0;
   for(int i = bars - 2; i >= 0; i--)
   {
      double a = rates[i].high - rates[i].low;
      double b = MathAbs(rates[i].high - rates[i + 1].close);
      double c = MathAbs(rates[i].low - rates[i + 1].close);
      double tr = MathMax(a, MathMax(b, c));
      atr = alpha * tr + (1.0 - alpha) * atr;
   }
   // recompute series then take shift
   double series[];
   ArrayResize(series, bars);
   series[bars - 1] = rates[bars - 1].high - rates[bars - 1].low;
   for(int i = bars - 2; i >= 0; i--)
   {
      double a = rates[i].high - rates[i].low;
      double b = MathAbs(rates[i].high - rates[i + 1].close);
      double c = MathAbs(rates[i].low - rates[i + 1].close);
      double tr = MathMax(a, MathMax(b, c));
      series[i] = alpha * tr + (1.0 - alpha) * series[i + 1];
   }
   return series[shift];
}

double LotsForRisk(double sl_dist)
{
   if(sl_dist <= 0) return 0;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money = balance * InpRiskPct / 100.0;
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_val <= 0 || tick_size <= 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double loss_per_lot = (sl_dist / tick_size) * tick_val;
   if(loss_per_lot <= 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lots = risk_money / loss_per_lot;
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   return MathMax(vmin, MathMin(vmax, lots));
}

void ManageOpen()
{
   if(PositionsByMagic() == 0) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
      int held = (int)((TimeCurrent() - open_time) / PeriodSeconds(PERIOD_H1));
      if(held >= g_max_hold)
      {
         trade.PositionClose(ticket);
         continue;
      }

      long type = PositionGetInteger(POSITION_TYPE);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double risk = g_risk;
      if(risk <= 0) risk = MathAbs(open_price - sl);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      // hybrid / trail
      if(g_exit_mode == 1 || g_exit_mode == 2)
      {
         if(type == POSITION_TYPE_BUY)
         {
            if(bid >= open_price + risk * g_trail_act)
            {
               double nsl = bid - risk * g_trail_dist;
               if(nsl > sl) trade.PositionModify(ticket, nsl, tp);
            }
         }
         else
         {
            if(ask <= open_price - risk * g_trail_act)
            {
               double nsl = ask + risk * g_trail_dist;
               if(sl == 0 || nsl < sl) trade.PositionModify(ticket, nsl, tp);
            }
         }
      }
      // partial: move SL to BE+ after partial_at_r (approx)
      if(g_exit_mode == 3)
      {
         double part_r = 1.5;
         if(type == POSITION_TYPE_BUY && bid >= open_price + risk * part_r)
         {
            double nsl = open_price + risk * 0.1;
            if(nsl > sl) trade.PositionModify(ticket, nsl, tp);
         }
         if(type == POSITION_TYPE_SELL && ask <= open_price - risk * part_r)
         {
            double nsl = open_price - risk * 0.1;
            if(sl == 0 || nsl < sl) trade.PositionModify(ticket, nsl, tp);
         }
      }
   }
}

void OpenFromSignal(int idx)
{
   int dir = SIG_DIR[idx];
   double atr = AtrAt(1);
   if(atr <= 0) return;
   double sl_dist = SIG_ATR[idx] * atr;
   double rr = SIG_RR[idx];
   double price = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (dir > 0) ? price - sl_dist : price + sl_dist;
   double tp = (dir > 0) ? price + sl_dist * rr : price - sl_dist * rr;
   double lots = LotsForRisk(sl_dist);
   if(lots <= 0) return;

   g_risk = sl_dist;
   g_exit_mode = SIG_EXIT[idx];
   g_trail_act = SIG_TACT[idx];
   g_trail_dist = SIG_TDIST[idx];
   g_max_hold = SIG_HOLD[idx];

   bool ok = false;
   if(dir > 0) ok = trade.Buy(lots, _Symbol, price, sl, tp, "WF signal LONG");
   else ok = trade.Sell(lots, _Symbol, price, sl, tp, "WF signal SHORT");
   if(ok)
      Print("WF entry ", (dir > 0 ? "LONG" : "SHORT"), " idx=", idx, " ATR=", atr, " SLd=", sl_dist);
}

void OnTick()
{
   ManageOpen();
   datetime t0 = iTime(_Symbol, PERIOD_H1, 0);
   if(t0 == 0 || t0 == g_last_bar) return;
   g_last_bar = t0;

   if(PositionsByMagic() > 0) return;
   if(SIG_Y_N <= 0) return;

   // Signal was on closed bar [1]; enter now at bar[0] open (matches Python i -> i+1)
   datetime t1 = iTime(_Symbol, PERIOD_H1, 1);
   int idx = FindSignalIndex(t1);
   if(idx < 0) return;
   OpenFromSignal(idx);
}
'''
  return header + arrays + body


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--schedule", type=Path, default=SCHEDULE)
  ap.add_argument("--out", type=Path, default=OUT_MQ5)
  args = ap.parse_args()
  if not args.schedule.exists():
    raise SystemExit(f"Missing schedule: {args.schedule} (run export_wf_schedule.py first)")
  data = json.loads(args.schedule.read_text(encoding="utf-8"))
  code = gen_ea(data)
  args.out.parent.mkdir(parents=True, exist_ok=True)
  args.out.write_text(code, encoding="utf-8")
  print(f"Wrote {args.out} ({len(code)} chars, signals={len(data.get('signals') or [])})")


if __name__ == "__main__":
  main()
