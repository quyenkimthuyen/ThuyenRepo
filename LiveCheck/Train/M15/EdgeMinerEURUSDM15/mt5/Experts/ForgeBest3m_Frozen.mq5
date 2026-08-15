//+------------------------------------------------------------------+
//| ForgeBest3m_Frozen.mq5                                           |
//| Frozen EA from EdgeMiner2 Trade Model "Best 3m"                  |
//| Source: last_strategy Forge RR3 hybrid 4L2S price+bb #0998       |
//|                                                                  |
//| IMPORTANT                                                        |
//| - Static rules only (no weekly re-mine, no ML, no KB)            |
//| - Will NOT reproduce app walk-forward ~+134R                     |
//| - Designed for EURUSD H1                                         |
//|                                                                  |
//| Install: copy to MQL5/Experts/, compile in MetaEditor            |
//+------------------------------------------------------------------+
#property copyright "EdgeMiner2 freeze"
#property version   "1.00"

#include <Trade/Trade.mqh>

//---------------- Input (frozen defaults from best_3m_frozen.json) --
input group "=== Frozen strategy ==="
input double InpScoreThreshold   = 0.8291058051065867;
input double InpAtrMultSL        = 0.7384794237626883;
input double InpRR               = 3.0;
input int    InpMinRulesMatch    = 2;
input int    InpMaxTradesPerWeek = 2;
input int    InpMinBarsBetween   = 4;
input int    InpMaxHoldBars      = 36;
input bool   InpSessionFilter    = true;
input int    InpSessionFrom      = 7;   // broker server hour
input int    InpSessionTo        = 20;
input double InpTrailActivateR   = 1.8;
input double InpTrailDistanceR   = 0.6;
input double InpRiskPct          = 1.0;
input ulong  InpMagic            = 20260722;
input bool   InpAllowLong        = true;
input bool   InpAllowShort       = true;

CTrade trade;
datetime g_last_bar = 0;
int      g_last_entry_bar = -9999;
int      g_week_trades = 0;
int      g_week_key = -1;
int      g_entry_bar = -1;
double   g_entry_price = 0;
double   g_risk = 0;
double   g_tp = 0;
bool     g_trail_on = false;

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber((int)InpMagic);
   trade.SetDeviationInPoints(20);
   trade.SetTypeFillingBySymbol(_Symbol);
   Print("ForgeBest3m_Frozen loaded | ", _Symbol, " ", EnumToString(_Period),
         " | RR=", InpRR, " ATRx=", InpAtrMultSL);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {}

//+------------------------------------------------------------------+
void OnTick()
{
   ManageOpenTrade();

   datetime t = iTime(_Symbol, PERIOD_H1, 0);
   if(t == 0 || t == g_last_bar)
      return;
   g_last_bar = t;

   // New H1 bar: evaluate closed bar [1], enter at current open
   if(PositionsTotalByMagic() > 0)
      return;

   int sig = EvaluateSignalAt(1);
   if(sig == 0)
      return;

   OpenTrade(sig);
}

//+------------------------------------------------------------------+
int PositionsTotalByMagic()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionSelectByTicket(PositionGetTicket(i)))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      n++;
   }
   return n;
}

//+------------------------------------------------------------------+
int WeekKey(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   // ISO-ish week key: year*100 + week-of-year approx via day-of-year
   int w = (dt.day_of_year / 7) + 1;
   return dt.year * 100 + w;
}

//+------------------------------------------------------------------+
void ResetWeekCounter(datetime t)
{
   int wk = WeekKey(t);
   if(wk != g_week_key)
   {
      g_week_key = wk;
      g_week_trades = 0;
   }
}

//---------------- Feature helpers (match feature_engine.py) --------
// Arrays are series-style: index 0 = newest bar.
double EmaAt(const double &close[], int period, int shift, int bars)
{
   if(bars <= period + shift)
      return EMPTY_VALUE;
   double k = 2.0 / (period + 1.0);
   double series[];
   ArrayResize(series, bars);
   series[bars - 1] = close[bars - 1]; // oldest
   for(int i = bars - 2; i >= 0; i--)
      series[i] = close[i] * k + series[i + 1] * (1.0 - k);
   return series[shift];
}

double AtrEwm(const double &high[], const double &low[], const double &close[],
              int period, int shift, int bars)
{
   if(bars < period + shift + 2)
      return EMPTY_VALUE;
   double atr[];
   ArrayResize(atr, bars);
   atr[bars - 1] = high[bars - 1] - low[bars - 1];
   double alpha = 1.0 / period; // matches indicators.atr (ewm alpha=1/period)
   for(int i = bars - 2; i >= 0; i--)
   {
      double a = high[i] - low[i];
      double b = MathAbs(high[i] - close[i + 1]);
      double c = MathAbs(low[i] - close[i + 1]);
      double tr = MathMax(a, MathMax(b, c));
      atr[i] = alpha * tr + (1.0 - alpha) * atr[i + 1];
   }
   return atr[shift];
}

double RsiAt(const double &close[], int period, int shift, int bars)
{
   if(bars < period + shift + 5)
      return EMPTY_VALUE;
   double alpha = 1.0 / period;
   double avg_gain = 0.0, avg_loss = 0.0;
   bool started = false;
   for(int i = bars - 2; i >= shift; i--)
   {
      double d = close[i] - close[i + 1];
      double g = (d > 0.0) ? d : 0.0;
      double l = (d < 0.0) ? -d : 0.0;
      if(!started)
      {
         avg_gain = g;
         avg_loss = l;
         started = true;
      }
      else
      {
         avg_gain = alpha * g + (1.0 - alpha) * avg_gain;
         avg_loss = alpha * l + (1.0 - alpha) * avg_loss;
      }
   }
   if(avg_loss <= 0.0)
      return 100.0;
   double rs = avg_gain / avg_loss;
   return 100.0 - (100.0 / (1.0 + rs));
}

double AdxAt(const double &high[], const double &low[], const double &close[],
             int period, int shift, int bars)
{
   if(bars < period * 3 + shift)
      return EMPTY_VALUE;
   double alpha = 1.0 / period;
   double atr = 0, pdm = 0, mdm = 0, adx = 0;
   bool seeded = false;
   int dx_count = 0;
   for(int i = bars - 2; i >= shift; i--)
   {
      double up = high[i] - high[i + 1];
      double dn = low[i + 1] - low[i];
      double plus_dm = (up > dn && up > 0) ? up : 0;
      double minus_dm = (dn > up && dn > 0) ? dn : 0;
      double a = high[i] - low[i];
      double b = MathAbs(high[i] - close[i + 1]);
      double c = MathAbs(low[i] - close[i + 1]);
      double trv = MathMax(a, MathMax(b, c));

      if(!seeded)
      {
         atr = trv; pdm = plus_dm; mdm = minus_dm; seeded = true;
         continue;
      }
      atr = alpha * trv + (1.0 - alpha) * atr;
      pdm = alpha * plus_dm + (1.0 - alpha) * pdm;
      mdm = alpha * minus_dm + (1.0 - alpha) * mdm;
      if(atr <= 0)
         continue;
      double pdi = 100.0 * pdm / atr;
      double mdi = 100.0 * mdm / atr;
      double den = pdi + mdi;
      double dx = den > 0 ? 100.0 * MathAbs(pdi - mdi) / den : 0;
      if(dx_count == 0)
         adx = dx;
      else
         adx = alpha * dx + (1.0 - alpha) * adx;
      dx_count++;
   }
   return adx;
}

// Min-max rank over window (NOT percentile) — matches FeatureMatrix._pct_rank
double MinMaxRank(const double &series[], int shift, int window, int bars)
{
   int from = shift;
   int to = MathMin(bars - 1, shift + window - 1);
   if(to - from + 1 < window / 2)
      return EMPTY_VALUE;
   double mn = series[from], mx = series[from];
   for(int i = from; i <= to; i++)
   {
      if(series[i] < mn) mn = series[i];
      if(series[i] > mx) mx = series[i];
   }
   return (series[shift] - mn) / (mx - mn + 1e-12);
}

double HtfTrendAt(const datetime &time[], const double &close[], int shift, int bars)
{
   // Approximate H4 EMA50 vs EMA200 by sampling every 4 H1 bars ending at shift
   int n4 = bars / 4;
   if(n4 < 220)
      return 0;
   double h4[];
   ArrayResize(h4, n4);
   for(int k = 0; k < n4; k++)
   {
      int idx = shift + k * 4;
      if(idx >= bars) idx = bars - 1;
      h4[k] = close[idx];
   }
   double e50 = EmaAt(h4, 50, 0, n4);
   double e200 = EmaAt(h4, 200, 0, n4);
   if(e50 == EMPTY_VALUE || e200 == EMPTY_VALUE)
      return 0;
   if(e50 > e200) return 1.0;
   if(e50 < e200) return -1.0;
   return 0;
}

//+------------------------------------------------------------------+
struct FeatSnap
{
   double bb_width_pct;
   double price_vs_ema50;
   double atr_pct;
   double adx;
   double pullback_short;
   double atr;
};

bool BuildFeatures(int shift, FeatSnap &f)
{
   int bars = 400;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_H1, 0, bars, rates) < bars)
      return false;

   double close[], high[], low[], open[];
   datetime time[];
   ArrayResize(close, bars); ArrayResize(high, bars); ArrayResize(low, bars);
   ArrayResize(open, bars); ArrayResize(time, bars);
   for(int i = 0; i < bars; i++)
   {
      close[i] = rates[i].close;
      high[i]  = rates[i].high;
      low[i]   = rates[i].low;
      open[i]  = rates[i].open;
      time[i]  = rates[i].time;
   }

   double atr14[];
   ArrayResize(atr14, bars);
   // Build full ATR series once (same ewm recursion as AtrEwm)
   atr14[bars - 1] = high[bars - 1] - low[bars - 1];
   {
      double alpha = 1.0 / 14.0;
      for(int i = bars - 2; i >= 0; i--)
      {
         double a = high[i] - low[i];
         double b = MathAbs(high[i] - close[i + 1]);
         double c = MathAbs(low[i] - close[i + 1]);
         double tr = MathMax(a, MathMax(b, c));
         atr14[i] = alpha * tr + (1.0 - alpha) * atr14[i + 1];
      }
   }

   f.atr = atr14[shift];
   if(f.atr == EMPTY_VALUE || f.atr <= 0)
      return false;

   double e21 = EmaAt(close, 21, shift, bars);
   double e8  = EmaAt(close, 8, shift, bars);
   double e50 = EmaAt(close, 50, shift, bars);
   if(e21 == EMPTY_VALUE || e8 == EMPTY_VALUE || e50 == EMPTY_VALUE)
      return false;

   // Bollinger 20,2
   double sum = 0;
   for(int i = shift; i < shift + 20; i++) sum += close[i];
   double mid = sum / 20.0;
   double var = 0;
   for(int i = shift; i < shift + 20; i++)
   {
      double d = close[i] - mid;
      var += d * d;
   }
   double std = MathSqrt(var / 20.0);
   double bb_u = mid + 2.0 * std;
   double bb_l = mid - 2.0 * std;
   double bb_width = (bb_u - bb_l) / (mid + 1e-12);

   double bb_widths[];
   ArrayResize(bb_widths, bars);
   for(int s = 0; s < bars - 25; s++)
   {
      double ssum = 0;
      for(int i = s; i < s + 20; i++) ssum += close[i];
      double smid = ssum / 20.0;
      double svar = 0;
      for(int i = s; i < s + 20; i++)
      {
         double d = close[i] - smid;
         svar += d * d;
      }
      double sstd = MathSqrt(svar / 20.0);
      bb_widths[s] = ((smid + 2 * sstd) - (smid - 2 * sstd)) / (smid + 1e-12);
   }
   for(int s = bars - 25; s < bars; s++)
      bb_widths[s] = bb_width;

   f.bb_width_pct = MinMaxRank(bb_widths, shift, 50, bars - 25);
   f.atr_pct = MinMaxRank(atr14, shift, 50, bars);
   f.price_vs_ema50 = (close[shift] - e50) / (f.atr + 1e-12);
   f.adx = AdxAt(high, low, close, 14, shift, bars);

   double htf = HtfTrendAt(time, close, shift, bars);
   double ema_stack_bear = (e8 < e21 && e21 < e50) ? 1.0 : 0.0;
   double rsi = RsiAt(close, 14, shift, bars);
   f.pullback_short = (
      htf < 0 && ema_stack_bear > 0 &&
      high[shift] >= e21 * 0.999 && close[shift] < e21 &&
      rsi < 65 && rsi > 45
   ) ? 1.0 : 0.0;

   return true;
}

//+------------------------------------------------------------------+
void ScoreSide(const FeatSnap &f, bool is_long, double &score, int &count)
{
   score = 0; count = 0;
   // Hardcoded frozen rules from best_3m_frozen.json
   if(is_long)
   {
      // bb_width_pct < 0.1011 w=2.111
      if(f.bb_width_pct != EMPTY_VALUE && f.bb_width_pct < 0.1011) { score += 2.111; count++; }
      // price_vs_ema50 < -1.5625 w=183.119
      if(f.price_vs_ema50 < -1.5625) { score += 183.119; count++; }
      // bb_width_pct < 0.2544 w=9.453
      if(f.bb_width_pct != EMPTY_VALUE && f.bb_width_pct < 0.2544) { score += 9.453; count++; }
      // atr_pct < 0.157 w=3.545
      if(f.atr_pct != EMPTY_VALUE && f.atr_pct < 0.157) { score += 3.545; count++; }
   }
   else
   {
      // pullback_short eq1 w=1.393
      if(f.pullback_short > 0.5) { score += 1.393; count++; }
      // adx > 38.6395 w=0.143
      if(f.adx != EMPTY_VALUE && f.adx > 38.6395) { score += 0.143; count++; }
   }
}

//+------------------------------------------------------------------+
int EvaluateSignalAt(int shift)
{
   FeatSnap f;
   if(!BuildFeatures(shift, f))
      return 0;

   datetime t = iTime(_Symbol, PERIOD_H1, shift);
   MqlDateTime dt;
   TimeToStruct(t, dt);
   if(InpSessionFilter && (dt.hour < InpSessionFrom || dt.hour > InpSessionTo))
      return 0;

   ResetWeekCounter(t);
   if(g_week_trades >= InpMaxTradesPerWeek)
      return 0;

   // bar index proxy for spacing
   int bar_idx = (int)(t / PeriodSeconds(PERIOD_H1));
   if(bar_idx - g_last_entry_bar < InpMinBarsBetween)
      return 0;

   double ls, ss; int lc, sc;
   ScoreSide(f, true, ls, lc);
   ScoreSide(f, false, ss, sc);

   // ML disabled → prob=0.5 → combined = score * 1.0
   double combined_l = ls;
   double combined_s = ss;

   int sig = 0;
   if(InpAllowLong && lc >= InpMinRulesMatch && combined_l >= InpScoreThreshold && combined_l > combined_s)
      sig = 1;
   else if(InpAllowShort && sc >= InpMinRulesMatch && combined_s >= InpScoreThreshold && combined_s > combined_l)
      sig = -1;

   return sig;
}

//+------------------------------------------------------------------+
double LotsForRisk(double sl_distance)
{
   if(sl_distance <= 0)
      return 0;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money = balance * InpRiskPct / 100.0;
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_val <= 0 || tick_size <= 0)
      return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double loss_per_lot = (sl_distance / tick_size) * tick_val;
   if(loss_per_lot <= 0)
      return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lots = risk_money / loss_per_lot;
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   return MathMax(vmin, MathMin(vmax, lots));
}

//+------------------------------------------------------------------+
void OpenTrade(int sig)
{
   FeatSnap f;
   if(!BuildFeatures(1, f))
      return;

   double sl_dist = InpAtrMultSL * f.atr;
   double price = (sig > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (sig > 0) ? price - sl_dist : price + sl_dist;
   double tp = (sig > 0) ? price + sl_dist * InpRR : price - sl_dist * InpRR;
   double lots = LotsForRisk(sl_dist);
   if(lots <= 0)
      return;

   bool ok = false;
   if(sig > 0)
      ok = trade.Buy(lots, _Symbol, price, sl, tp, "Best3m frozen LONG");
   else
      ok = trade.Sell(lots, _Symbol, price, sl, tp, "Best3m frozen SHORT");

   if(ok)
   {
      g_entry_price = price;
      g_risk = sl_dist;
      g_tp = tp;
      g_trail_on = false;
      g_entry_bar = (int)(iTime(_Symbol, PERIOD_H1, 0) / PeriodSeconds(PERIOD_H1));
      g_last_entry_bar = g_entry_bar;
      g_week_trades++;
      Print("Opened ", (sig > 0 ? "LONG" : "SHORT"),
            " lots=", lots, " SL=", sl, " TP=", tp, " ATR=", f.atr);
   }
   else
      Print("Order failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
void ManageOpenTrade()
{
   if(PositionsTotalByMagic() == 0)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double risk = g_risk;
      if(risk <= 0)
         risk = MathAbs(open_price - sl);

      // timeout
      datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
      int held = (int)((TimeCurrent() - open_time) / PeriodSeconds(PERIOD_H1));
      if(held >= InpMaxHoldBars)
      {
         trade.PositionClose(ticket);
         Print("Closed by timeout bars=", held);
         continue;
      }

      // hybrid trail: activate near TP (1.8R), trail 0.6R
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(type == POSITION_TYPE_BUY)
      {
         if(bid >= open_price + risk * InpTrailActivateR)
         {
            g_trail_on = true;
            double new_sl = bid - risk * InpTrailDistanceR;
            if(new_sl > sl)
               trade.PositionModify(ticket, new_sl, tp);
         }
      }
      else
      {
         if(ask <= open_price - risk * InpTrailActivateR)
         {
            g_trail_on = true;
            double new_sl = ask + risk * InpTrailDistanceR;
            if(sl == 0 || new_sl < sl)
               trade.PositionModify(ticket, new_sl, tp);
         }
      }
   }
}

//+------------------------------------------------------------------+
