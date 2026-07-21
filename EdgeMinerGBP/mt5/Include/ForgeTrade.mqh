//+------------------------------------------------------------------+
//| ForgeTrade.mqh — position sizing & hybrid exit management        |
//+------------------------------------------------------------------+
#ifndef FORGE_TRADE_MQH
#define FORGE_TRADE_MQH

#include "ForgeConfig.mqh"

struct ForgeTradeState
{
  bool     active;
  int      direction;
  double   entry;
  double   sl;
  double   tp;
  double   risk;
  datetime entryTime;
  int      barsHeld;
  bool     partialDone;
  bool     trailActive;
};

double ForgeAdjustEntry(int direction, double rawOpen)
{
  double half = (FORGE_SPREAD_PIPS / 2.0 + FORGE_SLIPPAGE_PIPS) * FORGE_PIP;
  return (direction > 0) ? rawOpen + half : rawOpen - half;
}

double ForgeCalcLots(double riskPct, double riskPrice)
{
  if(riskPrice <= 0) return 0.0;
  double balance = AccountInfoDouble(ACCOUNT_BALANCE);
  double riskMoney = balance * riskPct / 100.0;
  double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
  double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
  if(tickValue <= 0 || tickSize <= 0) return 0.01;
  double moneyPerLot = (riskPrice / tickSize) * tickValue;
  if(moneyPerLot <= 0) return 0.01;
  double lots = riskMoney / moneyPerLot;
  double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
  double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
  double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
  lots = MathFloor(lots / step) * step;
  return MathMax(minLot, MathMin(maxLot, lots));
}

bool ForgeModifySL(ulong ticket, double newSl)
{
  MqlTradeRequest req = {};
  MqlTradeResult res = {};
  if(!PositionSelectByTicket(ticket)) return false;
  req.action = TRADE_ACTION_SLTP;
  req.position = ticket;
  req.symbol = _Symbol;
  req.sl = NormalizeDouble(newSl, _Digits);
  req.tp = PositionGetDouble(POSITION_TP);
  return OrderSend(req, res);
}

void ForgeManageExit(ForgeTradeState &st, ulong ticket)
{
  if(!st.active || !PositionSelectByTicket(ticket)) return;

  double h = iHigh(_Symbol, PERIOD_H1, 0);
  double l = iLow(_Symbol, PERIOD_H1, 0);
  double c = iClose(_Symbol, PERIOD_H1, 0);
  st.barsHeld++;

  if(StringFind(FORGE_EXIT_MODE, "trail") >= 0 || StringFind(FORGE_EXIT_MODE, "hybrid") >= 0)
  {
    if(!st.partialDone)
    {
      if(st.direction > 0 && h >= st.entry + st.risk * FORGE_TRAIL_ACTIVATE_R)
      {
        st.trailActive = true;
        double nsl = h - st.risk * FORGE_TRAIL_DISTANCE_R;
        if(nsl > st.sl) { st.sl = nsl; ForgeModifySL(ticket, st.sl); }
      }
      else if(st.direction < 0 && l <= st.entry - st.risk * FORGE_TRAIL_ACTIVATE_R)
      {
        st.trailActive = true;
        double nsl = l + st.risk * FORGE_TRAIL_DISTANCE_R;
        if(nsl < st.sl) { st.sl = nsl; ForgeModifySL(ticket, st.sl); }
      }
    }
  }

  if(StringFind(FORGE_EXIT_MODE, "partial") >= 0 && !st.partialDone)
  {
    if(st.direction > 0 && h >= st.entry + st.risk * FORGE_PARTIAL_AT_R)
    {
      st.partialDone = true;
      st.sl = st.entry + st.risk * 0.1;
      ForgeModifySL(ticket, st.sl);
    }
    else if(st.direction < 0 && l <= st.entry - st.risk * FORGE_PARTIAL_AT_R)
    {
      st.partialDone = true;
      st.sl = st.entry - st.risk * 0.1;
      ForgeModifySL(ticket, st.sl);
    }
  }

  if(st.barsHeld >= FORGE_MAX_HOLD_BARS)
  {
    MqlTradeRequest req = {};
    MqlTradeResult res = {};
    req.action = TRADE_ACTION_DEAL;
    req.symbol = _Symbol;
    req.volume = PositionGetDouble(POSITION_VOLUME);
    req.type = (st.direction > 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
    req.position = ticket;
    req.price = (st.direction > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    req.deviation = 20;
    if(OrderSend(req, res))
      st.active = false;
  }
}

#endif
