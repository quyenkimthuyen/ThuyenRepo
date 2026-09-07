//+------------------------------------------------------------------+
//| ForgeBridgeLC2G23.mq5 — EdgeMiner GBPUSD M15 (magic 20281041, bridge_lc2_g23)
//| Thin execution EA — App (Best 3m) decides via mt5/bridge_live files.  |
//| Modes:                                                           |
//|   Live         — write bar.json, read decision.json (App)        |
//|   Replay       — read replay_signals.csv (Strategy Tester)       |
//|   HistoryFeed  — CopyRates paced by App sim_control.json         |
//| Keep ForgeBest3m_Frozen / ForgeBest3m_WF for MT5 side-by-side.   |
//+------------------------------------------------------------------+
#property copyright "EdgeMinerM15 bridge"
#property version   "1.28"

#include <Trade/Trade.mqh>

enum ENUM_BRIDGE_MODE
{
   BRIDGE_LIVE = 0,           // Live file bridge
   BRIDGE_REPLAY = 1,         // Replay CSV (tester)
   BRIDGE_HISTORY_FEED = 2    // App-controlled historical bar feed
};

input group "=== Bridge ==="
input ENUM_BRIDGE_MODE InpMode = BRIDGE_LIVE;
input string InpBridgeSubdir   = "bridge_lc2_g23";          // under MQL5/Files/ (use bridge_sim for HistoryFeed)
input int    InpDecisionWaitMs = 60000;             // Live: shared wait for ALL models (parallel poll)
input int    InpHistoryDecisionWaitMs = 20000;      // HistoryFeed: max wait (remine tuần có thể chậm)
input int    InpPollMs         = 500;
input int    InpChartBars      = 1344;              // M15 bars exported for App chart
input int    InpHeartbeatMs    = 2000;              // Live connection/tick snapshot
input int    InpHistoryChunk   = 750;               // Bars per history sync response
input bool   InpHistoryPaperFills = true;           // HistoryFeed: paper fills from OHLC (no OrderSend)
input bool   InpShowComment    = true;              // Chart Comment: bar + per-model sync status

input group "=== Risk ==="
input double InpRiskPct        = 1.0;
input ulong  InpMagic          = 20281041;        // base magic; multi-model uses models.json
input int    InpMaxModels      = 5;               // max concurrent trade models
input int    InpSlipPoints     = 30;
input int    InpMaxHoldBars    = 36;                // fallback if decision omits

CTrade   trade;
const string INSTANCE_ID = "LC2G23";

bool UsePaperFills()
{
   // HistoryFeed must never OrderSend — broker fills current market, not OOS close.
   if(InpMode == BRIDGE_HISTORY_FEED)
      return true;
   return InpHistoryPaperFills;
}

string PeriodTag()
{
   ENUM_TIMEFRAMES p = Period();
   if(p == PERIOD_M1)  return "M1";
   if(p == PERIOD_M5)  return "M5";
   if(p == PERIOD_M15) return "M15";
   if(p == PERIOD_M30) return "M30";
   if(p == PERIOD_H1)  return "H1";
   if(p == PERIOD_H4)  return "H4";
   if(p == PERIOD_D1)  return "D1";
   string s = EnumToString(p);
   StringReplace(s, "PERIOD_", "");
   return s;
}


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
int      g_active_slot = -1;        // roster slot owning g_sync_* / g_user_intervened
int      g_exit_mode = 0;
double   g_trail_act = 1.0;
double   g_trail_dist = 0.5;
int      g_max_hold = 36;
bool     g_had_position = false;
uint     g_last_heartbeat_ms = 0;
string   g_last_history_request = "";

// Chart / App sync status (last closed-bar handshake)
string   g_sync_bar = "";
string   g_sync_summary = "boot";
string   g_sync_line[MAX_MODELS];
string   g_sync_status[MAX_MODELS];   // OK|TIMEOUT|OPEN|FLAT|BUY|SELL|...
string   g_sync_action[MAX_MODELS];
int      g_sync_n = 0;
bool     g_late_pending = false;      // TIMEOUT slots — keep polling after wait budget
datetime g_pending_bar_dt = 0;        // closed bar time for late recovery
uint     g_last_comment_ms = 0;

// Multi-model roster (App writes models.json)
string   g_model_ids[MAX_MODELS];
ulong    g_model_magics[MAX_MODELS];
double   g_model_risk_pct[MAX_MODELS];  // per-model; 0 → fallback
int      g_model_n = 0;
double   g_roster_risk_pct = 0;   // 0 = use InpRiskPct (legacy top-level fallback)
ulong    g_roster_base_magic = 0; // models.json base_magic — orphan sweep
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
double   g_slot_sync_sl[MAX_MODELS];
double   g_slot_sync_tp[MAX_MODELS];
bool     g_slot_user_intervened[MAX_MODELS];

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
int      g_live_feed_timer_ms = 0;
string   g_pending_decision = "";
bool     g_paper_open = false;
int      g_paper_held = 0;
ulong    g_paper_ticket = 700000;
int      g_last_hist_spread_pts = 0;  // last non-zero MqlRates.spread (avoid weekend tick)

//+------------------------------------------------------------------+
string BridgePath(const string name)
{
   return InpBridgeSubdir + "\\" + name;
}

// Forward decls — roster loader uses JSON helpers defined below
string JsonGetString(const string json, const string key);
double JsonGetDouble(const string json, const string key, const double def = 0);
int    ParseExitMode(const string json);
void RefreshChartComment(const bool force = false);
void WriteEaSyncJson();
void PublishBarSyncBegin(const string bar_want);
void PublishBarSyncModel(const int slot, const string status, const string action, const string detail);
void PublishBarSyncEnd(const bool do_print);
bool DecisionMatchesBar(const string json, const string want_bar_time);
bool TryReadDecisionForBar(const string want_bar_time, const string model_id, string &json_out);
bool ApplyLiveDecisionSlot(const int slot, const string json, bool &any_open);
void TryRecoverLateDecisions();
void WaitHistoryDecisionsForBar(const string want);

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
   g_model_risk_pct[0] = 0;
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
   double bm = JsonGetDouble(json, "base_magic", 0);
   if(bm > 0)
      g_roster_base_magic = (ulong)bm;
   else
      g_roster_base_magic = (ulong)InpMagic;

   // Parse models array entries: look for "id" / "magic" / optional "risk_pct"
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
      // Per-model risk: scan this object until the next "id" (or end)
      int next_id = StringFind(json, "\"id\"", q2 + 1);
      int chunk_end = (next_id > idp ? next_id : StringLen(json));
      string chunk = StringSubstr(json, idp, chunk_end - idp);
      double model_rp = JsonGetDouble(chunk, "risk_pct", 0);
      if(model_rp <= 0)
         model_rp = g_roster_risk_pct;
      g_model_ids[n] = mid;
      g_model_magics[n] = magic;
      g_model_risk_pct[n] = model_rp;
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
   if(g_active_slot >= 0 && g_active_slot < MAX_MODELS)
   {
      g_slot_sync_sl[g_active_slot] = g_sync_sl;
      g_slot_sync_tp[g_active_slot] = g_sync_tp;
      g_slot_user_intervened[g_active_slot] = g_user_intervened;
   }
   if(slot < 0 || slot >= g_model_n)
   {
      g_active_magic = InpMagic;
      g_active_model_id = "";
      g_active_slot = -1;
      return;
   }
   g_active_magic = g_model_magics[slot];
   g_active_model_id = g_model_ids[slot];
   trade.SetExpertMagicNumber((int)g_active_magic);
   g_active_slot = slot;
   g_sync_sl = g_slot_sync_sl[slot];
   g_sync_tp = g_slot_sync_tp[slot];
   g_user_intervened = g_slot_user_intervened[slot];
}

double EffectiveRiskPct()
{
   // Prefer active model slot risk (BUG-01); then roster top-level; then input.
   int slot = FindModelSlotByMagic(g_active_magic);
   if(slot >= 0 && g_model_risk_pct[slot] > 0)
      return g_model_risk_pct[slot];
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
   g_active_slot = -1;
   ArrayInitialize(g_slot_paper_open, false);
   ArrayInitialize(g_slot_paper_held, 0);
   ArrayInitialize(g_slot_sync_sl, 0.0);
   ArrayInitialize(g_slot_sync_tp, 0.0);
   for(int i = 0; i < MAX_MODELS; i++)
   {
      g_slot_pending[i] = "";
      g_slot_user_intervened[i] = false;
   }

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
         Print("ForgeBridgeLC2G23 requires a hedging account.");
         return INIT_FAILED;
      }
      g_sim_ea_status = "idle";
      WriteSimControlFile();
      EventSetMillisecondTimer(50);
      Print("ForgeBridgeLC2G23 HistoryFeed | Files/", InpBridgeSubdir,
            " | paper=", UsePaperFills(), " | models=", g_model_n,
            " | base_magic=", InpMagic);
      g_sync_summary = "history feed idle";
      RefreshChartComment(true);
   }
   else
   {
      if(AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      {
         Print("ForgeBridgeLC2G23 requires a hedging account.");
         return INIT_FAILED;
      }
      WriteBarsJson();
      WriteConnectionJson();
      WritePositionsJson();
      EventSetMillisecondTimer((int)MathMax(500, InpHeartbeatMs));
      Print("ForgeBridgeLC2G23 Live | Files/", InpBridgeSubdir,
            " | models=", g_model_n, " | base_magic=", InpMagic,
            " | mt5_positions=", PositionsByMagic());
      g_sync_summary = "live ready | waiting first bar";
      RefreshChartComment(true);
   }

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(InpMode == BRIDGE_HISTORY_FEED)
   {
      // Reset may have wiped parquet; workers block on history_request.
      // Serve export chunks while pumping OOS bars — otherwise no decide/hits.
      ProcessHistoryRequest();
      ProcessHistoryFeed();
      return;
   }
   if(InpMode == BRIDGE_LIVE)
   {
      // Same Live EA / same bridge_live files: App writes sim_control.json to
      // pace OOS bars. Worker + Live desk must not see a second "sim mode".
      if(ReadSimControlFile() && g_sim_enabled)
      {
         if(g_live_feed_timer_ms != 50)
         {
            EventKillTimer();
            EventSetMillisecondTimer(50);
            g_live_feed_timer_ms = 50;
         }
         uint now_ms = GetTickCount();
         if(g_last_heartbeat_ms == 0 || now_ms - g_last_heartbeat_ms >= (uint)MathMax(500, InpHeartbeatMs))
         {
            WriteConnectionJson();
            g_last_heartbeat_ms = now_ms;
         }
         ProcessHistoryRequest();
         ProcessHistoryFeed();
         return;
      }
      if(g_live_feed_timer_ms == 50)
      {
         EventKillTimer();
         EventSetMillisecondTimer((int)MathMax(500, InpHeartbeatMs));
         g_live_feed_timer_ms = 0;
      }
      WriteConnectionJson();
      ProcessHistoryRequest();
      ProcessManualCommand();
      RefreshChartComment(false);
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
string ModelIdForMagic(const ulong magic)
{
   for(int s = 0; s < g_model_n; s++)
   {
      if(g_model_magics[s] == magic)
         return g_model_ids[s];
   }
   return "";
}

// Snapshot open MT5 positions for App journal reconcile (restart / desync safe).
bool WritePositionsJson()
{
   LoadModelsRoster();
   string json = "{";
   json += "\"updated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"server_time\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"" + PeriodTag() + "\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"bridge_subdir\":\"" + InpBridgeSubdir + "\",";
   json += "\"positions\":[";

   bool first = true;
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      ulong magic = (ulong)PositionGetInteger(POSITION_MAGIC);
      if(!MagicIsOurs(magic)) continue;

      string mid = ModelIdForMagic(magic);
      string typ = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      if(!first) json += ",";
      first = false;
      json += "{";
      json += "\"ticket\":" + IntegerToString((long)ticket) + ",";
      json += "\"magic\":" + IntegerToString((long)magic) + ",";
      if(mid != "")
         json += "\"model_id\":\"" + mid + "\",";
      json += "\"type\":\"" + typ + "\",";
      json += "\"volume\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + ",";
      json += "\"price_open\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), _Digits) + ",";
      json += "\"sl\":" + DoubleToString(PositionGetDouble(POSITION_SL), _Digits) + ",";
      json += "\"tp\":" + DoubleToString(PositionGetDouble(POSITION_TP), _Digits) + ",";
      json += "\"profit\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2) + ",";
      json += "\"time\":\"" + TimeToString((datetime)PositionGetInteger(POSITION_TIME), TIME_DATE | TIME_SECONDS) + "\"";
      json += "}";
      n++;
   }
   json += "],\"n\":" + IntegerToString(n) + "}\n";

   int h = FileOpen(BridgePath("positions.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return false;
   FileWriteString(h, json);
   FileClose(h);
   return true;
}

//+------------------------------------------------------------------+
bool MagicIsOurs(const ulong magic)
{
   if(magic == InpMagic)
      return true;
   for(int s = 0; s < g_model_n; s++)
      if(g_model_magics[s] == magic)
         return true;
   // BUG-10: disabled/orphan tickets still in Live magic block
   ulong base = (g_roster_base_magic > 0 ? g_roster_base_magic : (ulong)InpMagic);
   const int LIVE_MAGIC_SPAN = 15;
   if(magic >= base && magic < base + (ulong)LIVE_MAGIC_SPAN)
      return true;
   return false;
}

string DealReasonTag(const long reason)
{
   if(reason == DEAL_REASON_SL) return "sl";
   if(reason == DEAL_REASON_TP) return "tp";
   if(reason == DEAL_REASON_SO) return "stop_out";
   if(reason == DEAL_REASON_CLIENT || reason == DEAL_REASON_MOBILE || reason == DEAL_REASON_WEB)
      return "manual_close";
   if(reason == DEAL_REASON_EXPERT) return "ea_close";
   return "closed";
}

bool WriteDealsJson()
{
   // Source of truth for App journal: actual OUT deals from MT5 history.
   datetime from = TimeCurrent() - 7 * 24 * 3600;
   if(!HistorySelect(from, TimeCurrent()))
      return false;
   string json = "{";
   json += "\"updated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"" + PeriodTag() + "\",";
   json += "\"deals\":[";
   bool first = true;
   int n = 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0 && n < 80; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0) continue;
      if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) continue;
      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
      ulong magic = (ulong)HistoryDealGetInteger(deal, DEAL_MAGIC);
      if(!MagicIsOurs(magic)) continue;
      ulong pos_id = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
      double profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                    + HistoryDealGetDouble(deal, DEAL_SWAP)
                    + HistoryDealGetDouble(deal, DEAL_COMMISSION);
      long dtype = HistoryDealGetInteger(deal, DEAL_TYPE);
      string typ = (dtype == DEAL_TYPE_SELL) ? "SELL" : "BUY";
      if(!first) json += ",";
      first = false;
      json += "{";
      json += "\"deal\":" + IntegerToString((long)deal) + ",";
      json += "\"position_id\":" + IntegerToString((long)pos_id) + ",";
      json += "\"ticket\":" + IntegerToString((long)pos_id) + ",";
      json += "\"magic\":" + IntegerToString((long)magic) + ",";
      json += "\"model_id\":\"" + ModelIdForMagic(magic) + "\",";
      json += "\"type\":\"" + typ + "\",";
      json += "\"volume\":" + DoubleToString(HistoryDealGetDouble(deal, DEAL_VOLUME), 2) + ",";
      json += "\"price\":" + DoubleToString(HistoryDealGetDouble(deal, DEAL_PRICE), _Digits) + ",";
      json += "\"profit\":" + DoubleToString(profit, 2) + ",";
      json += "\"profit_raw\":" + DoubleToString(HistoryDealGetDouble(deal, DEAL_PROFIT), 2) + ",";
      json += "\"swap\":" + DoubleToString(HistoryDealGetDouble(deal, DEAL_SWAP), 2) + ",";
      json += "\"commission\":" + DoubleToString(HistoryDealGetDouble(deal, DEAL_COMMISSION), 2) + ",";
      json += "\"reason\":\"" + DealReasonTag(HistoryDealGetInteger(deal, DEAL_REASON)) + "\",";
      json += "\"time\":\"" + TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE | TIME_SECONDS) + "\"";
      json += "}";
      n++;
   }
   json += "],\"n\":" + IntegerToString(n) + "}\n";
   int dh = FileOpen(BridgePath("deals.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(dh == INVALID_HANDLE)
      return false;
   FileWriteString(dh, json);
   FileClose(dh);
   return true;
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
   string pat = "\"" + key + "\":";
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
   string pat = "\"" + key + "\":";
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

int ParseExitMode(const string json)
{
   // Exact "exit_mode": — do not match mining key exit_modes_full_only.
   string em = JsonGetString(json, "exit_mode");
   StringToLower(em);
   if(em == "full" || em == "0") return 0;
   if(em == "hybrid" || em == "1") return 1;
   if(em == "trail" || em == "2") return 2;
   if(em == "partial" || em == "3") return 3;
   double n = JsonGetDouble(json, "exit_mode", -1);
   if(n >= 0.0 && n <= 3.0)
      return (int)n;
   return 0;
}

bool JsonGetBool(const string json, const string key, const bool def = false)
{
   string pat = "\"" + key + "\":";
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
   if(CopyRates(_Symbol, Period(), 1, 1, r) < 1)
      return false;

   long time_msc = (long)r[0].time * 1000;
   string bar_time = TimeToString(r[0].time, TIME_DATE | TIME_MINUTES);
   // MT5 TimeToString uses yyyy.mm.dd hh:mi — matches App
   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   long login = AccountInfoInteger(ACCOUNT_LOGIN);

   string json = "{";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"" + PeriodTag() + "\",";
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
   json += "\"period\":\"" + PeriodTag() + "\",";
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
   int copied = CopyRates(_Symbol, Period(), 0, requested, rates);
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
   prefix += "\"period\":\"" + PeriodTag() + "\",\"bars\":[";
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
   prefix += "\"period\":\"" + PeriodTag() + "\",\"source\":\"history_feed\",\"bars\":[";
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
   int total = Bars(_Symbol, Period());
   string from_time_text = JsonGetString(request, "from_time");
   datetime from_time = StringToTime(from_time_text == "" ? "2023.01.01 00:00" : from_time_text);
   int oldest_shift = iBarShift(_Symbol, Period(), from_time, false);
   // iBarShift returns -1 when from_time is outside loaded history; treat as "all bars".
   if(oldest_shift < 0)
      oldest_shift = MathMax(0, total - 1);
   int available = MathMax(0, MathMin(total - 1, oldest_shift)); // exclude forming bar
   int wanted = MathMin(chunk_size, MathMax(0, available - offset));

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = 0;
   if(wanted > 0)
      copied = CopyRates(_Symbol, Period(), offset + 1, wanted, rates);
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
   prefix += "\"symbol\":\"" + _Symbol + "\",\"period\":\"" + PeriodTag() + "\",";
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
   if(CopyRates(_Symbol, Period(), 0, 1, current) < 1)
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
   json += "\"period\":\"" + PeriodTag() + "\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"ea_version\":\"1.28\",";
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
   WritePositionsJson();
   WriteDealsJson();
   return true;
}

void HeartbeatIfDue()
{
   // Sleep() in decision-wait blocks OnTimer/OnTick; keep connection.json fresh
   // so the App "EA ONLINE" chip does not flip OFFLINE for up to 120s.
   uint now_ms = GetTickCount();
   if(g_last_heartbeat_ms == 0 || now_ms - g_last_heartbeat_ms >= (uint)MathMax(500, InpHeartbeatMs))
   {
      WriteConnectionJson();
      g_last_heartbeat_ms = now_ms;
   }
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
   // BUG-02: close roster magics + full Live magic span on this symbol so
   // disabled/orphan tickets (magic reserved but dropped from models.json) flatten.
   ulong base = (g_roster_base_magic > 0 ? g_roster_base_magic : (ulong)InpMagic);
   const int LIVE_MAGIC_SPAN = 15; // match shared.constants.LIVE_MAX_MODELS

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      ulong want = (ulong)PositionGetInteger(POSITION_MAGIC);
      bool ours = (want == (ulong)InpMagic);
      if(!ours && want >= base && want < base + (ulong)LIVE_MAGIC_SPAN)
         ours = true;
      if(!ours)
      {
         for(int s = 0; s < g_model_n; s++)
            if(g_model_magics[s] == want) { ours = true; break; }
      }
      if(!ours) continue;
      int slot_close = FindModelSlotByMagic(want);
      if(slot_close >= 0)
         SetActiveSlot(slot_close);
      else
      {
         // Orphan magic (disabled model) — keep real magic on fill, not InpMagic
         g_active_magic = want;
         g_active_model_id = "";
         trade.SetExpertMagicNumber((int)want);
      }
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
      HeartbeatIfDue();
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

bool DecisionMatchesBar(const string json, const string want_bar_time)
{
   string bt = JsonGetString(json, "bar_time");
   if(bt == "")
      bt = JsonGetString(json, "time");
   return (bt != "" && bt == want_bar_time);
}

bool TryReadDecisionForBar(const string want_bar_time, const string model_id, string &json_out)
{
   bool ok = (model_id != "")
      ? ReadDecisionJsonForModel(model_id, json_out)
      : ReadDecisionJson(json_out);
   if(!ok)
      return false;
   return DecisionMatchesBar(json_out, want_bar_time);
}

bool ApplyLiveDecisionSlot(const int slot, const string json, bool &any_open)
{
   if(slot < 0 || slot >= g_model_n)
      return false;
   string action = JsonGetString(json, "action");
   StringToUpper(action);
   if(action == "FLAT" || action == "HOLD" || action == "")
   {
      PublishBarSyncModel(slot, "OK", (action == "" ? "FLAT" : action), "");
      return true;
   }
   SetActiveSlot(slot);
   if(OpenFromDecision(json))
   {
      any_open = true;
      PublishBarSyncModel(slot, "ENTERED", action, "");
      return true;
   }
   PublishBarSyncModel(slot, "FAIL", action, "OrderSend");
   return true;
}

void TryRecoverLateDecisions()
{
   if(!g_late_pending || g_sync_bar == "" || g_model_n <= 0)
      return;
   bool any_open = false;
   bool changed = false;
   int still_to = 0;
   for(int s = 0; s < g_model_n; s++)
   {
      if(g_sync_status[s] != "TIMEOUT")
         continue;
      if(PositionsByMagic(g_model_magics[s]) > 0)
      {
         PublishBarSyncModel(s, "OPEN", "-", "late");
         changed = true;
         continue;
      }
      string json;
      if(!TryReadDecisionForBar(g_sync_bar, g_model_ids[s], json))
      {
         still_to++;
         continue;
      }
      string action = JsonGetString(json, "action");
      StringToUpper(action);
      if(action == "FLAT" || action == "HOLD" || action == "")
      {
         PublishBarSyncModel(s, "OK", (action == "" ? "FLAT" : action), "late");
      }
      else
      {
         SetActiveSlot(s);
         if(OpenFromDecision(json))
         {
            any_open = true;
            PublishBarSyncModel(s, "ENTERED", action, "late");
         }
         else
            PublishBarSyncModel(s, "FAIL", action, "OrderSend");
      }
      changed = true;
   }
   if(any_open && g_pending_bar_dt > 0)
      g_last_fill_bar = g_pending_bar_dt;
   if(changed)
      PublishBarSyncEnd(false);
   if(still_to <= 0)
   {
      g_late_pending = false;
      g_pending_bar_dt = 0;
   }
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
   json += "\"period\":\"" + PeriodTag() + "\",";
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
bool LookupCloseDeal(const ulong pos_ticket, const ulong magic,
                     double &profit, double &exit_px, string &reason)
{
   datetime from = TimeCurrent() - 7 * 24 * 3600;
   if(!HistorySelect(from, TimeCurrent()))
      return false;
   ulong want_magic = (magic > 0 ? magic : InpMagic);
   for(int pass = 0; pass < 2; pass++)
   {
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
      {
         ulong deal = HistoryDealGetTicket(i);
         if(deal == 0) continue;
         if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) continue;
         long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
         if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
         if(pass == 0)
         {
            if(pos_ticket == 0)
               break;
            if((ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID) != pos_ticket)
               continue;
         }
         else if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != want_magic)
            continue;
         profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                + HistoryDealGetDouble(deal, DEAL_SWAP)
                + HistoryDealGetDouble(deal, DEAL_COMMISSION);
         exit_px = HistoryDealGetDouble(deal, DEAL_PRICE);
         long dr = HistoryDealGetInteger(deal, DEAL_REASON);
         if(dr == DEAL_REASON_SL) reason = "sl";
         else if(dr == DEAL_REASON_TP) reason = "tp";
         else if(dr == DEAL_REASON_SO) reason = "stop_out";
         else if(dr == DEAL_REASON_CLIENT || dr == DEAL_REASON_MOBILE || dr == DEAL_REASON_WEB)
            reason = "manual_close";
         else if(dr == DEAL_REASON_EXPERT) reason = "ea_close";
         else if(reason == "" || reason == "closed")
            reason = "closed";
         return true;
      }
   }
   return false;
}

string DetectCloseReasonFromHistory()
{
   double profit = 0;
   double exit_px = 0;
   string reason = "closed";
   if(LookupCloseDeal(g_open_ticket, g_active_magic, profit, exit_px, reason))
      return reason;
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
   // Restart / other-slot close zeros the global baseline — seed, do not tag user edit.
   if(g_sync_sl == 0.0 && g_sync_tp == 0.0)
   {
      g_sync_sl = cur_sl;
      g_sync_tp = cur_tp;
      g_open_sl = cur_sl;
      g_open_tp = cur_tp;
      if(g_active_slot >= 0 && g_active_slot < MAX_MODELS)
      {
         g_slot_sync_sl[g_active_slot] = cur_sl;
         g_slot_sync_tp[g_active_slot] = cur_tp;
      }
      return;
   }
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
      if(g_active_slot >= 0 && g_active_slot < MAX_MODELS)
      {
         g_slot_sync_sl[g_active_slot] = g_sync_sl;
         g_slot_sync_tp[g_active_slot] = g_sync_tp;
      }
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
   if(g_active_slot >= 0 && g_active_slot < MAX_MODELS)
   {
      g_slot_sync_sl[g_active_slot] = g_sync_sl;
      g_slot_sync_tp[g_active_slot] = g_sync_tp;
      g_slot_user_intervened[g_active_slot] = true;
   }
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

   g_exit_mode = ParseExitMode(json);
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
      int save_slot = (slot >= 0) ? slot : FindModelSlotByMagic(g_active_magic);
      if(save_slot >= 0 && save_slot < MAX_MODELS)
      {
         g_slot_ticket[save_slot] = ticket;
         g_slot_sid[save_slot] = sid;
         g_slot_action[save_slot] = action;
         g_slot_entry[save_slot] = price;
         g_slot_sl[save_slot] = sl;
         g_slot_sl_init[save_slot] = sl;
         g_slot_lots[save_slot] = lots;
         g_slot_sync_sl[save_slot] = sl;
         g_slot_sync_tp[save_slot] = tp;
         g_slot_user_intervened[save_slot] = g_user_intervened;
         // BUG-11: per-slot exit/trail/risk so ManageOpen does not use last-open globals
         g_slot_risk[save_slot] = g_risk;
         g_slot_exit_mode[save_slot] = g_exit_mode;
         g_slot_trail_act[save_slot] = g_trail_act;
         g_slot_trail_dist[save_slot] = g_trail_dist;
         g_slot_max_hold[save_slot] = g_max_hold;
      }
      Print("ForgeBridge ENTERED app_signal sid=", sid,
            " model=", g_active_model_id,
            " magic=", g_active_magic,
            " ticket=", ticket,
            " ", action,
            " lots=", lots,
            " entry=", price,
            " sl=", sl,
            " tp=", tp,
            " source=", g_open_source);
      WritePositionsJson();
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
   // Prefer THIS position's deal — never the latest OUT for InpMagic (multi-model).
   double profit = 0;
   double exit_px = (g_open_action == "BUY")
      ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
      : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   string close_reason = reason;
   string hist_reason = close_reason;
   ulong mag = (g_active_magic > 0 ? g_active_magic : InpMagic);
   if(LookupCloseDeal(g_open_ticket, mag, profit, exit_px, hist_reason))
   {
      if(close_reason == "" || close_reason == "closed")
         close_reason = hist_reason;
   }
   else if(close_reason == "" || close_reason == "closed")
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
   if(g_active_slot >= 0 && g_active_slot < MAX_MODELS)
   {
      g_slot_sync_sl[g_active_slot] = 0;
      g_slot_sync_tp[g_active_slot] = 0;
      g_slot_user_intervened[g_active_slot] = false;
   }
   g_had_position = false;
   WritePositionsJson();
   WriteDealsJson();
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
         if(g_slot_ticket[s] != 0)
         {
            g_open_ticket = g_slot_ticket[s];
            if(g_slot_sid[s] != "")
               g_open_signal_id = g_slot_sid[s];
            if(g_slot_action[s] != "")
               g_open_action = g_slot_action[s];
            if(g_slot_entry[s] > 0)
               g_open_entry = g_slot_entry[s];
            if(g_slot_sl[s] > 0)
               g_open_sl = g_slot_sl[s];
            if(g_slot_lots[s] > 0)
               g_open_lots = g_slot_lots[s];
         }
         ReportCloseIfNeeded("closed");
         g_slot_ticket[s] = 0;
         g_slot_sid[s] = "";
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
      // Always restore this model's exit params. Gating on max_hold lost
      // full-TP genomes after reconnect (slot max_hold=0 → hybrid trail).
      g_exit_mode = g_slot_exit_mode[s];
      if(g_slot_max_hold[s] > 0)
         g_max_hold = g_slot_max_hold[s];
      if(g_slot_trail_act[s] > 0)
         g_trail_act = g_slot_trail_act[s];
      if(g_slot_trail_dist[s] > 0)
         g_trail_dist = g_slot_trail_dist[s];
      if(g_slot_risk[s] > 0)
         g_risk = g_slot_risk[s];
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
         g_slot_ticket[s] = ticket;
         g_slot_action[s] = g_open_action;
         g_slot_entry[s] = g_open_entry;
         g_slot_lots[s] = g_open_lots;

         // Keep App SL/TP in sync (user edits → mode manual)
         SyncPositionLevels(ticket);

         datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
         int held = (int)((TimeCurrent() - open_time) / PeriodSeconds(Period()));
         if(g_max_hold > 0 && held >= g_max_hold)
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
   if(CopyRates(_Symbol, Period(), 0, bars, rates) < bars)
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
      t_to += PeriodSeconds(Period()) * 96 - 1;

   ArrayFree(g_hist_rates);
   ArraySetAsSeries(g_hist_rates, false);
   int copied = CopyRates(_Symbol, Period(), t_from, t_to, g_hist_rates);
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
   g_last_hist_spread_pts = 0;
   // Multi-model: wipe ALL slot paper/pending — otherwise a Stop mid-trade leaves
   // g_slot_paper_open[] true while journal was cleared, or vice versa.
   ArrayInitialize(g_slot_paper_open, false);
   ArrayInitialize(g_slot_paper_held, 0);
   for(int i = 0; i < MAX_MODELS; i++)
   {
      g_slot_pending[i] = "";
      g_slot_ticket[i] = 0;
      g_slot_sid[i] = "";
   }
   Print("ForgeBridgeLC2G23 HistoryFeed loaded bars=", g_hist_n,
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

double HistSpreadPrice(const MqlRates &r)
{
   // OHLC from CopyRates is Bid. Live fills BUY at Ask / SELL at Bid.
   // Prefer the bar's stored spread — never weekend SYMBOL_SPREAD during Replay.
   int pts = (int)r.spread;
   if(pts > 0)
      g_last_hist_spread_pts = pts;
   else if(g_last_hist_spread_pts > 0)
      pts = g_last_hist_spread_pts;
   else
      pts = 10; // 1.0 pip on 3/5-digit
   return pts * _Point;
}

void ManagePaperHistory(const MqlRates &r)
{
   if(!g_paper_open)
      return;
   g_paper_held++;

   const double spr = HistSpreadPrice(r);
   const double bid_h = r.high;
   const double bid_l = r.low;
   const double bid_c = r.close;
   const double ask_h = r.high + spr;
   const double ask_l = r.low + spr;
   const double ask_c = r.close + spr;

   // Live trail: BUY from Bid, SELL from Ask
   if(g_exit_mode == 1 || g_exit_mode == 2)
   {
      if(g_open_action == "BUY")
      {
         if(bid_h >= g_open_entry + g_risk * g_trail_act)
         {
            double nsl = bid_h - g_risk * g_trail_dist;
            if(nsl > g_open_sl)
               g_open_sl = nsl;
         }
      }
      else
      {
         if(ask_l <= g_open_entry - g_risk * g_trail_act)
         {
            double nsl = ask_l + g_risk * g_trail_dist;
            if(g_open_sl == 0 || nsl < g_open_sl)
               g_open_sl = nsl;
         }
      }
   }

   const bool trail_moved = (g_open_sl_initial > 0.0
                             && MathAbs(g_open_sl - g_open_sl_initial) > (_Point * 0.5));

   if(g_open_action == "BUY")
   {
      if(g_open_sl > 0 && bid_l <= g_open_sl)
      {
         ReportPaperClose(trail_moved ? "trail" : "sl", g_open_sl,
                          TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
      if(g_open_tp > 0 && bid_h >= g_open_tp)
      {
         ReportPaperClose("tp", g_open_tp, TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
   }
   else
   {
      if(g_open_sl > 0 && ask_h >= g_open_sl)
      {
         ReportPaperClose(trail_moved ? "trail" : "sl", g_open_sl,
                          TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
      if(g_open_tp > 0 && ask_l <= g_open_tp)
      {
         ReportPaperClose("tp", g_open_tp, TimeToString(r.time, TIME_DATE | TIME_MINUTES));
         return;
      }
   }

   // held includes entry bar; Python uses (i - entry_idx) >= max_hold
   // max_hold<=0 means unlimited (full TP) — never treat 0 as "close next bar"
   if(g_max_hold > 0 && g_paper_held - 1 >= g_max_hold)
      ReportPaperClose("max_hold",
                       (g_open_action == "BUY") ? bid_c : ask_c,
                       TimeToString(r.time, TIME_DATE | TIME_MINUTES));
}

bool PaperOpenFromDecision(const string json, const MqlRates &r, const string bar_time = "")
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
   // Same as live OrderSend: BUY at Ask, SELL at Bid (OHLC is Bid).
   const double spr = HistSpreadPrice(r);
   const double entry_price = (action == "BUY") ? (r.open + spr) : r.open;
   if(sl <= 0 || tp <= 0 || entry_price <= 0)
      return false;

   g_exit_mode = ParseExitMode(json);
   g_trail_act = JsonGetDouble(json, "trail_activate_r", 1.0);
   g_trail_dist = JsonGetDouble(json, "trail_distance_r", 0.5);
   g_max_hold = (int)JsonGetDouble(json, "max_hold_bars", InpMaxHoldBars);

   // Rebase SL/TP onto Bid/Ask fill using planned risk/RR from App decision.
   // Decision levels are vs lab spread-adjusted entry; live also rebases onto
   // current Ask/Bid so lot size and R stay as intended.
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
   Print("ForgeBridgeLC2G23 HistoryFeed paper ", action, " @", entry_price,
         " sl=", sl, " tp=", tp, " risk=", sl_dist,
         " spread=", spr, " sid=", sid, " bar=", bt);
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
      if(UsePaperFills())
      {
         if(g_slot_paper_open[s])
            continue;
      }
      else if(PositionsByMagic(g_model_magics[s]) > 0)
         continue;
      SetActiveSlot(s);
      bool ok = false;
      if(UsePaperFills())
         ok = PaperOpenFromDecision(g_slot_pending[s], r, bt);
      else
         ok = OpenFromDecision(g_slot_pending[s]);
      if(ok && UsePaperFills())
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

void WaitHistoryDecisionsForBar(const string want)
{
   // Live polls every flat model in parallel until each has a bar-matched
   // decision. Sequential wait with delay_ms+6000 starved models 2–5 →
   // missed entries and different fills every Replay run.
   LoadModelsRoster();
   bool pending[MAX_MODELS];
   int n_pending = 0;
   for(int s = 0; s < g_model_n; s++)
   {
      pending[s] = false;
      bool flat = UsePaperFills()
         ? (!g_slot_paper_open[s])
         : (PositionsByMagic(g_model_magics[s]) == 0);
      if(!flat || g_slot_pending[s] != "")
      {
         PublishBarSyncModel(s, "OPEN", "-", "skip");
         continue;
      }
      pending[s] = true;
      n_pending++;
   }

   int wait_ms = (int)MathMax(InpHistoryDecisionWaitMs, 30000 * MathMax(1, g_model_n));
   wait_ms = (int)MathMin(wait_ms, 120000);
   uint deadline = GetTickCount() + (uint)wait_ms;
   int poll = (int)MathMax(20, MathMin(50, InpPollMs));

   while(n_pending > 0 && GetTickCount() < deadline)
   {
      HeartbeatIfDue();
      for(int s = 0; s < g_model_n; s++)
      {
         if(!pending[s])
            continue;
         string json;
         if(!TryReadDecisionForBar(want, g_model_ids[s], json))
            continue;
         string action = JsonGetString(json, "action");
         StringToUpper(action);
         if(action == "BUY" || action == "SELL")
         {
            g_slot_pending[s] = json;
            PublishBarSyncModel(s, "OK", action, "pending");
         }
         else
            PublishBarSyncModel(s, "OK", (action == "" ? "FLAT" : action), "");
         pending[s] = false;
         n_pending--;
      }
      if(n_pending > 0)
         Sleep(poll);
   }

   for(int s = 0; s < g_model_n; s++)
   {
      if(!pending[s])
         continue;
      PublishBarSyncModel(s, "TIMEOUT", "-", IntegerToString(wait_ms) + "ms");
      Print("ForgeBridgeLC2G23 HistoryFeed: no decision for ", want,
            " model=", g_model_ids[s],
            " (waited ", wait_ms, "ms)");
   }
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
      // Live leaves positions open at Friday close. Force-close at last Bid
      // ("end_range") invented R (incl. ~-2R after worker weekend reconcile).
      int n_open = 0;
      for(int s = 0; s < g_model_n; s++)
         if(g_slot_paper_open[s])
            n_open++;
      if(!UsePaperFills() && g_had_position && PositionsByMagic() > 0)
         CloseAllByMagic("end_range");
      g_sim_ea_status = "completed";
      g_sim_enabled = false;
      WriteSimControlFile();
      Print("ForgeBridgeLC2G23 HistoryFeed completed bars=", g_hist_n,
            " paper_open=", n_open, " (left open like Live)");
      return;
   }

   MqlRates r = g_hist_rates[g_hist_cursor];

   // Open pending from previous bar decision at this bar's open
   ApplyPendingOpen(r);

   if(UsePaperFills())
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
   PublishBarSyncBegin(want);
   WaitHistoryDecisionsForBar(want);
   PublishBarSyncEnd(true);

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
string ModeTag()
{
   if(InpMode == BRIDGE_HISTORY_FEED) return "HISTORY_FEED";
   if(InpMode == BRIDGE_REPLAY) return "REPLAY";
   return "LIVE";
}

string ShortModelId(const string mid)
{
   int n = StringLen(mid);
   if(n <= 20) return mid;
   return StringSubstr(mid, 0, 12) + ".." + StringSubstr(mid, n - 6, 6);
}

string JsonEscapeLocal(const string s)
{
   string o = s;
   StringReplace(o, "\\", "\\\\");
   StringReplace(o, "\"", "\\\"");
   return o;
}

void RefreshChartComment(const bool force = false)
{
   if(!InpShowComment)
   {
      Comment("");
      return;
   }
   uint now_ms = GetTickCount();
   if(!force && g_last_comment_ms != 0 && now_ms - g_last_comment_ms < 400)
      return;
   g_last_comment_ms = now_ms;

   string txt = "ForgeBridgeLC2G23 " + ModeTag() + "\n";
   txt += _Symbol + " " + PeriodTag() + " | " + InpBridgeSubdir + "\n";
   txt += "models=" + IntegerToString(MathMax(g_model_n, 0))
      + " magic_base=" + IntegerToString((long)InpMagic) + "\n";
   if(g_sync_bar != "")
      txt += "bar " + g_sync_bar + "\n";
   txt += g_sync_summary + "\n";
   for(int i = 0; i < g_sync_n; i++)
      txt += g_sync_line[i] + "\n";
   Comment(txt);
}

void WriteEaSyncJson()
{
   // App Pipeline health reads this to confirm EA↔decision handshake.
   string json = "{";
   json += "\"updated_at\":\"" + TimeToString(TimeLocal(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"server_time\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"period\":\"" + PeriodTag() + "\",";
   json += "\"instance_id\":\"" + INSTANCE_ID + "\",";
   json += "\"bridge_subdir\":\"" + JsonEscapeLocal(InpBridgeSubdir) + "\",";
   json += "\"mode\":\"" + ModeTag() + "\",";
   json += "\"bar_time\":\"" + JsonEscapeLocal(g_sync_bar) + "\",";
   json += "\"summary\":\"" + JsonEscapeLocal(g_sync_summary) + "\",";
   json += "\"model_n\":" + IntegerToString(g_sync_n) + ",";
   json += "\"models\":[";
   for(int i = 0; i < g_sync_n; i++)
   {
      if(i > 0) json += ",";
      string mid = (i < g_model_n ? g_model_ids[i] : "");
      ulong mag = (i < g_model_n ? g_model_magics[i] : InpMagic);
      json += "{";
      json += "\"id\":\"" + JsonEscapeLocal(mid) + "\",";
      json += "\"magic\":" + IntegerToString((long)mag) + ",";
      json += "\"status\":\"" + JsonEscapeLocal(g_sync_status[i]) + "\",";
      json += "\"action\":\"" + JsonEscapeLocal(g_sync_action[i]) + "\"";
      json += "}";
   }
   json += "]}\n";

   int h = FileOpen(BridgePath("ea_sync.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, json);
   FileClose(h);
}

void PublishBarSyncBegin(const string bar_want)
{
   g_sync_bar = bar_want;
   g_sync_n = 0;
   g_sync_summary = "waiting App decision...";
   for(int i = 0; i < MAX_MODELS; i++)
   {
      g_sync_line[i] = "";
      g_sync_status[i] = "";
      g_sync_action[i] = "";
   }
   RefreshChartComment(true);
}

void PublishBarSyncModel(const int slot, const string status, const string action, const string detail)
{
   if(slot < 0 || slot >= MAX_MODELS)
      return;
   if(slot >= g_sync_n)
      g_sync_n = slot + 1;
   string mid = (slot < g_model_n ? g_model_ids[slot] : "");
   ulong mag = (slot < g_model_n ? g_model_magics[slot] : InpMagic);
   string act = action;
   if(act == "")
      act = "-";
   g_sync_status[slot] = status;
   g_sync_action[slot] = act;
   g_sync_line[slot] = ShortModelId(mid) + " #" + IntegerToString((long)mag)
      + " " + status + " " + act
      + (detail != "" ? (" " + detail) : "");
}

void PublishBarSyncEnd(const bool do_print)
{
   int n_ok = 0, n_to = 0, n_sig = 0, n_open = 0;
   for(int i = 0; i < g_sync_n; i++)
   {
      string st = g_sync_status[i];
      if(st == "TIMEOUT") n_to++;
      else if(st == "OPEN") n_open++;
      else if(st == "BUY" || st == "SELL" || st == "ENTERED") n_sig++;
      else n_ok++;
   }
   if(n_to > 0)
   {
      g_sync_summary = "TIMEOUT " + IntegerToString(n_to) + "/" + IntegerToString(g_sync_n)
         + " | App slow / worker down?";
      g_late_pending = true;
   }
   else
   {
      g_late_pending = false;
      g_pending_bar_dt = 0;
      // If any model line carries "late", surface catch-up (not a fresh miss).
      bool any_late = false;
      for(int i = 0; i < g_sync_n; i++)
      {
         if(StringFind(g_sync_line[i], " late") >= 0)
         {
            any_late = true;
            break;
         }
      }
      if(any_late)
         g_sync_summary = "SYNC OK | late catch-up";
      else if(n_sig > 0)
         g_sync_summary = "SYNC OK | entries " + IntegerToString(n_sig);
      else
         g_sync_summary = "SYNC OK | flat/hold";
   }

   WriteEaSyncJson();
   RefreshChartComment(true);
   if(do_print)
   {
      Print("ForgeBridge bar ", g_sync_bar, " | ", g_sync_summary,
            " | models=", g_sync_n, " | ", InpBridgeSubdir);
      for(int i = 0; i < g_sync_n; i++)
         Print("  ", g_sync_line[i]);
   }
}

//+------------------------------------------------------------------+
void OnTick()
{
   // History feed is timer-driven; do not trade live ticks in parallel
   if(InpMode == BRIDGE_HISTORY_FEED)
      return;
   if(InpMode == BRIDGE_LIVE && ReadSimControlFile() && g_sim_enabled)
      return;

   LoadModelsRoster();
   ManageOpen();

   uint now_ms = GetTickCount();
   if(g_last_heartbeat_ms == 0 || now_ms - g_last_heartbeat_ms >= (uint)MathMax(500, InpHeartbeatMs))
   {
      WriteConnectionJson();
      g_last_heartbeat_ms = now_ms;
      RefreshChartComment(false);
   }

   ProcessManualCommand();
   TryRecoverLateDecisions();

   datetime t0 = iTime(_Symbol, Period(), 0);
   if(t0 == 0 || t0 == g_last_bar)
      return;
   g_last_bar = t0;
   WriteBarsJson();

   datetime t1 = iTime(_Symbol, Period(), 1);
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

   // Live: publish closed bar, wait in PARALLEL for all model decisions.
   // Sequential wait drained the shared budget on model #0 and caused TIMEOUT 2/3–3/3.
   if(!WriteBarJson(t1))
      return;

   string want = TimeToString(t1, TIME_DATE | TIME_MINUTES);
   PublishBarSyncBegin(want);
   g_pending_bar_dt = t1;
   g_late_pending = false;

   bool pending[MAX_MODELS];
   int n_pending = 0;
   for(int s = 0; s < g_model_n; s++)
   {
      pending[s] = false;
      if(PositionsByMagic(g_model_magics[s]) > 0)
      {
         PublishBarSyncModel(s, "OPEN", "-", "skip");
         continue;
      }
      pending[s] = true;
      n_pending++;
   }

   // Budget scales with model count; hard cap 120s (week-boundary remine can lag).
   int live_wait = (int)MathMax(InpDecisionWaitMs, 30000 * MathMax(1, g_model_n));
   live_wait = (int)MathMin(live_wait, 120000);
   uint deadline = GetTickCount() + (uint)live_wait;
   int poll = (int)MathMax(50, InpPollMs);
   bool any_open = false;

   while(n_pending > 0 && GetTickCount() < deadline)
   {
      HeartbeatIfDue();
      for(int s = 0; s < g_model_n; s++)
      {
         if(!pending[s])
            continue;
         string json;
         if(!TryReadDecisionForBar(want, g_model_ids[s], json))
            continue;
         ApplyLiveDecisionSlot(s, json, any_open);
         pending[s] = false;
         n_pending--;
      }
      if(n_pending > 0)
         Sleep(poll);
   }

   for(int s = 0; s < g_model_n; s++)
   {
      if(!pending[s])
         continue;
      PublishBarSyncModel(s, "TIMEOUT", "-", IntegerToString(live_wait) + "ms");
   }
   PublishBarSyncEnd(true);
   if(any_open)
      g_last_fill_bar = t1;
}
//+------------------------------------------------------------------+
