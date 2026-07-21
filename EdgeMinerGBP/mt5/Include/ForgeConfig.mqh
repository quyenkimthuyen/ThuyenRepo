// Placeholder — replaced by export script (ForgeConfig.mqh in mt5/output/)
#ifndef FORGE_CONFIG_MQH
#define FORGE_CONFIG_MQH

#define FORGE_MODEL_ID "placeholder"
#define FORGE_MODEL_LABEL "Run export_mt5_ea.py first"
#define FORGE_WEEK_START ""
#define FORGE_STRATEGY_NAME "placeholder"

#define FORGE_SCORE_THRESHOLD 2.0
#define FORGE_ML_PROB_MIN 0.4
#define FORGE_MIN_RULES_MATCH 2
#define FORGE_MIN_BARS_BETWEEN 4
#define FORGE_MAX_TRADES_WEEK 2
#define FORGE_MAX_HOLD_BARS 24
#define FORGE_RR 2.5
#define FORGE_ATR_MULT 0.9
#define FORGE_EXIT_MODE "full"
#define FORGE_SESSION_FILTER 1
#define FORGE_PARTIAL_PCT 0.4
#define FORGE_PARTIAL_AT_R 1.2
#define FORGE_TRAIL_ACTIVATE_R 1.0
#define FORGE_TRAIL_DISTANCE_R 0.5
#define FORGE_SPREAD_PIPS 1.0
#define FORGE_SLIPPAGE_PIPS 0.3

#define FORGE_LONG_RULES_COUNT 0
string FORGE_LONG_RULES_FEAT[] = {};
string FORGE_LONG_RULES_OP[] = {};
double FORGE_LONG_RULES_THR[] = {};
double FORGE_LONG_RULES_W[] = {};

#define FORGE_SHORT_RULES_COUNT 0
string FORGE_SHORT_RULES_FEAT[] = {};
string FORGE_SHORT_RULES_OP[] = {};
double FORGE_SHORT_RULES_THR[] = {};
double FORGE_SHORT_RULES_W[] = {};

#define FORGE_ML_FEATURE_COUNT 0
string FORGE_ML_FEATURES[] = {};
#define FORGE_ML_ENABLED 0
double FORGE_ML_MEAN[] = {};
double FORGE_ML_SCALE[] = {};
#define FORGE_ML_LONG_ENABLED 0
double FORGE_ML_LONG_COEF[] = {};
double FORGE_ML_LONG_INTERCEPT = 0.0;
#define FORGE_ML_SHORT_ENABLED 0
double FORGE_ML_SHORT_COEF[] = {};
double FORGE_ML_SHORT_INTERCEPT = 0.0;

#endif
