//+------------------------------------------------------------------+
//| ForgeBridge.mq5                                                  |
//| Thin execution EA — App (Best 3m) decides via mt5/bridge files.  |
//| Modes:                                                           |
//|   Live   — write bar.json, read decision.json (App service)      |
//|   Replay — read replay_signals.csv for Strategy Tester compare   |
//| Keep ForgeBest3m_Frozen / ForgeBest3m_WF for MT5 side-by-side.   |
//+------------------------------------------------------------------+
#property copyright "EdgeMiner2 bridge"
#property version   "1.02"

#include <Trade/Trade.mqh>

enum ENUM_BRIDGE_MODE
{
   BRIDGE_LIVE = 0,    // Live file bridge
   BRIDGE_REPLAY = 1   // Replay CSV (tester)
};

input group "=== Bridge ==="
input ENUM_BRIDGE_MODE InpMode = BRIDGE_LIVE;
input string InpBridgeSubdir   = "bridge";          // under MQL5/Files/
input int    InpDecisionWaitMs = 8000;              // Live: wait for decision
input int    InpPollMs         = 500;
input int    InpChartBars      = 1344;              // M15 bars exported for App chart
input int    InpHeartbeatMs    = 2000;              // Live connection/tick snapshot
input int    InpHistoryChunk   = 750;               // Bars per history sync response

input group "=== Risk ==="
input double InpRiskPct        = 1.0;
input ulong  InpMagic          = 20260724;
input int    InpSlipPoints     = 30;
input int    InpMaxHoldBars    = 36;                // fallback if decision omits

CTrade   trade;
datetime g_last_bar = 0;
datetime g_last_fill_bar = 0;
string   g_last_signal_id = "";
ulong    g_open_ticket = 0;
string   g_open_signal_id = "";
string   g_open_action = "";
double   g_open_entry = 0;
double   g_open_sl = 0;
double   g_open_tp = 0;
double   g_open_lots = 0;
double   g_risk = 0;
int      g_exit_mode = 1;
double   g_trail_act = 1.0;
double   g_trail_dist = 0.5;
int      g_max_hold = 36;
bool     g_had_position = false;
uint     g_last_heartbeat_ms = 0;
string   g_last_history_request = "";

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

//+------------------------------------------------------------------+
string BridgePath(const string name)
{
   return InpBridgeSubdir + "\\" + name;
}

//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber((int)InpMagic);
   trade.SetDeviationInPoints(InpSlipPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   g_max_hold = InpMaxHoldBars;

   FolderCreate(InpBridgeSubdir);

   if(InpMode == BRIDGE_REPLAY)
   {
      if(!LoadReplayCsv())
      {
         Print("ForgeBridge Replay: failed to load ", BridgePath("replay_signals.csv"));
         return INIT_FAILED;
      }
      Print("ForgeBridge Replay loaded signals=", g_rep_n);
   }
   else
   {
      WriteBarsJson();
      WriteConnectionJson();
      EventSetMillisecondTimer((int)MathMax(500, InpHeartbeatMs));
      Print("ForgeBridge Live | Files/", InpBridgeSubdir, " | magic=", InpMagic);
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
   if(InpMode == BRIDGE_LIVE)
   {
      WriteConnectionJson();
      ProcessHistoryRequest();
   }
}

//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
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
   datetime from_time = StringToTime(from_time_text == "" ? "2025.01.01 00:00" : from_time_text);
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

//+------------------------------------------------------------------+
bool WaitDecisionForBar(const string want_bar_time, string &json_out)
{
   uint start = GetTickCount();
   while(GetTickCount() - start < (uint)InpDecisionWaitMs)
   {
      if(ReadDecisionJson(json_out))
      {
         string bt = JsonGetString(json_out, "bar_time");
         if(bt == "" ) bt = JsonGetString(json_out, "time");
         if(bt == want_bar_time || StringFind(json_out, want_bar_time) >= 0)
            return true;
      }
      Sleep(InpPollMs);
   }
   if(!ReadDecisionJson(json_out))
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
   const string reason
)
{
   string json = "{";
   json += "\"event\":\"" + event + "\",";
   json += "\"signal_id\":\"" + signal_id + "\",";
   json += "\"action\":\"" + action + "\",";
   json += "\"ok\":" + (ok ? "true" : "false") + ",";
   json += "\"detail\":\"" + detail + "\",";
   json += "\"ticket\":" + IntegerToString((long)ticket) + ",";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"price\":" + DoubleToString(price, _Digits) + ",";
   json += "\"sl\":" + DoubleToString(sl, _Digits) + ",";
   json += "\"tp\":" + DoubleToString(tp, _Digits) + ",";
   json += "\"lots\":" + DoubleToString(lots, 2) + ",";
   json += "\"profit\":" + DoubleToString(profit, 2) + ",";
   json += "\"reason\":\"" + reason + "\",";
   json += "\"time\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "\"";
   json += "}\n";
   int h = FileOpen(BridgePath("fill.json"), FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE) return;
   FileWriteString(h, json);
   FileClose(h);
}

void WriteFillJson(const string signal_id, const string action, const bool ok, const string detail)
{
   WriteFillJsonEx("open", signal_id, action, ok, detail, 0, 0, 0, 0, 0, 0, detail);
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
   double sl_dist = MathAbs(price - sl);
   if(sl_dist <= 0) return false;
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
         if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
         ticket = t;
         price = PositionGetDouble(POSITION_PRICE_OPEN);
         sl = PositionGetDouble(POSITION_SL);
         tp = PositionGetDouble(POSITION_TP);
         lots = PositionGetDouble(POSITION_VOLUME);
         break;
      }
      g_open_ticket = ticket;
      g_open_signal_id = sid;
      g_open_action = action;
      g_open_entry = price;
      g_open_sl = sl;
      g_open_tp = tp;
      g_open_lots = lots;
      g_had_position = true;
      g_last_signal_id = sid;
      Print("ForgeBridge entry ", action, " ticket=", ticket, " lots=", lots, " sl=", sl, " tp=", tp);
   }

   WriteFillJsonEx("open", sid, action, ok, ok ? "opened" : IntegerToString(trade.ResultRetcode()),
                   ticket, price, sl, tp, lots, 0, ok ? "opened" : "reject");
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
   WriteFillJsonEx("close", g_open_signal_id, g_open_action, true, "closed",
                   g_open_ticket, exit_px, g_open_sl, g_open_tp, g_open_lots, profit, reason);
   g_open_ticket = 0;
   g_open_signal_id = "";
   g_had_position = false;
}

//+------------------------------------------------------------------+
void ManageOpen()
{
   int npos = PositionsByMagic();
   if(g_had_position && npos == 0)
   {
      ReportCloseIfNeeded("closed");
      return;
   }
   if(npos == 0) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      g_open_ticket = ticket;
      g_open_entry = PositionGetDouble(POSITION_PRICE_OPEN);
      g_open_sl = PositionGetDouble(POSITION_SL);
      g_open_tp = PositionGetDouble(POSITION_TP);
      g_open_lots = PositionGetDouble(POSITION_VOLUME);
      g_open_action = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      g_had_position = true;

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
void OnTick()
{
   ManageOpen();

   uint now_ms = GetTickCount();
   if(g_last_heartbeat_ms == 0 || now_ms - g_last_heartbeat_ms >= (uint)MathMax(500, InpHeartbeatMs))
   {
      WriteConnectionJson();
      g_last_heartbeat_ms = now_ms;
   }

   datetime t0 = iTime(_Symbol, PERIOD_M15, 0);
   if(t0 == 0 || t0 == g_last_bar)
      return;
   g_last_bar = t0;
   WriteBarsJson();

   if(PositionsByMagic() > 0)
      return;

   datetime t1 = iTime(_Symbol, PERIOD_M15, 1);
   if(t1 == 0 || t1 == g_last_fill_bar)
      return;

   if(InpMode == BRIDGE_REPLAY)
   {
      int idx = FindReplayIndex(t1);
      if(idx < 0) return;
      OpenFromReplay(idx);
      g_last_fill_bar = t1;
      return;
   }

   // Live: publish closed bar, wait for App decision
   if(!WriteBarJson(t1))
      return;

   string want = TimeToString(t1, TIME_DATE | TIME_MINUTES);
   string json;
   if(!WaitDecisionForBar(want, json))
   {
      Print("ForgeBridge: no decision for ", want);
      return;
   }

   string action = JsonGetString(json, "action");
   StringToUpper(action);
   if(action == "FLAT" || action == "HOLD" || action == "")
      return;

   if(OpenFromDecision(json))
      g_last_fill_bar = t1;
}
//+------------------------------------------------------------------+
