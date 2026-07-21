//+------------------------------------------------------------------+
//| ForexForgeEA.mq5 — Expert Advisor from ForexForge Trade Model    |
//| GBP/USD H1 · rules + ML filter · weekly walk-forward config        |
//+------------------------------------------------------------------+
#property copyright "ForexForge"
#property version   "1.00"

#include <Trade/Trade.mqh>
#include "Include/ForgeConfig.mqh"
#include "Include/ForgeFeatures.mqh"
#include "Include/ForgeSignals.mqh"
#include "Include/ForgeTrade.mqh"

input double InpRiskPct      = 1.0;     // Risk % mỗi lệnh
input ulong  InpMagic        = 20260721;
input int    InpMaxSpreadPts = 25;      // Max spread (points), 0=off
input bool   InpAllowShort   = true;
input bool   InpAllowLong    = true;

CTrade       g_trade;
datetime     g_lastBar = 0;
int          g_weekKey = -1;
int          g_tradesThisWeek = 0;
int          g_lastSignalBar = -9999;
ForgeTradeState g_state;

bool IsNewH1Bar()
{
  datetime t = iTime(_Symbol, PERIOD_H1, 0);
  if(t != g_lastBar)
  {
    g_lastBar = t;
    return true;
  }
  return false;
}

void ResetWeekIfNeeded()
{
  int wk = ForgeIsoWeekKey(TimeCurrent());
  if(wk != g_weekKey)
  {
    g_weekKey = wk;
    g_tradesThisWeek = 0;
  }
}

bool SpreadOk()
{
  if(InpMaxSpreadPts <= 0) return true;
  return (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) <= InpMaxSpreadPts;
}

bool HasOpenPosition()
{
  for(int i = PositionsTotal() - 1; i >= 0; i--)
  {
    ulong ticket = PositionGetTicket(i);
    if(!PositionSelectByTicket(ticket)) continue;
    if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
       PositionGetInteger(POSITION_MAGIC) == (long)InpMagic)
      return true;
  }
  return false;
}

ulong FindOurTicket()
{
  for(int i = PositionsTotal() - 1; i >= 0; i--)
  {
    ulong ticket = PositionGetTicket(i);
    if(!PositionSelectByTicket(ticket)) continue;
    if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
       PositionGetInteger(POSITION_MAGIC) == (long)InpMagic)
      return ticket;
  }
  return 0;
}

double ForgeCalcAtrFromSymbol(int shift)
{
  double h[], l[], c[];
  ArraySetAsSeries(h, true);
  ArraySetAsSeries(l, true);
  ArraySetAsSeries(c, true);
  int n = 80;
  if(CopyHigh(_Symbol, PERIOD_H1, shift, n, h) < n) return 0;
  if(CopyLow(_Symbol, PERIOD_H1, shift, n, l) < n) return 0;
  if(CopyClose(_Symbol, PERIOD_H1, shift, n, c) < n) return 0;
  return ForgeCalcAtr(h, l, c, n, 14, 1);
}

bool OpenForgeTrade(int direction)
{
  double atr = ForgeCalcAtrFromSymbol(1);
  if(atr <= 0) return false;

  double rawOpen = iOpen(_Symbol, PERIOD_H1, 0);
  double entry = ForgeAdjustEntry(direction, rawOpen);
  double slDist = FORGE_ATR_MULT * atr;
  double sl, tp;
  if(direction > 0)
  {
    sl = entry - slDist;
    tp = entry + slDist * FORGE_RR;
  }
  else
  {
    sl = entry + slDist;
    tp = entry - slDist * FORGE_RR;
  }

  double lots = ForgeCalcLots(InpRiskPct, slDist);
  if(lots <= 0) return false;

  g_trade.SetExpertMagicNumber(InpMagic);
  g_trade.SetDeviationInPoints(20);
  bool ok = (direction > 0)
    ? g_trade.Buy(lots, _Symbol, 0, sl, tp, FORGE_STRATEGY_NAME)
    : g_trade.Sell(lots, _Symbol, 0, sl, tp, FORGE_STRATEGY_NAME);

  if(ok)
  {
    g_state.active = true;
    g_state.direction = direction;
    g_state.entry = entry;
    g_state.sl = sl;
    g_state.tp = tp;
    g_state.risk = slDist;
    g_state.entryTime = TimeCurrent();
    g_state.barsHeld = 0;
    g_state.partialDone = false;
    g_state.trailActive = false;
    g_tradesThisWeek++;
    g_lastSignalBar = (int)iBarShift(_Symbol, PERIOD_H1, iTime(_Symbol, PERIOD_H1, 1));
    Print("ForexForgeEA: ", (direction > 0 ? "LONG" : "SHORT"),
          " lots=", lots, " SL=", sl, " TP=", tp, " model=", FORGE_MODEL_ID);
  }
  return ok;
}

int OnInit()
{
  if(_Symbol != "GBPUSD")
    Print("Cảnh báo: Trade model được train trên GBP/USD H1, symbol hiện tại: ", _Symbol);
  if(_Period != PERIOD_H1)
    Print("Cảnh báo: EA thiết kế cho H1, chart hiện tại: ", EnumToString((ENUM_TIMEFRAMES)_Period));

  Print("ForexForgeEA loaded | model=", FORGE_MODEL_ID, " | week=", FORGE_WEEK_START,
        " | strategy=", FORGE_STRATEGY_NAME);
  g_trade.SetExpertMagicNumber(InpMagic);
  ResetWeekIfNeeded();
  return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
}

void OnTick()
{
  ResetWeekIfNeeded();

  ulong ticket = FindOurTicket();
  if(ticket > 0)
  {
    g_state.active = true;
    ForgeManageExit(g_state, ticket);
    return;
  }
  g_state.active = false;

  if(!IsNewH1Bar()) return;
  if(!SpreadOk()) return;
  if(HasOpenPosition()) return;
  if(g_tradesThisWeek >= FORGE_MAX_TRADES_WEEK) return;

  int signalBar = 1;
  int barIdx = (int)iBarShift(_Symbol, PERIOD_H1, iTime(_Symbol, PERIOD_H1, signalBar));
  if(barIdx - g_lastSignalBar < FORGE_MIN_BARS_BETWEEN) return;

  int sig = ForgeEvaluateSignal(signalBar);
  if(sig > 0 && !InpAllowLong) sig = 0;
  if(sig < 0 && !InpAllowShort) sig = 0;
  if(sig == 0) return;

  OpenForgeTrade(sig);
}

//+------------------------------------------------------------------+
