//+------------------------------------------------------------------+
//| ImportDukaEA.mq5 — import Dukascopy CSV then idle                |
//+------------------------------------------------------------------+
#property copyright "EdgeMiner2"
#property version   "1.00"

input string InpFile   = "EURUSD_Duka_H1.csv";
input string InpSymbol = "EURUSD_DUK";

bool g_done = false;

int OnInit()
{
   EventSetTimer(2);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

void OnTimer()
{
   if(g_done) return;
   g_done = true;
   EventKillTimer();

   string flag = "import_duka_done.txt";
   if(FileIsExist(flag))
   {
      Print("Import already done previously");
      return;
   }

   CustomSymbolDelete(InpSymbol);
   if(!CustomSymbolCreate(InpSymbol, "EdgeMiner2\\"))
   {
      Print("CustomSymbolCreate failed ", GetLastError());
      return;
   }
   CustomSymbolSetInteger(InpSymbol, SYMBOL_DIGITS, 5);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_CALC_MODE, SYMBOL_CALC_MODE_FOREX);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_CHART_MODE, SYMBOL_CHART_MODE_BID);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_MODE, SYMBOL_TRADE_MODE_FULL);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_POINT, 0.00001);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE, 0.00001);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE, 1.0);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE, 100000);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_MIN, 0.01);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_MAX, 100.0);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_STEP, 0.01);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_SPREAD, 10);
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_BASE, "EUR");
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_PROFIT, "USD");
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_MARGIN, "USD");

   int h = FileOpen(InpFile, FILE_READ|FILE_CSV|FILE_ANSI|FILE_SHARE_READ, ',');
   if(h == INVALID_HANDLE)
   {
      Print("Cannot open ", InpFile, " err=", GetLastError());
      return;
   }

   MqlRates rates[];
   int n = 0;
   while(!FileIsEnding(h))
   {
      string ds = FileReadString(h);
      if(StringLen(ds) < 8)
         break;
      double op = FileReadNumber(h);
      double hi = FileReadNumber(h);
      double lo = FileReadNumber(h);
      double cl = FileReadNumber(h);
      double tv = FileReadNumber(h);
      double rv = FileReadNumber(h);
      int sp = (int)FileReadNumber(h);
      datetime t = StringToTime(ds);
      if(t <= 0) continue;
      ArrayResize(rates, n + 1);
      rates[n].time = t;
      rates[n].open = op;
      rates[n].high = hi;
      rates[n].low = lo;
      rates[n].close = cl;
      rates[n].tick_volume = (long)MathMax(tv, 1);
      rates[n].real_volume = (long)rv;
      rates[n].spread = sp;
      n++;
   }
   FileClose(h);
   Print("Parsed bars=", n);

   int chunk = 4000, written = 0;
   for(int i = 0; i < n; i += chunk)
   {
      int cnt = (int)MathMin(chunk, n - i);
      MqlRates part[];
      ArrayResize(part, cnt);
      ArrayCopy(part, rates, 0, i, cnt);
      int w = CustomRatesUpdate(InpSymbol, part);
      if(w < 0)
      {
         Print("CustomRatesUpdate fail i=", i, " err=", GetLastError());
         return;
      }
      written += w;
   }

   SymbolSelect(InpSymbol, true);
   int fh = FileOpen(flag, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(fh != INVALID_HANDLE)
   {
      FileWriteString(fh, IntegerToString(written));
      FileClose(fh);
   }
   Print("Imported ", written, "/", n, " bars into ", InpSymbol);
}

void OnTick() {}
