//+------------------------------------------------------------------+
//| ForgeSignals.mqh — rule + ML signal (generate_signals_mined)     |
//+------------------------------------------------------------------+
#ifndef FORGE_SIGNALS_MQH
#define FORGE_SIGNALS_MQH

#include "ForgeConfig.mqh"
#include "ForgeFeatures.mqh"

double ForgeSigmoid(double x)
{
  return 1.0 / (1.0 + MathExp(-x));
}

bool ForgeRuleMatch(const string feat, const string op, double thr, int shift)
{
  double v = ForgeGetFeature(feat, shift);
  if(op == "eq1") return (v > 0.5);
  if(op == "gt") return (v > thr);
  if(op == "lt") return (v < thr);
  return false;
}

void ForgeScoreRules(const string &feats[], const string &ops[], const double &thrs[],
                     const double &ws[], int n, int shift, double &score, int &count)
{
  score = 0.0;
  count = 0;
  for(int i = 0; i < n; i++)
  {
    if(ForgeRuleMatch(feats[i], ops[i], thrs[i], shift))
    {
      score += ws[i];
      count++;
    }
  }
}

double ForgeMLProb(bool isLong, int shift)
{
  if(!FORGE_ML_ENABLED || FORGE_ML_FEATURE_COUNT <= 0) return 0.5;

  double z = isLong ? FORGE_ML_LONG_INTERCEPT : FORGE_ML_SHORT_INTERCEPT;
  bool enabled = isLong ? (FORGE_ML_LONG_ENABLED == 1) : (FORGE_ML_SHORT_ENABLED == 1);
  if(!enabled) return 0.5;

  for(int i = 0; i < FORGE_ML_FEATURE_COUNT; i++)
  {
    double raw = ForgeGetFeature(FORGE_ML_FEATURES[i], shift);
    double scaled = raw;
    if(i < ArraySize(FORGE_ML_MEAN) && i < ArraySize(FORGE_ML_SCALE))
      scaled = (raw - FORGE_ML_MEAN[i]) / (FORGE_ML_SCALE[i] + 1e-12);
    double coef = 0.0;
    if(isLong && i < ArraySize(FORGE_ML_LONG_COEF)) coef = FORGE_ML_LONG_COEF[i];
    if(!isLong && i < ArraySize(FORGE_ML_SHORT_COEF)) coef = FORGE_ML_SHORT_COEF[i];
    z += coef * scaled;
  }
  return ForgeSigmoid(z);
}

int ForgeIsoWeekKey(datetime t)
{
  MqlDateTime dt;
  TimeToStruct(t, dt);
  return dt.year * 100 + dt.day_of_year / 7;
}

bool ForgeSessionOk(int shift)
{
  if(!FORGE_SESSION_FILTER) return true;
  datetime barTime = iTime(_Symbol, PERIOD_H1, shift);
  MqlDateTime dt;
  TimeToStruct(barTime, dt);
  return (dt.hour >= 7 && dt.hour <= 20);
}

// Returns +1 long, -1 short, 0 none
int ForgeEvaluateSignal(int shift)
{
  if(!ForgeSessionOk(shift)) return 0;

  double ls = 0, ss = 0;
  int lc = 0, sc = 0;
  ForgeScoreRules(FORGE_LONG_RULES_FEAT, FORGE_LONG_RULES_OP, FORGE_LONG_RULES_THR,
                  FORGE_LONG_RULES_W, FORGE_LONG_RULES_COUNT, shift, ls, lc);
  ForgeScoreRules(FORGE_SHORT_RULES_FEAT, FORGE_SHORT_RULES_OP, FORGE_SHORT_RULES_THR,
                  FORGE_SHORT_RULES_W, FORGE_SHORT_RULES_COUNT, shift, ss, sc);

  double mlL = ForgeMLProb(true, shift);
  double mlS = ForgeMLProb(false, shift);
  double combinedL = ls * (0.5 + mlL);
  double combinedS = ss * (0.5 + mlS);

  if(lc >= FORGE_MIN_RULES_MATCH && combinedL >= FORGE_SCORE_THRESHOLD && combinedL > combinedS)
  {
    if(mlL >= FORGE_ML_PROB_MIN) return 1;
  }
  else if(sc >= FORGE_MIN_RULES_MATCH && combinedS >= FORGE_SCORE_THRESHOLD && combinedS > combinedL)
  {
    if(mlS >= FORGE_ML_PROB_MIN) return -1;
  }
  return 0;
}

#endif
