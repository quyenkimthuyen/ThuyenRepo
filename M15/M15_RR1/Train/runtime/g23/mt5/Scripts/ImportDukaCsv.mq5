//+------------------------------------------------------------------+
//| ImportDukaCsv.mq5 — import Dukascopy H1 CSV into custom symbol   |
//+------------------------------------------------------------------+
#property script_show_inputs
input string InpFile   = "EURUSD_Duka_H1.csv";
input string InpSymbol = "EURUSD_DUK";
input bool   InpRecreate = true;

int OnStart()
{
   if(InpRecreate)
   {
      if(SymbolSelect(InpSymbol, true))
         SymbolSelect(InpSymbol, false);
      CustomSymbolDelete(InpSymbol);
   }

   if(!CustomSymbolCreate(InpSymbol, "EdgeMiner2\\", "EURUSD"))
   {
      // origin may not exist offline — create without origin
      if(!CustomSymbolCreate(InpSymbol, "EdgeMiner2\\"))
      {
         Print("CustomSymbolCreate failed: ", GetLastError());
         return INIT_FAILED;
      }
   }

   CustomSymbolSetInteger(InpSymbol, SYMBOL_DIGITS, 5);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_CALC_MODE, SYMBOL_CALC_MODE_FOREX);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_CHART_MODE, SYMBOL_CHART_MODE_BID);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_MODE, SYMBOL_TRADE_MODE_FULL);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_EXEMODE, SYMBOL_TRADE_EXECUTION_INSTANT);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_FILLING_MODE, SYMBOL_FILLING_FOK|SYMBOL_FILLING_IOC);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_ORDER_MODE,
      SYMBOL_ORDER_MARKET|SYMBOL_ORDER_LIMIT|SYMBOL_ORDER_STOP|SYMBOL_ORDER_SL|SYMBOL_ORDER_TP);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_POINT, 0.00001);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE, 0.00001);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE, 1.0);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE, 100000);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_VOLUME_MIN, 100); // 0.01 lots * 100? volume in units depends
   // volume min as lots*100 for forex often: use doubles
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_MIN, 0.01);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_MAX, 100.0);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_STEP, 0.01);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_SPREAD, 10);
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_BASE, "EUR");
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_PROFIT, "USD");
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_MARGIN, "EUR");

   int h = FileOpen(InpFile, FILE_READ|FILE_CSV|FILE_ANSI|FILE_SHARE_READ, ',');
   if(h == INVALID_HANDLE)
   {
      Print("Cannot open ", InpFile, " err=", GetLastError());
      return INIT_FAILED;
   }

   MqlRates rates[];
   ArrayResize(rates, 0);
   int n = 0;
   while(!FileIsEnding(h))
   {
      string ds = FileReadString(h);
      if(ds == "" || FileIsEnding(h))
         break;
      // date time may be "2024.01.01 00:00:00" in first field if CSV not split on space
      // Our CSV: YYYY.MM.DD HH:MM:SS,open,high,low,close,tickvol,vol,spread
      // With comma delimiter, first field is "YYYY.MM.DD HH:MM:SS" only if no comma in datetime — OK
      double op = FileReadNumber(h);
      double hi = FileReadNumber(h);
      double lo = FileReadNumber(h);
      double cl = FileReadNumber(h);
      double tv = FileReadNumber(h);
      double rv = FileReadNumber(h);
      int sp = (int)FileReadNumber(h);

      datetime t = StringToTime(ds);
      if(t <= 0)
         continue;

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

   if(n <= 0)
   {
      Print("No bars parsed");
      return INIT_FAILED;
   }

   // Replace rates in chunks
   int chunk = 5000;
   int written = 0;
   for(int i = 0; i < n; i += chunk)
   {
      int cnt = MathMin(chunk, n - i);
      MqlRates part[];
      ArrayResize(part, cnt);
      for(int j = 0; j < cnt; j++)
         part[j] = rates[i + j];
      int w = CustomRatesUpdate(InpSymbol, part);
      if(w < 0)
      {
         Print("CustomRatesUpdate failed at ", i, " err=", GetLastError());
         return INIT_FAILED;
      }
      written += w;
   }

   SymbolSelect(InpSymbol, true);
   Print("Imported ", written, "/", n, " bars into ", InpSymbol);
   ChartOpen(InpSymbol, PERIOD_H1);
   return INIT_SUCCEEDED;
}
