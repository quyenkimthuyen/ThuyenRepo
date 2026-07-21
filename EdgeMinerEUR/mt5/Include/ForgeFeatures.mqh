//+------------------------------------------------------------------+
//| ForgeFeatures.mqh — feature engine (mirror feature_engine.py)    |
//+------------------------------------------------------------------+
#ifndef FORGE_FEATURES_MQH
#define FORGE_FEATURES_MQH

#define FORGE_WARMUP 120
#define FORGE_PIP 0.0001

double ForgeEmaOnArray(const double &src[], int count, int period, int shift)
{
  if(shift >= count - 1) return 0.0;
  double k = 2.0 / (period + 1.0);
  int start = MathMin(count - 2, shift + period * 4);
  double ema = src[start];
  for(int i = start - 1; i >= shift; i--)
    ema = src[i] * k + ema * (1.0 - k);
  return ema;
}

double ForgePctRank(const double &arr[], int count, int window, int shift)
{
  if(shift + window >= count) return 0.5;
  double val = arr[shift];
  double mn = val, mx = val;
  int n = 0;
  for(int i = shift; i < shift + window && i < count; i++)
  {
    double v = arr[i];
    if(v < mn) mn = v;
    if(v > mx) mx = v;
    n++;
  }
  if(n < 2) return 0.5;
  return (val - mn) / (mx - mn + 1e-12);
}

double ForgeZScore(const double &arr[], int count, int window, int shift)
{
  if(shift + window >= count) return 0.0;
  double sum = 0, sum2 = 0;
  int n = 0;
  for(int i = shift; i < shift + window && i < count; i++)
  {
    sum += arr[i];
    sum2 += arr[i] * arr[i];
    n++;
  }
  if(n < 2) return 0.0;
  double mean = sum / n;
  double var = sum2 / n - mean * mean;
  double std = MathSqrt(MathMax(var, 0));
  if(std < 1e-12) return 0.0;
  return (arr[shift] - mean) / std;
}

double ForgeCalcAtr(const double &high[], const double &low[], const double &close[],
                    int count, int period, int shift)
{
  if(shift + period + 2 >= count) return 0.0;
  double atr = 0;
  for(int i = shift + period; i >= shift; i--)
  {
    double tr = MathMax(high[i] - low[i],
               MathMax(MathAbs(high[i] - close[i + 1]), MathAbs(low[i] - close[i + 1])));
    if(i == shift + period)
      atr = tr;
    else
      atr = (tr + (period - 1) * atr) / period;
  }
  return atr;
}

double ForgeCalcRsi(const double &close[], int count, int period, int shift)
{
  if(shift + period + 2 >= count) return 50.0;
  double avgGain = 0, avgLoss = 0;
  for(int i = shift + period; i > shift; i--)
  {
    double d = close[i - 1] - close[i];
    avgGain += (d > 0 ? d : 0);
    avgLoss += (d < 0 ? -d : 0);
  }
  avgGain /= period;
  avgLoss /= period;
  if(avgLoss < 1e-12) return 100.0;
  double rs = avgGain / avgLoss;
  return 100.0 - 100.0 / (1.0 + rs);
}

double ForgeCalcAdx(const double &high[], const double &low[], const double &close[],
                    int count, int period, int shift)
{
  if(shift + period * 2 + 2 >= count) return 0.0;
  double plusDi = 0, minusDi = 0, dx = 0, adx = 0;
  for(int i = shift + period; i >= shift; i--)
  {
    double up = high[i - 1] - high[i];
    double dn = low[i] - low[i - 1];
    double plusDm = (up > dn && up > 0) ? up : 0;
    double minusDm = (dn > up && dn > 0) ? dn : 0;
    double tr = MathMax(high[i] - low[i],
               MathMax(MathAbs(high[i] - close[i + 1]), MathAbs(low[i] - close[i + 1])));
    double atr = ForgeCalcAtr(high, low, close, count, period, i);
    if(atr < 1e-12) continue;
    double pdi = 100.0 * plusDm / atr;
    double mdi = 100.0 * minusDm / atr;
    double curDx = 100.0 * MathAbs(pdi - mdi) / (pdi + mdi + 1e-12);
    if(i == shift + period)
    { plusDi = pdi; minusDi = mdi; dx = curDx; adx = curDx; }
    else
    {
      plusDi = (pdi + (period - 1) * plusDi) / period;
      minusDi = (mdi + (period - 1) * minusDi) / period;
      dx = (curDx + (period - 1) * dx) / period;
      adx = (dx + (period - 1) * adx) / period;
    }
  }
  return adx;
}

double ForgeHtfTrend(int shift)
{
  double h4c[];
  ArraySetAsSeries(h4c, true);
  int n = CopyClose(_Symbol, PERIOD_H4, shift, 260, h4c);
  if(n < 60) return 0.0;
  double e50 = ForgeEmaOnArray(h4c, n, 50, 0);
  double e200 = ForgeEmaOnArray(h4c, n, 200, 0);
  if(e50 > e200) return 1.0;
  if(e50 < e200) return -1.0;
  return 0.0;
}

double ForgeGetFeature(const string name, int shift)
{
  double o[], h[], l[], c[];
  ArraySetAsSeries(o, true);
  ArraySetAsSeries(h, true);
  ArraySetAsSeries(l, true);
  ArraySetAsSeries(c, true);
  int need = FORGE_WARMUP + 80;
  if(CopyOpen(_Symbol, PERIOD_H1, shift, need, o) < need) return 0.0;
  if(CopyHigh(_Symbol, PERIOD_H1, shift, need, h) < need) return 0.0;
  if(CopyLow(_Symbol, PERIOD_H1, shift, need, l) < need) return 0.0;
  if(CopyClose(_Symbol, PERIOD_H1, shift, need, c) < need) return 0.0;

  int count = need;
  double atr = ForgeCalcAtr(h, l, c, count, 14, 0);
  double atrArr[];
  ArrayResize(atrArr, 60);
  for(int i = 0; i < 60; i++)
    atrArr[i] = ForgeCalcAtr(h, l, c, count, 14, i);

  double e8 = ForgeEmaOnArray(c, count, 8, 0);
  double e21 = ForgeEmaOnArray(c, count, 21, 0);
  double e50 = ForgeEmaOnArray(c, count, 50, 0);
  double e8p = ForgeEmaOnArray(c, count, 8, 1);
  double e21p = ForgeEmaOnArray(c, count, 21, 1);

  double bbMid = 0, bbUp = 0, bbLo = 0;
  {
    double sum = 0, sum2 = 0;
    for(int i = 0; i < 20; i++) { sum += c[i]; sum2 += c[i] * c[i]; }
    bbMid = sum / 20.0;
    double var = sum2 / 20.0 - bbMid * bbMid;
    double std = MathSqrt(MathMax(var, 0));
    bbUp = bbMid + 2.0 * std;
    bbLo = bbMid - 2.0 * std;
  }
  double bbWidth = (bbUp - bbLo) / (bbMid + 1e-12);
  double bbWidthArr[60];
  for(int i = 0; i < 60; i++)
  {
    double s = 0, s2 = 0;
    for(int j = i; j < i + 20 && j < count; j++) { s += c[j]; s2 += c[j] * c[j]; }
    double m = s / 20.0;
    double v = s2 / 20.0 - m * m;
    double st = MathSqrt(MathMax(v, 0));
    bbWidthArr[i] = (2.0 * st * 2.0) / (m + 1e-12);
  }

  double rsi = ForgeCalcRsi(c, count, 14, 0);
  double adx = ForgeCalcAdx(h, l, c, count, 14, 0);

  double macdHist = 0;
  {
    double fast = ForgeEmaOnArray(c, count, 12, 0);
    double slow = ForgeEmaOnArray(c, count, 26, 0);
    double macd = fast - slow;
    double sig = macd * 0.5;
    macdHist = (macd - sig) / (atr + 1e-12);
  }

  double roc5 = 0;
  if(c[5] > 0) roc5 = (c[0] - c[5]) / c[5] * 100.0;

  double body = MathAbs(c[0] - o[0]);
  double rng = h[0] - l[0] + 1e-12;
  double upperWick = h[0] - MathMax(c[0], o[0]);
  double lowerWick = MathMin(c[0], o[0]) - l[0];

  double rh20 = h[1], rl20 = l[1];
  for(int i = 1; i < 20; i++) { if(h[i] > rh20) rh20 = h[i]; if(l[i] < rl20) rl20 = l[i]; }

  datetime barTime = iTime(_Symbol, PERIOD_H1, shift);
  MqlDateTime dt;
  TimeToStruct(barTime, dt);
  int hour = dt.hour;

  double htf = ForgeHtfTrend(shift);
  double bbWidthPct = ForgePctRank(bbWidthArr, 60, 50, 0);
  double atrPct = ForgePctRank(atrArr, 60, 50, 0);
  double bbPos = (c[0] - bbLo) / (bbUp - bbLo + 1e-12);
  double squeeze = (bbWidthPct < 0.25) ? 1.0 : 0.0;

  if(name == "rsi") return rsi;
  if(name == "adx") return adx;
  if(name == "bb_pos") return bbPos;
  if(name == "bb_width_pct") return bbWidthPct;
  if(name == "atr_pct") return atrPct;
  if(name == "zscore_20") return ForgeZScore(c, count, 20, 0);
  if(name == "price_vs_ema21") return (c[0] - e21) / (atr + 1e-12);
  if(name == "price_vs_ema50") return (c[0] - e50) / (atr + 1e-12);
  if(name == "ema_slope_8") return (e8 - e8p) / (atr + 1e-12);
  if(name == "ema_slope_21") return (e21 - e21p) / (atr + 1e-12);
  if(name == "macd_hist") return macdHist;
  if(name == "roc_5") return roc5;
  if(name == "body_ratio") return body / rng;
  if(name == "htf_trend") return htf;
  if(name == "bb_width") return bbWidth;
  if(name == "lower_wick_ratio") return lowerWick / rng;
  if(name == "upper_wick_ratio") return upperWick / rng;
  if(name == "ema_stack_bull") return (e8 > e21 && e21 > e50) ? 1.0 : 0.0;
  if(name == "ema_stack_bear") return (e8 < e21 && e21 < e50) ? 1.0 : 0.0;
  if(name == "sweep_low_fade") return (l[0] < rl20 && c[0] > rl20) ? 1.0 : 0.0;
  if(name == "sweep_high_fade") return (h[0] > rh20 && c[0] < rh20) ? 1.0 : 0.0;
  if(name == "squeeze_break_up") return (squeeze > 0.5 && c[0] > bbUp && htf >= 0) ? 1.0 : 0.0;
  if(name == "squeeze_break_dn") return (squeeze > 0.5 && c[0] < bbLo && htf <= 0) ? 1.0 : 0.0;
  if(name == "pullback_long")
    return (htf > 0 && e8 > e21 && e21 > e50 && l[0] <= e21 * 1.001 && c[0] > e21 && rsi > 35 && rsi < 55) ? 1.0 : 0.0;
  if(name == "pullback_short")
    return (htf < 0 && e8 < e21 && e21 < e50 && h[0] >= e21 * 0.999 && c[0] < e21 && rsi < 65 && rsi > 45) ? 1.0 : 0.0;
  if(name == "range_buy") return (adx < 22 && bbPos < 0.1 && rsi < 35) ? 1.0 : 0.0;
  if(name == "range_sell") return (adx < 22 && bbPos > 0.9 && rsi > 65) ? 1.0 : 0.0;
  if(name == "overlap_session") return (hour >= 13 && hour < 16) ? 1.0 : 0.0;
  if(name == "asia_session") return (hour >= 0 && hour < 8) ? 1.0 : 0.0;
  if(name == "london_open") return (hour >= 8 && hour < 11) ? 1.0 : 0.0;
  if(name == "regime_trending") return (adx >= 25) ? 1.0 : 0.0;
  if(name == "regime_ranging") return (adx < 20) ? 1.0 : 0.0;
  if(name == "regime_high_vol") return (atrPct > 0.65) ? 1.0 : 0.0;
  if(name == "regime_low_vol") return (atrPct < 0.35) ? 1.0 : 0.0;

  return 0.0;
}

#endif
