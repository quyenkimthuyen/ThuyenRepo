//+------------------------------------------------------------------+
//| ForgeBridgeM15J9Sim.mq5 — EdgeMiner M15J9 SIM (magic 20262009, bridge_sim_m15j9) |
//| Thin execution EA — App (Best 3m) decides via mt5/bridge files.  |
//| Modes:                                                           |
//|   Live         — write bar.json, read decision.json (App)        |
//|   Replay       — read replay_signals.csv (Strategy Tester)       |
//|   HistoryFeed  — CopyRates paced by App sim_control.json         |
//| Keep ForgeBest3m_Frozen / ForgeBest3m_WF for MT5 side-by-side.   |
//+------------------------------------------------------------------+
#property copyright "EdgeMinerM15 bridge SIM"
#property version   "1.09"

#include <Trade/Trade.mqh>

enum ENUM_BRIDGE_MODE
{
   BRIDGE_LIVE = 0,           // Live file bridge
   BRIDGE_REPLAY = 1,         // Replay CSV (tester)
   BRIDGE_HISTORY_FEED = 2    // App-controlled historical bar feed
};

input group "=== Bridge ==="
input ENUM_BRIDGE_MODE InpMode = BRIDGE_HISTORY_FEED;
input string InpBridgeSubdir   = "bridge_sim_m15j9";    // under MQL5/Files/ (SIM HistoryFeed)
input int    InpDecisionWaitMs = 8000;              // Live: wait for decision
input int    InpHistoryDecisionWaitMs = 20000;      // HistoryFeed: max wait (remine tuần có thể chậm)
input int    InpPollMs         = 500;
input int    InpChartBars      = 1344;              // M15 bars exported for App chart
input int    InpHeartbeatMs    = 2000;              // Live connection/tick snapshot
input int    InpHistoryChunk   = 750;               // Bars per history sync response
input bool   InpHistoryPaperFills = true;           // HistoryFeed: paper fills from OHLC (no OrderSend)

input group "=== Risk ==="
input double InpRiskPct        = 1.0;
input ulong  InpMagic          = 20262009;        // base magic; multi-model uses models.json
input int    InpMaxModels      = 5;               // max concurrent trade models
input int    InpSlipPoints     = 30;
input int    InpMaxHoldBars    = 36;                // fallback if decision omits

CTrade   trade;
const string INSTANCE_ID = "M15J9";
#define MAX_MODELS 5
datetime g_last_bar = 0;
datetime g_last_fill_bar = 0;
string   g_last_signal_id = "";
ulong    g_open_ticket = 0;
string   g_open_signal_id = "";
string   g_open_action = "";
double   g_open_entry = 0;
double   g_open_sl = 0;
double   g_open_sl_initial = 0;  // paper trail: detect SL moved from plan
double   g_open_tp = 0;
double   g_open_lots = 0;
double   g_risk = 0;
double   g_sync_sl = 0;          // last SL known to App (sync baseline)
double   g_sync_tp = 0;
bool     g_user_intervened = false; // user edited SL/TP or manual test open
bool     g_ea_modifying = false;    // next SL/TP change is from EA trail
string   g_open_source = "strategy"; // strategy | manual_test
ulong    g_active_magic = 0;        // magic for current open/fill context
string   g_active_model_id = "";
int      g_exit_mode = 1;
double   g_trail_act = 1.0;
double   g_trail_dist = 0.5;
int      g_max_hold = 36;
bool     g_had_position = false;
uint     g_last_heartbeat_ms = 0;
string   g_last_history_request = "";

// Multi-model roster (App writes models.json)
string   g_model_ids[MAX_MODELS];
ulong    g_model_magics[MAX_MODELS];
int      g_model_n = 0;
double   g_roster_risk_pct = 0;   // 0 = use InpRiskPct
datetime g_models_mtime = 0;

// Per-slot HistoryFeed pending / paper state
string   g_slot_pending[MAX_MODELS];
bool     g_slot_paper_open[MAX_MODELS];
int      g_slot_paper_held[MAX_MODELS];
ulong    g_slot_ticket[MAX_MODELS];
string   g_slot_sid[MAX_MODELS];
string   g_slot_action[MAX_MODELS];
double   g_slot_entry[MAX_MODELS];
double   g_slot_sl[MAX_MODELS];
double   g_slot_sl_init[MAX_MODELS];
double   g_slot_tp[MAX_MODELS];
double   g_slot_lots[MAX_MODELS];
double   g_slot_risk[MAX_MODELS];
int      g_slot_exit_mode[MAX_MODELS];
double   g_slot_trail_act[MAX_MODELS];
double   g_slot_trail_dist[MAX_MODELS];
int      g_slot_max_hold[MAX_MODELS];

// Replay table
string   g_rep_time[];
int      g_rep_dir[];
double   g_rep_atr[];
double   g_rep_rr[];
int      g_rep_exit[];
double   g_rep_tact[];
double   g_rep_tdist[];
int      g_rep_hold[];
int      g_rep_n = 0;
int      g_rep_cursor = 0;

// History feed (App sim_control.json)
MqlRates g_hist_rates[];
int      g_hist_n = 0;
int      g_hist_cursor = 0;
string   g_sim_request_id = "";
bool     g_sim_enabled = false;
string   g_sim_from = "";
string   g_sim_to = "";
int      g_sim_delay_ms = 100;
string   g_sim_ea_status = "idle";
string   g_sim_last_bar = "";
string   g_sim_error = "";
string   g_pending_decision = "";
bool     g_paper_open = false;
int      g_paper_held = 0;
ulong    g_paper_ticket = 700000;

//+------------------------------------------------------------------+
string BridgePath(const string name)
{
   return InpBridgeSubdir + "\\" + name;
}

// Forward decls — roster loader uses JSON helpers defined below
string JsonGetString(const string json, const string key);
double JsonGetDouble(const string json, const string key, const double def = 0);

string DecisionPathForModel(const string model_id)
{
   string safe = model_id;
   StringReplace(safe, "\\", "_");
   StringReplace(safe, "/", "_");
   StringReplace(safe, ":", "_");
   StringReplace(safe, " ", "_");
   if(safe == "")
      safe = "unknown";
   return BridgePath("decisions\\" + safe + ".json");
}

string SafeModelFileName(const string model_id)
{
   string safe = model_id;
   int n = StringLen(safe);
   for(int i = 0; i < n; i++)
   {
      ushort c = StringGetCharacter(safe, i);
      bool ok = ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                 || (c >= '0' && c <= '9') || c == '-' || c == '_');
      if(!ok)
         StringSetCharacter(safe, i, '_');
   }
   if(safe == "")
      safe = "unknown";
   return safe;
}

void EnsureModelsDefaults()
{
   if(g_model_n > 0)
      return;
   g_model_n = 1;
   g_model_ids[0] = "";
   g_model_magics[0] = InpMagic;
   g_slot_pending[0] = "";
   g_slot_paper_open[0] = false;
}

datetime FileMTime(const string path)
{
   // MQL5 has no portable mtime via File*; reload periodically instead.
   return (datetime)(GetTickCount() / 1000);
}

bool LoadModelsRoster(const bool force = false)
{
   static uint last_load_ms = 0;
   uint now = GetTickCount();
   if(!force && last_load_ms != 0 && (now - last_load_ms) < 2000)
      return (g_model_n > 0);
   last_load_ms = now;

   int h = FileOpen(BridgePath("models.json"), FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
   {
      EnsureModelsDefaults();
      return false;
   }
   string json = "";
   while(!FileIsEnding(h))
      json += FileReadString(h) + "\n";
   FileClose(h);
   if(StringLen(json) < 10)
   {
      EnsureModelsDefaults();
      return false;
   }

   double rp = JsonGetDouble(json, "risk_pct", 0);
   if(rp > 0)
      g_roster_risk_pct = rp;

   // Parse models array entries: look for "id" / "magic" pairs in order
   int maxn = MathMin(InpMaxModels, MAX_MODELS);
   int n = 0;
   int pos = 0;
   while(n < maxn)
   {
      int idp = StringFind(json, "\"id\"", pos);
      if(idp < 0)
         break;
      int colon = StringFind(json, ":", idp);
      if(colon < 0)
         break;
      int q1 = StringFind(json, "\"", colon + 1);
      if(q1 < 0)
         break;
      int q2 = StringFind(json, "\"", q1 + 1);
      if(q2 < 0)
         break;
      string mid = StringSubstr(json, q1 + 1, q2 - q1 - 1);
      int magp = StringFind(json, "\"magic\"", q2);
      if(magp < 0 || magp > q2 + 120)
      {
         pos = q2 + 1;
         continue;
      }
      ulong magic = (ulong)JsonGetDouble(StringSubstr(json, magp, 80), "magic", (double)(InpMagic + n));
      g_model_ids[n] = mid;
      g_model_magics[n] = magic;
      n++;
      pos = magp + 5;
   }
   if(n <= 0)
   {
      EnsureModelsDefaults();
      return false;
   }
   g_model_n = n;
   FolderCreate(InpBridgeSubdir + "\\decisions");
   return true;
}

int FindModelSlotByMagic(const ulong magic)
{
   for(int i = 0; i < g_model_n; i++)
      if(g_model_magics[i] == magic)
         return i;
   return -1;
}

int FindModelSlotById(const string model_id)
{
   for(int i = 0; i < g_model_n; i++)
      if(g_model_ids[i] == model_id)
         return i;
   return -1;
}

void SetActiveSlot(const int slot)
{
   if(slot < 0 || slot >= g_model_n)
   {
      g_active_magic = InpMagic;
      g_active_model_id = "";
      return;
   }
   g_active_magic = g_model_magics[slot];
   g_active_model_id = g_model_ids[slot];
   trade.SetExpertMagicNumber((int)g_active_magic);
}

double EffectiveRiskPct()
{
   if(g_roster_risk_pct > 0)
      return g_roster_risk_pct;
   return InpRiskPct;
}

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber((int)InpMagic);
   trade.SetDeviationInPoints(InpSlipPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   g_max_hold = InpMaxHoldBars;
   g_active_magic = InpMagic;
   ArrayInitialize(g_slot_paper_open, false);
   ArrayInitialize(g_slot_paper_held, 0);
   for(int i = 0; i < MAX_MODELS; i++)
      g_slot_pending[i] = "";

   FolderCreate(InpBridgeSubdir);
   FolderCreate(InpBridgeSubdir + "\\decisions");
   LoadModelsRoster(true);

   if(InpMode == BRIDGE_REPLAY)
   {
      if(!LoadReplayCsv())
      {
         Print("ForgeBridge Replay: failed to load ", BridgePath("replay_signals.csv"));
         return INIT_FAILED;
      }
      Print("ForgeBridge Replay loaded signals=", g_rep_n);
   }
   else if(InpMode == BRIDGE_HISTORY_FEED)
   {
      if(AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      {
         Print("ForgeBridgeM15J9 requires a hedging account.");
         return INIT_FAILED;
      }
      g_sim_ea_status = "idle";
      WriteSimControlFile();
      EventSetMillisecondTimer(50);
      Print("ForgeBridgeM15J9 HistoryFeed | Files/", InpBridgeSubdir,
            " | paper=", InpHistoryPaperFills, " | models=", g_model_n,
            " | base_magic=", InpMagic);
   }
   else
   {
      if(AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      {
         Print("ForgeBridgeM15J9 requires a hedging account.");
         return INIT_FAILED;
      }
      WriteBarsJson();
      WriteConnectionJson();
      EventSetMillisecondTimer((int)MathMax(500, InpHeartbeatMs));
      Print("ForgeBridgeM15J9 Live | Files/", InpBridgeSubdir,
            " | models=", g_model_n, " | base_magic=", InpMagic);
   }

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(InpMode == BRIDGE_HISTORY_FEED)
   {
      ProcessHistoryFeed();
      return;
   }
   if(InpMode == BRIDGE_LIVE)
   {
      WriteConnectionJson();
      ProcessHistoryRequest();
      ProcessManualCommand();
   }
}

//+------------------------------------------------------------------+
int PositionsByMagic(const ulong magic)
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionSelectByTicket(PositionGetTicket(i))) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != magic) continue;
      n++;
   }
   return n;
}

int PositionsByMagic()
{
   LoadModelsRoster();
   int n = 0;
   for(int s = 0; s < g_model_n; s++)
      n += PositionsByMagic(g_model_magics[s]);
   if(n == 0)
      n = PositionsByMagic(InpMagic);
   return n;
}

//+------------------------------------------------------------------+
double LotsForRisk(double sl_dist)
{
   if(sl_dist <= 0) return 0;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money = balance * EffectiveRiskPct() / 100.0;
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

//+------------------------------------------------------------------+
string JsonGetString(const string json, const string key)
{
   string pat = "\"" + key + "\"";
   int p = StringFind(json, pat);
   if(p < 0) return "";
   int colon = StringFind(json, ":", p);
   if(colon < 0) return "";
   int q1 = StringFind(json, "\"", colon + 1);
   if(q1 < 0) return "";
   // null?
   string after = StringSubstr(json, colon + 1);
   StringTrimLeft(after);
   if(StringFind(after, "null") == 0) return "";
   int q2 = StringFind(json, "\"", q1 + 1);
   if(q2 < 0) return "";
   return StringSubstr(json, q1 + 1, q2 - q1 - 1);
}

double JsonGetDouble(const string json, const string key, const double def = 0)
{
   string pat = "\"" + key + "\"";
   int p = StringFind(json, pat);
   if(p < 0) return def;
   int colon = StringFind(json, ":", p);
   if(colon < 0) return def;
   string rest = StringSubstr(json, colon + 1);
   StringTrimLeft(rest);
   if(StringFind(rest, "null") == 0) return def;
   // strip quotes if any
   if(StringGetCharacter(rest, 0) == '"')
   {
      int q2 = StringFind(rest, "\"", 1);
      if(q2 > 0) rest = StringSubstr(rest, 1, q2 - 1);
   }
   else
   {
      int end = StringLen(rest);
      for(int i = 0; i < StringLen(rest); i++)
      {
         ushort c = StringGetCharacter(rest, i);
         if((c < '0' || c > '9') && c != '.' && c != '-' && c != 'e' && c != 'E' && c != '+')
         {
            end = i;
            break;
         }
      }
      rest = StringSubstr(rest, 0, end);
   }
   return StringToDouble(rest);
}

bool JsonGetBool(const string json, const string key, const bool def = false)
{
   string pat = "\"" + key + "\"";
   int p = StringFind(json, pat);
   if(p < 0) return def;
   int colon = StringFind(json, ":", p);
   if(colon < 0) return def;
   string rest = StringSubstr(json, colon + 1);
   StringTrimLeft(rest);
   if(StringFind(rest, "true") == 0) return true;
   if(StringFind(rest, "false") == 0) return false;
   return def;
}

//+------------------------------------------------------------------+
bool WriteBarJson(datetime t1)
{
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 1, r) < 1)
      return false;

   long time_msc = (long)r[0].time * 1000;
   string bar_time = TimeToString(r[0].time, TIME_DATE | TIME_MINUTES);
   // MT5 TimeToString uses yyyy.mm.dd hh:mi — matches App
   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   long login = AccountInfoInteger(ACCOUNT_LOGIN);

   string json = "{";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"M15\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"magic\":" + IntegerToString((long)InpMagic) + ",";
   json += "\"time\":\"" + bar_time + "\",";
   json += "\"bar_time\":\"" + bar_time + "\",";
   json += "\"time_msc\":" + IntegerToString(time_msc) + ",";
   json += "\"open\":" + DoubleToString(r[0].open, _Digits) + ",";
   json += "\"high\":" + DoubleToString(r[0].high, _Digits) + ",";
   json += "\"low\":" + DoubleToString(r[0].low, _Digits) + ",";
   json += "\"close\":" + DoubleToString(r[0].close, _Digits) + ",";
   json += "\"volume\":" + DoubleToString((double)r[0].tick_volume, 0) + ",";
   json += "\"tick_volume\":" + IntegerToString((int)r[0].tick_volume) + ",";
   json += "\"spread_points\":" + IntegerToString(spread) + ",";
   json += "\"digits\":" + IntegerToString(_Digits) + ",";
   json += "\"point\":" + DoubleToString(_Point, _Digits) + ",";
   json += "\"account\":" + IntegerToString((int)login);
   json += "}\n";

   int h = FileOpen(BridgePath("bar.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
   {
      Print("ForgeBridge: cannot write bar.json err=", GetLastError());
      return false;
   }
   FileWriteString(h, json);
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
bool WriteBarJsonFromRate(const MqlRates &rate)
{
   long time_msc = (long)rate.time * 1000;
   string bar_time = TimeToString(rate.time, TIME_DATE | TIME_MINUTES);
   int spread = (rate.spread > 0) ? rate.spread : (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   long login = AccountInfoInteger(ACCOUNT_LOGIN);

   string json = "{";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"M15\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"magic\":" + IntegerToString((long)InpMagic) + ",";
   json += "\"time\":\"" + bar_time + "\",";
   json += "\"bar_time\":\"" + bar_time + "\",";
   json += "\"time_msc\":" + IntegerToString(time_msc) + ",";
   json += "\"open\":" + DoubleToString(rate.open, _Digits) + ",";
   json += "\"high\":" + DoubleToString(rate.high, _Digits) + ",";
   json += "\"low\":" + DoubleToString(rate.low, _Digits) + ",";
   json += "\"close\":" + DoubleToString(rate.close, _Digits) + ",";
   json += "\"volume\":" + DoubleToString((double)rate.tick_volume, 0) + ",";
   json += "\"tick_volume\":" + IntegerToString((int)rate.tick_volume) + ",";
   json += "\"spread_points\":" + IntegerToString(spread) + ",";
   json += "\"digits\":" + IntegerToString(_Digits) + ",";
   json += "\"point\":" + DoubleToString(_Point, _Digits) + ",";
   json += "\"account\":" + IntegerToString((int)login);
   json += "}\n";

   int h = FileOpen(BridgePath("bar.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
   {
      Print("ForgeBridge: cannot write bar.json err=", GetLastError());
      return false;
   }
   FileWriteString(h, json);
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
bool WriteBarsJson()
{
   int requested = MathMax(48, InpChartBars);
   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(_Symbol, PERIOD_M15, 0, requested, rates);
   if(copied < 1)
      return false;

   int h = FileOpen(BridgePath("bars.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
   {
      Print("ForgeBridge: cannot write bars.json err=", GetLastError());
      return false;
   }

   string prefix = "{\"symbol\":\"" + _Symbol + "\",";
   prefix += "\"updated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   prefix += "\"period\":\"M15\",\"bars\":[";
   FileWriteString(h, prefix);
   for(int i = 0; i < copied; i++)
   {
      if(i > 0) FileWriteString(h, ",");
      string row = "{";
      row += "\"time\":\"" + TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES) + "\",";
      row += "\"time_msc\":" + IntegerToString((long)rates[i].time * 1000) + ",";
      row += "\"open\":" + DoubleToString(rates[i].open, _Digits) + ",";
      row += "\"high\":" + DoubleToString(rates[i].high, _Digits) + ",";
      row += "\"low\":" + DoubleToString(rates[i].low, _Digits) + ",";
      row += "\"close\":" + DoubleToString(rates[i].close, _Digits) + ",";
      row += "\"tick_volume\":" + IntegerToString((long)rates[i].tick_volume) + ",";
      row += "\"spread_points\":" + IntegerToString(rates[i].spread);
      row += "}";
      FileWriteString(h, row);
   }
   FileWriteString(h, "]}\n");
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
bool WriteBarsJsonHistoryFeed(const int upto_exclusive)
{
   // Write historical feed bars [0 .. upto_exclusive) for App chart replay
   if(g_hist_n < 1 || upto_exclusive < 1)
      return false;
   int end = MathMin(upto_exclusive, g_hist_n);
   int start = MathMax(0, end - MathMax(48, InpChartBars));

   int h = FileOpen(BridgePath("bars.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return false;

   string prefix = "{\"symbol\":\"" + _Symbol + "\",";
   prefix += "\"updated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   prefix += "\"period\":\"M15\",\"source\":\"history_feed\",\"bars\":[";
   FileWriteString(h, prefix);
   for(int i = start; i < end; i++)
   {
      if(i > start) FileWriteString(h, ",");
      string row = "{";
      row += "\"time\":\"" + TimeToString(g_hist_rates[i].time, TIME_DATE | TIME_MINUTES) + "\",";
      row += "\"time_msc\":" + IntegerToString((long)g_hist_rates[i].time * 1000) + ",";
      row += "\"open\":" + DoubleToString(g_hist_rates[i].open, _Digits) + ",";
      row += "\"high\":" + DoubleToString(g_hist_rates[i].high, _Digits) + ",";
      row += "\"low\":" + DoubleToString(g_hist_rates[i].low, _Digits) + ",";
      row += "\"close\":" + DoubleToString(g_hist_rates[i].close, _Digits) + ",";
      row += "\"tick_volume\":" + IntegerToString((long)g_hist_rates[i].tick_volume) + ",";
      row += "\"spread_points\":" + IntegerToString(g_hist_rates[i].spread);
      row += "}";
      FileWriteString(h, row);
   }
   FileWriteString(h, "]}\n");
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
bool ReadBridgeText(const string name, string &text)
{
   int h = FileOpen(BridgePath(name), FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return false;
   text = "";
   while(!FileIsEnding(h))
      text += FileReadString(h);
   FileClose(h);
   return StringLen(text) > 2;
}

//+------------------------------------------------------------------+
bool BeginAtomicBridgeFile(const string name, int &handle, string &tmp_name)
{
   tmp_name = name + ".tmp";
   FileDelete(BridgePath(tmp_name));
   handle = FileOpen(BridgePath(tmp_name), FILE_WRITE | FILE_TXT | FILE_ANSI);
   return handle != INVALID_HANDLE;
}

//+------------------------------------------------------------------+
bool FinishAtomicBridgeFile(const string name, const int handle, const string tmp_name)
{
   FileClose(handle);
   FileDelete(BridgePath(name));
   if(!FileMove(BridgePath(tmp_name), 0, BridgePath(name), FILE_REWRITE))
   {
      Print("ForgeBridge: cannot publish ", name, " err=", GetLastError());
      return false;
   }
   return true;
}

//+------------------------------------------------------------------+
bool ProcessHistoryRequest()
{
   string request;
   if(!ReadBridgeText("history_request.json", request))
      return false;

   string request_id = JsonGetString(request, "request_id");
   if(request_id == "" || request_id == g_last_history_request)
      return false;

   int offset = (int)MathMax(0, JsonGetDouble(request, "offset", 0));
   int chunk_size = (int)MathMax(100, MathMin(2000,
      JsonGetDouble(request, "chunk_size", InpHistoryChunk)));
   int total = Bars(_Symbol, PERIOD_M15);
   string from_time_text = JsonGetString(request, "from_time");
   datetime from_time = StringToTime(from_time_text == "" ? "2024.01.01 00:00" : from_time_text);
   int oldest_shift = iBarShift(_Symbol, PERIOD_M15, from_time, false);
   int available = MathMax(0, MathMin(total - 1, oldest_shift)); // exclude forming M15 bar
   int wanted = MathMin(chunk_size, MathMax(0, available - offset));

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = 0;
   if(wanted > 0)
      copied = CopyRates(_Symbol, PERIOD_M15, offset + 1, wanted, rates);
   if(copied < 0)
      copied = 0;

   int next_offset = offset + copied;
   bool done = copied == 0 || copied < wanted || next_offset >= available;
   int server_offset = (int)(TimeCurrent() - TimeGMT());

   int h;
   string tmp_name;
   if(!BeginAtomicBridgeFile("history_chunk.json", h, tmp_name))
      return false;

   string prefix = "{\"request_id\":\"" + request_id + "\",";
   prefix += "\"symbol\":\"" + _Symbol + "\",\"period\":\"M15\",";
   prefix += "\"server\":\"" + AccountInfoString(ACCOUNT_SERVER) + "\",";
   prefix += "\"account\":" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + ",";
   prefix += "\"server_utc_offset_seconds\":" + IntegerToString(server_offset) + ",";
   prefix += "\"offset\":" + IntegerToString(offset) + ",";
   prefix += "\"next_offset\":" + IntegerToString(next_offset) + ",";
   prefix += "\"available_bars\":" + IntegerToString(available) + ",";
   prefix += "\"done\":" + (done ? "true" : "false") + ",\"bars\":[";
   FileWriteString(h, prefix);

   for(int i = 0; i < copied; i++)
   {
      if(i > 0) FileWriteString(h, ",");
      string row = "{";
      row += "\"time\":\"" + TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES) + "\",";
      row += "\"time_msc\":" + IntegerToString((long)rates[i].time * 1000) + ",";
      row += "\"open\":" + DoubleToString(rates[i].open, _Digits) + ",";
      row += "\"high\":" + DoubleToString(rates[i].high, _Digits) + ",";
      row += "\"low\":" + DoubleToString(rates[i].low, _Digits) + ",";
      row += "\"close\":" + DoubleToString(rates[i].close, _Digits) + ",";
      row += "\"tick_volume\":" + IntegerToString((long)rates[i].tick_volume) + ",";
      row += "\"spread_points\":" + IntegerToString(rates[i].spread);
      row += "}";
      FileWriteString(h, row);
   }
   FileWriteString(h, "]}\n");
   if(!FinishAtomicBridgeFile("history_chunk.json", h, tmp_name))
      return false;

   g_last_history_request = request_id;
   Print("ForgeBridge history offset=", offset, " copied=", copied,
         " next=", next_offset, " done=", done);
   return true;
}

//+------------------------------------------------------------------+
bool WriteConnectionJson()
{
   MqlRates current[];
   ArraySetAsSeries(current, true);
   if(CopyRates(_Symbol, PERIOD_M15, 0, 1, current) < 1)
      return false;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return false;

   bool connected = (bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   bool terminal_trade = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool account_trade = (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   int positions = PositionsByMagic();

   string json = "{";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"M15\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"bridge_subdir\":\"" + InpBridgeSubdir + "\",";
   json += "\"magic\":" + IntegerToString((long)InpMagic) + ",";
   json += "\"account_margin_mode\":" + IntegerToString(AccountInfoInteger(ACCOUNT_MARGIN_MODE)) + ",";
   json += "\"hedging\":true,";
   json += "\"server_time\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"tick_time_msc\":" + IntegerToString((long)tick.time_msc) + ",";
   json += "\"bid\":" + DoubleToString(tick.bid, _Digits) + ",";
   json += "\"ask\":" + DoubleToString(tick.ask, _Digits) + ",";
   json += "\"spread_points\":" + IntegerToString((int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD)) + ",";
   json += "\"connected\":" + (connected ? "true" : "false") + ",";
   json += "\"terminal_trade_allowed\":" + (terminal_trade ? "true" : "false") + ",";
   json += "\"account_trade_allowed\":" + (account_trade ? "true" : "false") + ",";
   json += "\"account\":" + IntegerToString(login) + ",";
   json += "\"positions\":" + IntegerToString(positions) + ",";
   json += "\"bar\":{";
   json += "\"time\":\"" + TimeToString(current[0].time, TIME_DATE | TIME_MINUTES) + "\",";
   json += "\"time_msc\":" + IntegerToString((long)current[0].time * 1000) + ",";
   json += "\"open\":" + DoubleToString(current[0].open, _Digits) + ",";
   json += "\"high\":" + DoubleToString(current[0].high, _Digits) + ",";
   json += "\"low\":" + DoubleToString(current[0].low, _Digits) + ",";
   json += "\"close\":" + DoubleToString(current[0].close, _Digits) + ",";
   json += "\"tick_volume\":" + IntegerToString((long)current[0].tick_volume);
   json += "}}\n";

   int h = FileOpen(BridgePath("connection.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return false;
   FileWriteString(h, json);
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
bool ReadDecisionJson(string &json_out)
{
   int h = FileOpen(BridgePath("decision.json"), FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return false;
   json_out = "";
   while(!FileIsEnding(h))
      json_out += FileReadString(h) + "\n";
   FileClose(h);
   return (StringLen(json_out) > 5);
}

bool ReadDecisionJsonForModel(const string model_id, string &json_out)
{
   string path = BridgePath("decisions\\" + SafeModelFileName(model_id) + ".json");
   int h = FileOpen(path, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
   {
      // Compat: primary model may still live in decision.json
      if(g_model_n <= 1 || model_id == "" || (g_model_n > 0 && model_id == g_model_ids[0]))
         return ReadDecisionJson(json_out);
      return false;
   }
   json_out = "";
   while(!FileIsEnding(h))
      json_out += FileReadString(h) + "\n";
   FileClose(h);
   return (StringLen(json_out) > 5);
}

//+------------------------------------------------------------------+
bool ReadCommandJson(string &json_out)
{
   int h = FileOpen(BridgePath("command.json"), FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return false;
   json_out = "";
   while(!FileIsEnding(h))
      json_out += FileReadString(h) + "\n";
   FileClose(h);
   return (StringLen(json_out) > 5);
}

//+------------------------------------------------------------------+
void ClearCommandFile()
{
   FileDelete(BridgePath("command.json"));
}

//+------------------------------------------------------------------+
void WriteCommandAck(const string signal_id, const string status, const string detail)
{
   string json = "{";
   json += "\"signal_id\":\"" + signal_id + "\",";
   json += "\"status\":\"" + status + "\",";
   json += "\"detail\":\"" + detail + "\",";
   json += "\"updated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\"";
   json += "}\n";
   int h = FileOpen(BridgePath("command_ack.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, json);
   FileClose(h);
}

//+------------------------------------------------------------------+
bool CloseAllByMagic(const string reason)
{
   LoadModelsRoster();
   bool any = false;
   // Close every roster magic (and base InpMagic)
   ulong magics[MAX_MODELS + 1];
   int nm = 0;
   magics[nm++] = InpMagic;
   for(int s = 0; s < g_model_n; s++)
   {
      bool seen = false;
      for(int j = 0; j < nm; j++)
         if(magics[j] == g_model_magics[s]) { seen = true; break; }
      if(!seen && nm < MAX_MODELS + 1)
         magics[nm++] = g_model_magics[s];
   }
   for(int m = 0; m < nm; m++)
   {
      ulong want = magics[m];
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != want) continue;
         SetActiveSlot(FindModelSlotByMagic(want));
         string action = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
         double lots = PositionGetDouble(POSITION_VOLUME);
         double entry = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl = PositionGetDouble(POSITION_SL);
         double tp = PositionGetDouble(POSITION_TP);
         bool ok = trade.PositionClose(ticket);
         double exit_px = (action == "BUY")
            ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
            : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(ok)
         {
            any = true;
            WriteFillJsonEx("close",
               g_open_signal_id != "" ? g_open_signal_id : ("manual_close_" + IntegerToString((int)ticket)),
               action, true, reason, ticket, exit_px, sl, tp, lots, 0, reason,
               true, "manual_test");
         }
      }
   }
   if(any)
   {
      g_open_ticket = 0;
      g_open_signal_id = "";
      g_open_action = "";
      g_open_source = "strategy";
   }
   return any;
}

//+------------------------------------------------------------------+
void ProcessManualCommand()
{
   // Immediate market/close from App (GUI test) — does not wait for new bar.
   string json;
   if(!ReadCommandJson(json))
      return;

   string sid = JsonGetString(json, "signal_id");
   if(sid != "" && sid == g_last_signal_id)
   {
      ClearCommandFile();
      return;
   }

   string cmd = JsonGetString(json, "cmd");
   StringToLower(cmd);
   if(cmd == "" )
   {
      // allow action-only payload
      string act0 = JsonGetString(json, "action");
      StringToUpper(act0);
      if(act0 == "BUY" || act0 == "SELL")
         cmd = "market";
      else if(act0 == "FLAT" || act0 == "CLOSE")
         cmd = "close";
   }

   if(cmd == "close" || cmd == "flat")
   {
      bool closed = CloseAllByMagic("manual_test_close");
      WriteCommandAck(sid, closed ? "closed" : "noop", closed ? "closed" : "no_position");
      if(sid != "") g_last_signal_id = sid;
      ClearCommandFile();
      Print("ForgeBridge manual CLOSE ok=", closed);
      return;
   }

   if(cmd != "market")
   {
      WriteCommandAck(sid, "ignored", "unknown_cmd");
      ClearCommandFile();
      return;
   }

   if(PositionsByMagic() > 0)
   {
      // Prefer command magic/model; else reject only if that slot is busy
      string mid_cmd = JsonGetString(json, "model_id");
      ulong mag_cmd = (ulong)JsonGetDouble(json, "magic", 0);
      int slot_cmd = -1;
      if(mid_cmd != "") slot_cmd = FindModelSlotById(mid_cmd);
      if(slot_cmd < 0 && mag_cmd > 0) slot_cmd = FindModelSlotByMagic(mag_cmd);
      if(slot_cmd >= 0 && PositionsByMagic(g_model_magics[slot_cmd]) > 0)
      {
         WriteFillJsonEx("open", sid, JsonGetString(json, "action"), false, "already_open",
                         0, 0, 0, 0, 0, 0, "already_open");
         WriteCommandAck(sid, "rejected", "already_open");
         ClearCommandFile();
         return;
      }
      if(slot_cmd < 0)
      {
         // No target — OpenFromDecision will gate per magic
      }
   }

   bool ok = OpenFromDecision(json);
   WriteCommandAck(sid, ok ? "opened" : "rejected", ok ? "opened" : "order_failed");
   ClearCommandFile();
   Print("ForgeBridge manual MARKET ok=", ok, " sid=", sid);
}

//+------------------------------------------------------------------+
bool WaitDecisionForBar(const string want_bar_time, string &json_out, const int wait_ms_override = -1, const string model_id = "")
{
   int wait_ms = (wait_ms_override > 0) ? wait_ms_override : InpDecisionWaitMs;
   // History feed: poll tightly so low delay_ms is not wasted on Sleep(500)
   int poll = InpPollMs;
   if(InpMode == BRIDGE_HISTORY_FEED)
      poll = (int)MathMax(20, MathMin(50, InpPollMs));

   uint start = GetTickCount();
   while(GetTickCount() - start < (uint)wait_ms)
   {
      bool ok = (model_id != "")
         ? ReadDecisionJsonForModel(model_id, json_out)
         : ReadDecisionJson(json_out);
      if(ok)
      {
         // Exact bar_time only — StringFind matched expires_bar_time (= next bar)
         // and opened fills 1 bar late vs Python OOS.
         string bt = JsonGetString(json_out, "bar_time");
         if(bt == "" ) bt = JsonGetString(json_out, "time");
         if(bt == want_bar_time)
            return true;
      }
      Sleep(poll);
   }
   bool ok2 = (model_id != "")
      ? ReadDecisionJsonForModel(model_id, json_out)
      : ReadDecisionJson(json_out);
   if(!ok2)
      return false;
   string bt = JsonGetString(json_out, "bar_time");
   if(bt == "") bt = JsonGetString(json_out, "time");
   return bt == want_bar_time;
}

//+------------------------------------------------------------------+
void WriteFillJsonEx(
   const string event,
   const string signal_id,
   const string action,
   const bool ok,
   const string detail,
   const ulong ticket,
   const double price,
   const double sl,
   const double tp,
   const double lots,
   const double profit,
   const string reason,
   const bool manual = false,
   const string source = "",
   const string bar_time = ""
)
{
   string src = source;
   if(src == "")
      src = (manual || g_user_intervened) ? (g_open_source != "" ? g_open_source : "manual") : "strategy";
   string json = "{";
   json += "\"event\":\"" + event + "\",";
   json += "\"signal_id\":\"" + signal_id + "\",";
   json += "\"action\":\"" + action + "\",";
   json += "\"ok\":" + (ok ? "true" : "false") + ",";
   json += "\"detail\":\"" + detail + "\",";
   json += "\"ticket\":" + IntegerToString((long)ticket) + ",";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"M15\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"magic\":" + IntegerToString((long)(g_active_magic > 0 ? g_active_magic : InpMagic)) + ",";
   if(g_active_model_id != "")
      json += "\"model_id\":\"" + g_active_model_id + "\",";
   json += "\"price\":" + DoubleToString(price, _Digits) + ",";
   if(event == "close" && g_open_entry > 0)
      json += "\"entry\":" + DoubleToString(g_open_entry, _Digits) + ",";
   json += "\"sl\":" + DoubleToString(sl, _Digits) + ",";
   json += "\"tp\":" + DoubleToString(tp, _Digits) + ",";
   json += "\"lots\":" + DoubleToString(lots, 2) + ",";
   json += "\"profit\":" + DoubleToString(profit, 2) + ",";
   json += "\"reason\":\"" + reason + "\",";
   json += "\"manual\":" + (manual ? "true" : "false") + ",";
   json += "\"source\":\"" + src + "\",";
   if(bar_time != "")
      json += "\"bar_time\":\"" + bar_time + "\",";
   // HistoryFeed: prefer bar_time as logical clock; wall time is secondary
   if(bar_time != "")
      json += "\"time\":\"" + bar_time + "\"";
   else
      json += "\"time\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\"";
   json += "}\n";
   int h = FileOpen(BridgePath("fill.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h != INVALID_HANDLE)
   {
      FileWriteString(h, json);
      FileClose(h);
   }
   // Append queue so open+close at delay=1ms are not lost (fill.json is single-slot)
   h = FileOpen(BridgePath("ea_fills.jsonl"),
                FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h != INVALID_HANDLE)
   {
      FileSeek(h, 0, SEEK_END);
      FileWriteString(h, json);
      FileClose(h);
   }
}

void WriteFillJson(const string signal_id, const string action, const bool ok, const string detail)
{
   WriteFillJsonEx("open", signal_id, action, ok, detail, 0, 0, 0, 0, 0, 0, detail);
}

//+------------------------------------------------------------------+
string DetectCloseReasonFromHistory()
{
   datetime from = TimeCurrent() - 7 * 24 * 3600;
   if(!HistorySelect(from, TimeCurrent()))
      return "closed";
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0) continue;
      if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) continue;
      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
      long reason = HistoryDealGetInteger(deal, DEAL_REASON);
      if(reason == DEAL_REASON_SL) return "sl";
      if(reason == DEAL_REASON_TP) return "tp";
      if(reason == DEAL_REASON_SO) return "stop_out";
      if(reason == DEAL_REASON_CLIENT || reason == DEAL_REASON_MOBILE || reason == DEAL_REASON_WEB)
         return "manual_close";
      if(reason == DEAL_REASON_EXPERT) return "ea_close";
      break;
   }
   return "closed";
}

//+------------------------------------------------------------------+
bool PriceChanged(const double a, const double b)
{
   return MathAbs(a - b) > (_Point * 0.5);
}

//+------------------------------------------------------------------+
void SyncPositionLevels(const ulong ticket)
{
   // Detect user SL/TP edits vs EA trail; push modify fill to App.
   double cur_sl = PositionGetDouble(POSITION_SL);
   double cur_tp = PositionGetDouble(POSITION_TP);
   if(!PriceChanged(cur_sl, g_sync_sl) && !PriceChanged(cur_tp, g_sync_tp))
   {
      g_open_sl = cur_sl;
      g_open_tp = cur_tp;
      return;
   }

   if(g_ea_modifying)
   {
      g_sync_sl = cur_sl;
      g_sync_tp = cur_tp;
      g_open_sl = cur_sl;
      g_open_tp = cur_tp;
      g_ea_modifying = false;
      WriteFillJsonEx(
         "modify", g_open_signal_id, g_open_action, true, "ea_trail",
         ticket, g_open_entry, cur_sl, cur_tp, g_open_lots, 0, "ea_trail",
         false, "ea_trail"
      );
      return;
   }

   // User (or terminal) changed SL/TP
   g_user_intervened = true;
   g_sync_sl = cur_sl;
   g_sync_tp = cur_tp;
   g_open_sl = cur_sl;
   g_open_tp = cur_tp;
   WriteFillJsonEx(
      "modify", g_open_signal_id, g_open_action, true, "user_sl_tp",
      ticket, g_open_entry, cur_sl, cur_tp, g_open_lots, 0, "user_sl_tp",
      true, "user_edit"
   );
   Print("ForgeBridge user SL/TP edit sl=", cur_sl, " tp=", cur_tp);
}

//+------------------------------------------------------------------+
bool OpenFromDecision(const string json)
{
   string action = JsonGetString(json, "action");
   StringToUpper(action);
   if(action != "BUY" && action != "SELL")
      return false;

   string sid = JsonGetString(json, "signal_id");
   if(sid != "" && sid == g_last_signal_id)
      return false;

   // Bind magic / model from decision (multi-model roster)
   LoadModelsRoster();
   string mid = JsonGetString(json, "model_id");
   ulong magic = (ulong)JsonGetDouble(json, "magic", 0);
   int slot = -1;
   if(mid != "")
      slot = FindModelSlotById(mid);
   if(slot < 0 && magic > 0)
      slot = FindModelSlotByMagic(magic);
   if(slot < 0 && g_model_n > 0)
      slot = 0;
   if(slot >= 0)
      SetActiveSlot(slot);
   else
   {
      g_active_magic = (magic > 0) ? magic : InpMagic;
      g_active_model_id = mid;
      trade.SetExpertMagicNumber((int)g_active_magic);
   }
   if(PositionsByMagic(g_active_magic) > 0)
   {
      WriteFillJsonEx("open", sid, action, false, "already_open",
                      0, 0, 0, 0, 0, 0, "already_open");
      return false;
   }

   string cmd0 = JsonGetString(json, "cmd");
   StringToLower(cmd0);
   string reason0 = JsonGetString(json, "reason");
   StringToLower(reason0);
   bool manual_open = (cmd0 == "market") || (StringFind(reason0, "manual") >= 0)
                      || (StringFind(sid, "manual_test") == 0);
   g_open_source = manual_open ? "manual_test" : "strategy";
   g_user_intervened = manual_open;
   g_ea_modifying = false;

   double planned = JsonGetDouble(json, "entry", 0);
   double sl = JsonGetDouble(json, "sl", 0);
   double tp = JsonGetDouble(json, "tp", 0);

   string em = JsonGetString(json, "exit_mode");
   StringToLower(em);
   if(em == "full" || em == "0") g_exit_mode = 0;
   else if(em == "hybrid" || em == "1") g_exit_mode = 1;
   else if(em == "trail" || em == "2") g_exit_mode = 2;
   else if(em == "partial" || em == "3") g_exit_mode = 3;
   else g_exit_mode = 2;
   g_trail_act = JsonGetDouble(json, "trail_activate_r", 1.0);
   g_trail_dist = JsonGetDouble(json, "trail_distance_r", 0.5);
   g_max_hold = (int)JsonGetDouble(json, "max_hold_bars", InpMaxHoldBars);

   double price = (action == "BUY")
      ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
      : SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(sl <= 0 || tp <= 0)
   {
      Print("ForgeBridge: decision missing sl/tp");
      return false;
   }

   // Same as HistoryFeed paper: decision SL/TP are vs planned entry; live fills
   // at current bid/ask. Rebase so risk/RR (and lot size) stay as intended —
   // otherwise risk collapses → oversized lots + inflated R.
   double planned_risk = (planned > 0.0) ? MathAbs(planned - sl) : 0.0;
   double rr = JsonGetDouble(json, "rr", 0.0);
   if(rr <= 0.0 && planned_risk > 0.0 && planned > 0.0)
      rr = MathAbs(tp - planned) / planned_risk;
   if(rr <= 0.0)
      rr = 2.0;

   if(planned_risk > 0.0)
   {
      if(action == "BUY")
      {
         sl = price - planned_risk;
         tp = price + planned_risk * rr;
      }
      else
      {
         sl = price + planned_risk;
         tp = price - planned_risk * rr;
      }
   }
   else if(planned > 0.0)
   {
      double delta = price - planned;
      sl += delta;
      tp += delta;
   }

   double sl_dist = MathAbs(price - sl);
   if(sl_dist <= 0) return false;
   double pip = (_Digits == 3 || _Digits == 5) ? (10.0 * _Point) : _Point;
   if(sl_dist < 0.5 * pip)
   {
      Print("ForgeBridge: risk too small after rebase (", sl_dist, ")");
      return false;
   }
   g_risk = sl_dist;
   double lots = LotsForRisk(sl_dist);
   if(lots <= 0) return false;

   bool ok = false;
   if(action == "BUY")
      ok = trade.Buy(lots, _Symbol, price, sl, tp, "Bridge BUY");
   else
      ok = trade.Sell(lots, _Symbol, price, sl, tp, "Bridge SELL");

   ulong ticket = ok ? (ulong)trade.ResultOrder() : 0;
   // Prefer position ticket if available
   if(ok)
   {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong t = PositionGetTicket(i);
         if(!PositionSelectByTicket(t)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != g_active_magic) continue;
         ticket = t;
         price = PositionGetDouble(POSITION_PRICE_OPEN);
         sl = PositionGetDouble(POSITION_SL);
         tp = PositionGetDouble(POSITION_TP);
         lots = PositionGetDouble(POSITION_VOLUME);
         break;
      }
      // Keep R / trail math on intended risk (fill may differ slightly from request)
      if(planned_risk > 0.0)
         g_risk = planned_risk;
      else
         g_risk = MathAbs(price - sl);
      g_open_ticket = ticket;
      g_open_signal_id = sid;
      g_open_action = action;
      g_open_entry = price;
      g_open_sl = sl;
      g_open_tp = tp;
      g_open_lots = lots;
      g_sync_sl = sl;
      g_sync_tp = tp;
      g_had_position = true;
      g_last_signal_id = sid;
      Print("ForgeBridge entry ", action, " ticket=", ticket, " lots=", lots,
            " entry=", price, " sl=", sl, " tp=", tp,
            " risk=", g_risk, " source=", g_open_source);
   }

   WriteFillJsonEx("open", sid, action, ok, ok ? "opened" : IntegerToString(trade.ResultRetcode()),
                   ticket, price, sl, tp, lots, 0, ok ? "opened" : "reject",
                   manual_open, g_open_source);
   return ok;
}

//+------------------------------------------------------------------+
void ReportCloseIfNeeded(const string reason)
{
   if(g_open_ticket == 0 && g_open_signal_id == "")
      return;
   // Prefer deal profit from history for this position
   double profit = 0;
   double exit_px = (g_open_action == "BUY")
      ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
      : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   string close_reason = reason;
   datetime from = TimeCurrent() - 7 * 24 * 3600;
   if(HistorySelect(from, TimeCurrent()))
   {
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
      {
         ulong deal = HistoryDealGetTicket(i);
         if(deal == 0) continue;
         if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic) continue;
         if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) continue;
         long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
         if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
         profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                + HistoryDealGetDouble(deal, DEAL_SWAP)
                + HistoryDealGetDouble(deal, DEAL_COMMISSION);
         exit_px = HistoryDealGetDouble(deal, DEAL_PRICE);
         break;
      }
   }
   if(close_reason == "" || close_reason == "closed")
      close_reason = DetectCloseReasonFromHistory();
   bool manual_close = g_user_intervened
                       || close_reason == "manual_close"
                       || close_reason == "manual_test_close"
                       || g_open_source == "manual_test";
   WriteFillJsonEx("close", g_open_signal_id, g_open_action, true, close_reason,
                   g_open_ticket, exit_px, g_open_sl, g_open_tp, g_open_lots, profit, close_reason,
                   manual_close, manual_close ? (g_open_source == "manual_test" ? "manual_test" : "user_edit") : "strategy",
                   (InpMode == BRIDGE_HISTORY_FEED ? g_sim_last_bar : ""));
   g_open_ticket = 0;
   g_open_signal_id = "";
   g_open_source = "strategy";
   g_user_intervened = false;
   g_ea_modifying = false;
   g_sync_sl = 0;
   g_sync_tp = 0;
   g_had_position = false;
}

//+------------------------------------------------------------------+
void ManageOpen()
{
   LoadModelsRoster();
   // Detect closes for any roster magic
   static bool s_had[MAX_MODELS];
   static bool s_init = false;
   if(!s_init)
   {
      ArrayInitialize(s_had, false);
      s_init = true;
   }
   for(int s = 0; s < g_model_n; s++)
   {
      int n = PositionsByMagic(g_model_magics[s]);
      if(s_had[s] && n == 0)
      {
         SetActiveSlot(s);
         ReportCloseIfNeeded("closed");
         s_had[s] = false;
      }
      if(n > 0)
         s_had[s] = true;
   }

   for(int s = 0; s < g_model_n; s++)
   {
      ulong want = g_model_magics[s];
      if(PositionsByMagic(want) == 0)
         continue;
      SetActiveSlot(s);
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != want) continue;

         g_open_ticket = ticket;
         g_open_entry = PositionGetDouble(POSITION_PRICE_OPEN);
         g_open_lots = PositionGetDouble(POSITION_VOLUME);
         g_open_action = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
         g_had_position = true;

         // Keep App SL/TP in sync (user edits → mode manual)
         SyncPositionLevels(ticket);

         datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
         int held = (int)((TimeCurrent() - open_time) / PeriodSeconds(PERIOD_M15));
         if(held >= g_max_hold)
         {
            if(trade.PositionClose(ticket))
               ReportCloseIfNeeded("max_hold");
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

         if(g_exit_mode == 1 || g_exit_mode == 2)
         {
            if(type == POSITION_TYPE_BUY)
            {
               if(bid >= open_price + risk * g_trail_act)
               {
                  double nsl = bid - risk * g_trail_dist;
                  if(nsl > sl)
                  {
                     g_ea_modifying = true;
                     if(!trade.PositionModify(ticket, nsl, tp))
                        g_ea_modifying = false;
                  }
               }
            }
            else
            {
               if(ask <= open_price - risk * g_trail_act)
               {
                  double nsl = ask + risk * g_trail_dist;
                  if(sl == 0 || nsl < sl)
                  {
                     g_ea_modifying = true;
                     if(!trade.PositionModify(ticket, nsl, tp))
                        g_ea_modifying = false;
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
bool LoadReplayCsv()
{
   int h = FileOpen(BridgePath("replay_signals.csv"), FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return false;

   ArrayResize(g_rep_time, 0);
   ArrayResize(g_rep_dir, 0);
   ArrayResize(g_rep_atr, 0);
   ArrayResize(g_rep_rr, 0);
   ArrayResize(g_rep_exit, 0);
   ArrayResize(g_rep_tact, 0);
   ArrayResize(g_rep_tdist, 0);
   ArrayResize(g_rep_hold, 0);
   g_rep_n = 0;

   // header
   if(!FileIsEnding(h))
      FileReadString(h);

   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      StringTrimLeft(line);
      StringTrimRight(line);
      if(StringLen(line) < 8) continue;
      string parts[];
      int n = StringSplit(line, ',', parts);
      if(n < 8) continue;
      int i = g_rep_n;
      ArrayResize(g_rep_time, i + 1);
      ArrayResize(g_rep_dir, i + 1);
      ArrayResize(g_rep_atr, i + 1);
      ArrayResize(g_rep_rr, i + 1);
      ArrayResize(g_rep_exit, i + 1);
      ArrayResize(g_rep_tact, i + 1);
      ArrayResize(g_rep_tdist, i + 1);
      ArrayResize(g_rep_hold, i + 1);
      g_rep_time[i] = parts[0];
      g_rep_dir[i] = (int)StringToInteger(parts[1]);
      g_rep_atr[i] = StringToDouble(parts[2]);
      g_rep_rr[i] = StringToDouble(parts[3]);
      g_rep_exit[i] = (int)StringToInteger(parts[4]);
      g_rep_tact[i] = StringToDouble(parts[5]);
      g_rep_tdist[i] = StringToDouble(parts[6]);
      g_rep_hold[i] = (int)StringToInteger(parts[7]);
      g_rep_n++;
   }
   FileClose(h);
   return (g_rep_n > 0);
}

//+------------------------------------------------------------------+
double AtrAt(int shift)
{
   int bars = 120;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 0, bars, rates) < bars)
      return 0;
   double alpha = 1.0 / 14.0;
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

//+------------------------------------------------------------------+
int FindReplayIndex(datetime t1)
{
   string key = TimeToString(t1, TIME_DATE | TIME_MINUTES);
   for(int i = MathMax(0, g_rep_cursor - 2); i < g_rep_n; i++)
   {
      if(g_rep_time[i] == key)
      {
         g_rep_cursor = i;
         return i;
      }
   }
   // fuzzy: compare parsed times
   for(int i = MathMax(0, g_rep_cursor - 2); i < g_rep_n; i++)
   {
      datetime st = StringToTime(g_rep_time[i]);
      if(st == t1)
      {
         g_rep_cursor = i;
         return i;
      }
      if(st > t1 + 7 * 24 * 3600)
         break;
   }
   return -1;
}

//+------------------------------------------------------------------+
void OpenFromReplay(int idx)
{
   int dir = g_rep_dir[idx];
   double atr = AtrAt(1);
   if(atr <= 0) return;
   double sl_dist = g_rep_atr[idx] * atr;
   double rr = g_rep_rr[idx];
   double price = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (dir > 0) ? price - sl_dist : price + sl_dist;
   double tp = (dir > 0) ? price + sl_dist * rr : price - sl_dist * rr;
   double lots = LotsForRisk(sl_dist);
   if(lots <= 0) return;

   g_risk = sl_dist;
   g_exit_mode = g_rep_exit[idx];
   g_trail_act = g_rep_tact[idx];
   g_trail_dist = g_rep_tdist[idx];
   g_max_hold = g_rep_hold[idx];

   bool ok = false;
   if(dir > 0) ok = trade.Buy(lots, _Symbol, price, sl, tp, "BridgeReplay LONG");
   else ok = trade.Sell(lots, _Symbol, price, sl, tp, "BridgeReplay SHORT");
   if(ok)
      Print("ForgeBridge Replay entry ", (dir > 0 ? "LONG" : "SHORT"), " idx=", idx);
}

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
datetime ParseControlDate(string s)
{
   StringReplace(s, "-", ".");
   StringReplace(s, "T", " ");
   StringTrimLeft(s);
   StringTrimRight(s);
   if(StringLen(s) == 10)
      s += " 00:00";
   return StringToTime(s);
}

bool ReadSimControlFile()
{
   int h = FileOpen(BridgePath("sim_control.json"),
                    FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return false;
   string json = "";
   while(!FileIsEnding(h))
      json += FileReadString(h) + "\n";
   FileClose(h);
   if(StringLen(json) < 5)
      return false;

   g_sim_enabled = JsonGetBool(json, "enabled", false);
   string fr = JsonGetString(json, "from");
   string to = JsonGetString(json, "to");
   if(fr != "") g_sim_from = fr;
   if(to != "") g_sim_to = to;
   int delay = (int)JsonGetDouble(json, "delay_ms", g_sim_delay_ms);
   g_sim_delay_ms = (int)MathMax(1, delay);
   string rid = JsonGetString(json, "request_id");
   if(rid != "") g_sim_request_id = rid;
   return true;
}

void WriteSimControlFile()
{
   string json = "{";
   json += "\"enabled\":" + (g_sim_enabled ? "true" : "false") + ",";
   json += "\"from\":\"" + g_sim_from + "\",";
   json += "\"to\":\"" + g_sim_to + "\",";
   json += "\"delay_ms\":" + IntegerToString(g_sim_delay_ms) + ",";
   json += "\"request_id\":\"" + g_sim_request_id + "\",";
   json += "\"ea_status\":\"" + g_sim_ea_status + "\",";
   json += "\"bars_done\":" + IntegerToString(g_hist_cursor) + ",";
   json += "\"bars_total\":" + IntegerToString(g_hist_n) + ",";
   json += "\"last_bar\":\"" + g_sim_last_bar + "\",";
   json += "\"error\":\"" + g_sim_error + "\",";
   json += "\"updated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\"";
   json += "}\n";
   int h = FileOpen(BridgePath("sim_control.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, json);
   FileClose(h);
}

bool LoadHistoryRatesRange()
{
   datetime t_from = ParseControlDate(g_sim_from);
   datetime t_to = ParseControlDate(g_sim_to);
   if(t_from <= 0 || t_to <= 0 || t_to < t_from)
   {
      g_sim_error = "bad_from_to";
      g_sim_ea_status = "error";
      return false;
   }
   // Include the full end day when only a date is given
   if(StringLen(g_sim_to) <= 10)
      t_to += PeriodSeconds(PERIOD_M15) * 96 - 1;

   ArrayFree(g_hist_rates);
   ArraySetAsSeries(g_hist_rates, false);
   int copied = CopyRates(_Symbol, PERIOD_M15, t_from, t_to, g_hist_rates);
   if(copied < 1)
   {
      g_sim_error = "copy_rates_failed";
      g_sim_ea_status = "error";
      g_hist_n = 0;
      return false;
   }
   g_hist_n = copied;
   g_hist_cursor = 0;
   g_sim_error = "";
   g_pending_decision = "";
   g_paper_open = false;
   g_paper_held = 0;
   g_last_signal_id = "";
   g_open_ticket = 0;
   g_open_signal_id = "";
   g_had_position = false;
   Print("ForgeBridgeM15J9 HistoryFeed loaded bars=", g_hist_n,
         " from=", TimeToString(g_hist_rates[0].time, TIME_DATE | TIME_MINUTES),
         " to=", TimeToString(g_hist_rates[g_hist_n - 1].time, TIME_DATE | TIME_MINUTES));
   return true;
}

void ReportPaperClose(const string reason, const double exit_px, const string bar_time = "")
{
   if(!g_paper_open)
      return;
   double profit = 0;
   if(g_risk > 0)
   {
      if(g_open_action == "BUY")
         profit = (exit_px - g_open_entry) / g_risk;
      else
         profit = (g_open_entry - exit_px) / g_risk;
   }
   string bt = bar_time;
   if(bt == "")
      bt = g_sim_last_bar;
   WriteFillJsonEx("close", g_open_signal_id, g_open_action, true, reason,
                   g_open_ticket, exit_px, g_open_sl, g_open_tp, g_open_lots, profit, reason,
                   false, "strategy", bt);
   // Include entry on close payload via price fields already; App open may have been missed —
   // also stamp entry into a dedicated field by rewriting is hard in MQL; bar_time helps chart.
   g_paper_open = false;
   g_paper_held = 0;
   g_open_ticket = 0;
   g_open_signal_id = "";
   g_open_sl_initial = 0;
   g_had_position = false;
}

void ManagePaperHistory(const MqlRates &r)
{
   if(!g_paper_open)
      return;
   g_paper_held++;

   // Python backtest_mined enters at open then starts SL/TP/trail on the *next* bar
   // (i = entry_idx + 1). Checking the entry bar here caused same-bar SL and R drift.
   if(g_paper_held <= 1)
      return;

   // Match Python OOS trail: activate/move from bar high (BUY) / low (SELL)
   if(g_exit_mode == 1 || g_exit_mode == 2)
   {
      if(g_open_action == "BUY")
      {
         if(r.high >= g_open_entry + g_risk * g_trail_act)
         {
            double nsl = r.high - g_risk * g_trail_dist;
            if(nsl > g_open_sl)
               g_open_sl = nsl;
         }
      }
      else
      {
         if(r.low <= g_open_entry - g_risk * g_trail_act)
         {
            double nsl = r.low + g_risk * g_trail_dist;
            if(g_open_sl == 0 || nsl < g_open_sl)
               g_open_sl = nsl;
         }
      }
   }

   const bool trail_moved = (g_open_sl_initial > 0.0
                             && MathAbs(g_open_sl - g_open_sl_initial) > (_Point * 0.5));

   if(g_open_action == "BUY")
   {
      if(g_open_sl > 0 && r.low <= g_open_sl)
      {
         ReportPaperClose(trail_moved ? "trail" : "sl", g_open_sl,
                          TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
      if(g_open_tp > 0 && r.high >= g_open_tp)
      {
         ReportPaperClose("tp", g_open_tp, TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
   }
   else
   {
      if(g_open_sl > 0 && r.high >= g_open_sl)
      {
         ReportPaperClose(trail_moved ? "trail" : "sl", g_open_sl,
                          TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
      if(g_open_tp > 0 && r.low <= g_open_tp)
      {
         ReportPaperClose("tp", g_open_tp, TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
   }

   // held includes entry bar; Python uses (i - entry_idx) >= max_hold
   if(g_paper_held - 1 >= g_max_hold)
      ReportPaperClose("max_hold", r.close, TimeToString(r.time, TIME_DATE | TIME_MINUTES));
}

bool PaperOpenFromDecision(const string json, const double entry_price, const string bar_time = "")
{
   string action = JsonGetString(json, "action");
   StringToUpper(action);
   if(action != "BUY" && action != "SELL")
      return false;

   string sid = JsonGetString(json, "signal_id");
   if(sid != "" && sid == g_last_signal_id)
      return false;

   LoadModelsRoster();
   string mid = JsonGetString(json, "model_id");
   ulong magic = (ulong)JsonGetDouble(json, "magic", 0);
   int slot = -1;
   if(mid != "")
      slot = FindModelSlotById(mid);
   if(slot < 0 && magic > 0)
      slot = FindModelSlotByMagic(magic);
   if(slot < 0 && g_model_n > 0)
      slot = 0;
   if(slot >= 0)
      SetActiveSlot(slot);
   else
   {
      g_active_magic = (magic > 0) ? magic : InpMagic;
      g_active_model_id = mid;
   }

   double planned = JsonGetDouble(json, "entry", 0);
   double sl = JsonGetDouble(json, "sl", 0);
   double tp = JsonGetDouble(json, "tp", 0);
   if(sl <= 0 || tp <= 0 || entry_price <= 0)
      return false;

   string em = JsonGetString(json, "exit_mode");
   StringToLower(em);
   if(em == "full" || em == "0") g_exit_mode = 0;
   else if(em == "hybrid" || em == "1") g_exit_mode = 1;
   else if(em == "trail" || em == "2") g_exit_mode = 2;
   else if(em == "partial" || em == "3") g_exit_mode = 3;
   else g_exit_mode = 2;
   g_trail_act = JsonGetDouble(json, "trail_activate_r", 1.0);
   g_trail_dist = JsonGetDouble(json, "trail_distance_r", 0.5);
   g_max_hold = (int)JsonGetDouble(json, "max_hold_bars", InpMaxHoldBars);

   // Rebase SL/TP onto actual fill open using planned risk/RR from App decision.
   // HistoryFeed fills at bar open (raw); decision levels are vs spread-adjusted
   // planned entry — without rebase, risk collapses and paper R explodes vs OOS.
   double planned_risk = (planned > 0.0) ? MathAbs(planned - sl) : 0.0;
   double rr = JsonGetDouble(json, "rr", 0.0);
   if(rr <= 0.0 && planned_risk > 0.0 && planned > 0.0)
      rr = MathAbs(tp - planned) / planned_risk;
   if(rr <= 0.0)
      rr = 2.0;

   if(planned_risk > 0.0)
   {
      if(action == "BUY")
      {
         sl = entry_price - planned_risk;
         tp = entry_price + planned_risk * rr;
      }
      else
      {
         sl = entry_price + planned_risk;
         tp = entry_price - planned_risk * rr;
      }
   }
   else
   {
      // No planned entry: shift absolute levels by fill delta if possible
      if(planned > 0.0)
      {
         double delta = entry_price - planned;
         sl += delta;
         tp += delta;
      }
   }

   double sl_dist = MathAbs(entry_price - sl);
   if(sl_dist <= 0.0)
      return false;
   // Guard: refuse near-zero risk (< 0.5 pip) after rebase
   double pip = (_Digits == 3 || _Digits == 5) ? (10.0 * _Point) : _Point;
   if(sl_dist < 0.5 * pip)
      return false;

   g_risk = sl_dist;
   double lots = LotsForRisk(sl_dist);
   if(lots <= 0) lots = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   g_paper_ticket++;
   g_open_ticket = g_paper_ticket;
   g_open_signal_id = sid;
   g_open_action = action;
   g_open_entry = entry_price;
   g_open_sl = sl;
   g_open_sl_initial = sl;
   g_open_tp = tp;
   g_open_lots = lots;
   g_open_source = "strategy";
   g_user_intervened = false;
   g_had_position = true;
   g_paper_open = true;
   g_paper_held = 0;
   g_last_signal_id = sid;

   string bt = bar_time;
   if(bt == "")
      bt = g_sim_last_bar;
   WriteFillJsonEx("open", sid, action, true, "opened",
                   g_open_ticket, entry_price, sl, tp, lots, 0, "opened",
                   false, "strategy", bt);
   Print("ForgeBridgeM15J9 HistoryFeed paper ", action, " @", entry_price,
         " sl=", sl, " tp=", tp, " risk=", sl_dist,
         " sid=", sid, " bar=", bt);
   return true;
}

void ApplyPendingOpen(const MqlRates &r)
{
   LoadModelsRoster();
   string bt = TimeToString(r.time, TIME_DATE | TIME_MINUTES);
   for(int s = 0; s < g_model_n; s++)
   {
      if(g_slot_pending[s] == "")
         continue;
      if(InpHistoryPaperFills)
      {
         if(g_slot_paper_open[s])
            continue;
      }
      else if(PositionsByMagic(g_model_magics[s]) > 0)
         continue;
      SetActiveSlot(s);
      bool ok = false;
      if(InpHistoryPaperFills)
         ok = PaperOpenFromDecision(g_slot_pending[s], r.open, bt);
      else
         ok = OpenFromDecision(g_slot_pending[s]);
      if(ok && InpHistoryPaperFills)
      {
         g_slot_paper_open[s] = true;
         g_slot_paper_held[s] = 0;
         g_slot_ticket[s] = g_open_ticket;
         g_slot_sid[s] = g_open_signal_id;
         g_slot_action[s] = g_open_action;
         g_slot_entry[s] = g_open_entry;
         g_slot_sl[s] = g_open_sl;
         g_slot_sl_init[s] = g_open_sl_initial;
         g_slot_tp[s] = g_open_tp;
         g_slot_lots[s] = g_open_lots;
         g_slot_risk[s] = g_risk;
         g_slot_exit_mode[s] = g_exit_mode;
         g_slot_trail_act[s] = g_trail_act;
         g_slot_trail_dist[s] = g_trail_dist;
         g_slot_max_hold[s] = g_max_hold;
      }
      g_slot_pending[s] = "";
   }
   // Compat aliases
   g_paper_open = false;
   g_pending_decision = "";
   for(int i = 0; i < g_model_n; i++)
   {
      if(g_slot_paper_open[i])
         g_paper_open = true;
      if(g_slot_pending[i] != "")
         g_pending_decision = g_slot_pending[i];
   }
}

void ManagePaperHistoryAll(const MqlRates &r)
{
   for(int s = 0; s < g_model_n; s++)
   {
      if(!g_slot_paper_open[s])
         continue;
      SetActiveSlot(s);
      g_open_ticket = g_slot_ticket[s];
      g_open_signal_id = g_slot_sid[s];
      g_open_action = g_slot_action[s];
      g_open_entry = g_slot_entry[s];
      g_open_sl = g_slot_sl[s];
      g_open_sl_initial = g_slot_sl_init[s];
      g_open_tp = g_slot_tp[s];
      g_open_lots = g_slot_lots[s];
      g_risk = g_slot_risk[s];
      g_exit_mode = g_slot_exit_mode[s];
      g_trail_act = g_slot_trail_act[s];
      g_trail_dist = g_slot_trail_dist[s];
      g_max_hold = g_slot_max_hold[s];
      g_paper_open = true;
      g_paper_held = g_slot_paper_held[s];
      g_had_position = true;
      ManagePaperHistory(r);
      g_slot_paper_held[s] = g_paper_held;
      g_slot_sl[s] = g_open_sl;
      g_slot_tp[s] = g_open_tp;
      if(!g_paper_open || g_open_ticket == 0)
      {
         g_slot_paper_open[s] = false;
         g_slot_ticket[s] = 0;
         g_slot_sid[s] = "";
      }
   }
   g_paper_open = false;
   for(int i = 0; i < g_model_n; i++)
      if(g_slot_paper_open[i])
         g_paper_open = true;
}

void ProcessHistoryFeed()
{
   static string s_loaded_request = "";

   if(!ReadSimControlFile())
      return;

   if(!g_sim_enabled)
   {
      if(g_sim_ea_status == "running")
      {
         g_sim_ea_status = "idle";
         WriteSimControlFile();
      }
      return;
   }

   if(g_sim_request_id == "" || g_sim_from == "" || g_sim_to == "")
   {
      g_sim_error = "missing_control_fields";
      g_sim_ea_status = "error";
      WriteSimControlFile();
      return;
   }

   if(s_loaded_request != g_sim_request_id)
   {
      if(!LoadHistoryRatesRange())
      {
         WriteSimControlFile();
         return;
      }
      s_loaded_request = g_sim_request_id;
      g_sim_ea_status = "running";
      WriteSimControlFile();
   }

   if(g_hist_n < 1 || g_hist_cursor >= g_hist_n)
   {
      if(g_paper_open && g_hist_n > 0)
         ReportPaperClose(
           "end_range",
           g_hist_rates[g_hist_n - 1].close,
           TimeToString(g_hist_rates[g_hist_n - 1].time, TIME_DATE | TIME_MINUTES)
         );
      else if(g_had_position && PositionsByMagic() > 0)
         CloseAllByMagic("end_range");
      g_sim_ea_status = "completed";
      g_sim_enabled = false;
      WriteSimControlFile();
      Print("ForgeBridgeM15J9 HistoryFeed completed bars=", g_hist_n);
      return;
   }

   MqlRates r = g_hist_rates[g_hist_cursor];

   // Open pending from previous bar decision at this bar's open
   ApplyPendingOpen(r);

   if(InpHistoryPaperFills)
      ManagePaperHistoryAll(r);
   else
      ManageOpen();

   if(!WriteBarJsonFromRate(r))
   {
      g_sim_error = "write_bar_failed";
      g_sim_ea_status = "error";
      WriteSimControlFile();
      return;
   }
   WriteBarsJsonHistoryFeed(g_hist_cursor + 1);
   WriteConnectionJson();

   string want = TimeToString(r.time, TIME_DATE | TIME_MINUTES);
   g_sim_last_bar = want;

   // Ask each flat model for a decision (parallel models, shared wait budget)
   LoadModelsRoster();
   int wait_ms = (int)MathMax(5000, MathMin(InpHistoryDecisionWaitMs, g_sim_delay_ms + 8000));
   wait_ms = (int)MathMax(wait_ms, 3000 * MathMax(1, g_model_n));
   for(int s = 0; s < g_model_n; s++)
   {
      bool flat = InpHistoryPaperFills
         ? (!g_slot_paper_open[s])
         : (PositionsByMagic(g_model_magics[s]) == 0);
      if(!flat || g_slot_pending[s] != "")
         continue;
      string json;
      if(WaitDecisionForBar(want, json, wait_ms, g_model_ids[s]))
      {
         string action = JsonGetString(json, "action");
         StringToUpper(action);
         if(action == "BUY" || action == "SELL")
            g_slot_pending[s] = json;
      }
      else if(g_model_n == 1)
         Print("ForgeBridgeM15J9 HistoryFeed: no decision for ", want,
               " (waited ", wait_ms, "ms — Start feed App / bridge_sim loop?)");
   }

   g_hist_cursor++;
   g_sim_ea_status = "running";
   g_sim_error = "";
   // Re-read so App Stop/Pause (enabled=false) is not overwritten
   bool still = g_sim_enabled;
   string keep_status = g_sim_ea_status;
   string keep_last = g_sim_last_bar;
   string keep_err = g_sim_error;
   int keep_cursor = g_hist_cursor;
   ReadSimControlFile();
   g_sim_ea_status = keep_status;
   g_sim_last_bar = keep_last;
   g_sim_error = keep_err;
   g_hist_cursor = keep_cursor;
   if(!still)
      g_sim_enabled = false;
   WriteSimControlFile();

   Sleep((int)MathMax(1, g_sim_delay_ms));
}

//+------------------------------------------------------------------+
void OnTick()
{
   // History feed is timer-driven; do not trade live ticks in parallel
   if(InpMode == BRIDGE_HISTORY_FEED)
      return;

   LoadModelsRoster();
   ManageOpen();

   uint now_ms = GetTickCount();
   if(g_last_heartbeat_ms == 0 || now_ms - g_last_heartbeat_ms >= (uint)MathMax(500, InpHeartbeatMs))
   {
      WriteConnectionJson();
      g_last_heartbeat_ms = now_ms;
   }

   ProcessManualCommand();

   datetime t0 = iTime(_Symbol, PERIOD_M15, 0);
   if(t0 == 0 || t0 == g_last_bar)
      return;
   g_last_bar = t0;
   WriteBarsJson();

   datetime t1 = iTime(_Symbol, PERIOD_M15, 1);
   if(t1 == 0 || t1 == g_last_fill_bar)
      return;

   if(InpMode == BRIDGE_REPLAY)
   {
      if(PositionsByMagic(InpMagic) > 0)
         return;
      int idx = FindReplayIndex(t1);
      if(idx < 0) return;
      OpenFromReplay(idx);
      g_last_fill_bar = t1;
      return;
   }

   // Live: publish closed bar, wait for App decision(s) — one open per model magic
   if(!WriteBarJson(t1))
      return;

   string want = TimeToString(t1, TIME_DATE | TIME_MINUTES);
   bool any_open = false;
   for(int s = 0; s < g_model_n; s++)
   {
      if(PositionsByMagic(g_model_magics[s]) > 0)
         continue;
      string json;
      if(!WaitDecisionForBar(want, json, -1, g_model_ids[s]))
      {
         if(g_model_n == 1)
            Print("ForgeBridge: no decision for ", want);
         continue;
      }
      string action = JsonGetString(json, "action");
      StringToUpper(action);
      if(action == "FLAT" || action == "HOLD" || action == "")
         continue;
      SetActiveSlot(s);
      if(OpenFromDecision(json))
         any_open = true;
   }
   if(any_open)
      g_last_fill_bar = t1;
}
//+------------------------------------------------------------------+
