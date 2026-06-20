#!/usr/bin/env node
/* Test runner for PriceAC (Node.js, no external deps). */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.join(__dirname, "..");
let passed = 0;
let failed = 0;

const assert = {
  ok(value, message) {
    if (!value) {
      throw new Error(message || "Assertion failed");
    }
  },
  equal(actual, expected, message) {
    if (actual !== expected) {
      throw new Error(message || `Expected ${expected}, got ${actual}`);
    }
  },
  approx(actual, expected, tolerance = 1, message) {
    if (Math.abs(actual - expected) > tolerance) {
      throw new Error(message || `Expected ~${expected}, got ${actual}`);
    }
  },
  throws(fn, message) {
    let threw = false;
    try {
      fn();
    } catch (error) {
      threw = true;
    }
    if (!threw) {
      throw new Error(message || "Expected function to throw");
    }
  }
};

const sharedCtx = {
  console,
  localStorage: {
    store: {},
    getItem(key) {
      return this.store[key] ?? null;
    },
    setItem(key, value) {
      this.store[key] = value;
    },
    removeItem(key) {
      delete this.store[key];
    }
  },
  URLSearchParams,
  fetch: global.fetch,
  document: {
    querySelector: () => null,
    body: { classList: { toggle() {} } }
  }
};

vm.createContext(sharedCtx);

const loadEngine = (relativePath, exportName) => {
  const source = fs.readFileSync(path.join(root, relativePath), "utf8");
  vm.runInContext(source, sharedCtx, { filename: relativePath });

  if (exportName && typeof sharedCtx[exportName] === "undefined") {
    throw new Error(`Export ${exportName} not found in ${relativePath}`);
  }

  return exportName ? sharedCtx[exportName] : sharedCtx;
};

const test = (name, fn) => {
  try {
    fn();
    passed += 1;
    console.log(`  ✓ ${name}`);
  } catch (error) {
    failed += 1;
    console.error(`  ✗ ${name}`);
    console.error(`    ${error.message}`);
  }
};

const loadBitcoin = () => JSON.parse(
  fs.readFileSync(path.join(root, "data/bitcoin.json"), "utf8")
);

const loadGold = () => JSON.parse(
  fs.readFileSync(path.join(root, "data/gold.json"), "utf8")
);

const RANGE_KEYS = ["1D", "2D", "1W", "1M", "3M", "1Y", "5Y", "10Y"];
const INTERVAL_KEYS = ["1D", "1W", "1M"];

console.log("PriceAC tests\n");

const RangeUtils = loadEngine("js/range-utils.js", "RangeUtils");
loadEngine("js/elliott.js", "ElliottEngine");
const PsychologyEngine = loadEngine("js/psychology.js", "PsychologyEngine");
const EmaPsychologyEngine = loadEngine("js/ema-mode.js", "EmaPsychologyEngine");
const MarketDataService = loadEngine("js/market-data.js", "MarketDataService");
loadEngine("js/investment-advice.js", "InvestmentAdvisor");
const AppMode = loadEngine("js/app-mode.js", "AppMode");
const ProAnalysis = loadEngine("js/pro-analysis.js", "ProAnalysis");
const ProSimulation = loadEngine("js/pro-simulation.js", "ProSimulation");

const enrichBitcoinCache = (cache, clipped) => ProAnalysis.enrichPsychologyCache(cache, clipped);

const buildUnifiedBitcoinCache = (fullSeries, asOfDate = null) => PsychologyEngine.buildUnifiedPsychologyCache(
  fullSeries,
  asOfDate
    ? { asOfDate, enrichCache: enrichBitcoinCache }
    : { enrichCache: enrichBitcoinCache }
);

const buildSimWalkForwardCache = (fullSeries, cursorDate) => buildUnifiedBitcoinCache(fullSeries, cursorDate);

test("filterSeriesByDayRange respects calendar days", () => {
  const daily = [
    { date: "2024-01-01" },
    { date: "2024-01-02" },
    { date: "2024-01-03" },
    { date: "2024-01-04" }
  ];
  const slice = RangeUtils.filterSeriesByDayRange(daily, 2);
  assert.equal(slice.length, 2);
  assert.equal(slice[0].date, "2024-01-03");
  assert.equal(slice[1].date, "2024-01-04");
});

test("buildVisibleDailySlice enforces minimum points for 1D", () => {
  const daily = [{ date: "2024-06-18" }, { date: "2024-06-19" }];
  const slice = RangeUtils.buildVisibleDailySlice(daily, "1D");
  assert.equal(slice.length, 2);
});

test("isValidRangeKey rejects unknown ranges", () => {
  assert.ok(RangeUtils.isValidRangeKey("1M"));
  assert.ok(!RangeUtils.isValidRangeKey("2Y"));
  assert.ok(!RangeUtils.isValidRangeKey(""));
});

test("sanitizeSeries sorts and dedupes candles", () => {
  const out = RangeUtils.sanitizeSeries([
    { date: "2024-01-03", price: 3 },
    { date: "2024-01-01", price: 1 },
    { date: "2024-01-01", price: 2 },
    { date: "2024-01-02", price: 2 }
  ]);
  assert.equal(out.length, 3);
  assert.equal(out[0].date, "2024-01-01");
  assert.equal(out[0].price, 1);
  assert.equal(out[2].date, "2024-01-03");
});

test("2D daily range is about 2 days", () => {
  const bitcoin = loadBitcoin();
  const daily = RangeUtils.buildVisibleDailySlice(bitcoin, "2D");
  assert.ok(daily.length >= 2 && daily.length <= 2, `2D daily length ${daily.length}`);
});

test("1M daily range is about 30 days", () => {
  const bitcoin = loadBitcoin();
  const daily = RangeUtils.buildVisibleDailySlice(bitcoin, "1M");
  assert.ok(daily.length >= 28 && daily.length <= 31, `1M daily length ${daily.length}`);
});

test("1M weekly range is about 4-5 weeks not 30 weeks", () => {
  const bitcoin = loadBitcoin();
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1M", "1W", PsychologyEngine.aggregateSeries);
  assert.ok(visible.length >= 4 && visible.length <= 6, `1M weekly bars ${visible.length}`);
});

test("1Y weekly range is about 52 weeks", () => {
  const bitcoin = loadBitcoin();
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1Y", "1W", PsychologyEngine.aggregateSeries);
  assert.ok(visible.length >= 50 && visible.length <= 54, `1Y weekly bars ${visible.length}`);
});

test("10Y span covers at most 10 years of daily data", () => {
  const bitcoin = loadBitcoin();
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "10Y", "1D", PsychologyEngine.aggregateSeries);
  const span = RangeUtils.getVisibleSpanDays(visible);
  assert.ok(span <= 3652, `10Y span ${span} days`);
  assert.ok(visible.length >= 365, "10Y should include substantial history");
});

test("all range and interval combinations produce valid visible series", () => {
  const bitcoin = loadBitcoin();

  RANGE_KEYS.forEach((rangeKey) => {
    INTERVAL_KEYS.forEach((intervalKey) => {
      const visible = RangeUtils.buildVisibleSeries(
        bitcoin,
        rangeKey,
        intervalKey,
        PsychologyEngine.aggregateSeries
      );

      assert.ok(visible.length >= RangeUtils.MIN_VISIBLE_POINTS, `${rangeKey}/${intervalKey} too short`);

      for (let index = 1; index < visible.length; index += 1) {
        assert.ok(
          visible[index].date >= visible[index - 1].date,
          `${rangeKey}/${intervalKey} not sorted at ${index}`
        );
      }

      visible.forEach((point) => {
        assert.ok(point.date, `${rangeKey}/${intervalKey} missing date`);
        assert.ok(Number.isFinite(point.close ?? point.price), `${rangeKey}/${intervalKey} invalid price`);
      });
    });
  });
});

test("range switch sequence keeps monotonic dates", () => {
  const bitcoin = loadBitcoin();
  const sequence = ["1M", "1Y", "1W", "10Y", "3M", "5Y", "1D"];

  sequence.forEach((rangeKey) => {
    const visible = RangeUtils.buildVisibleSeries(
      bitcoin,
      rangeKey,
      "1D",
      PsychologyEngine.aggregateSeries
    );
    const sanitized = RangeUtils.sanitizeSeries(visible);
    assert.equal(sanitized.length, visible.length);

    for (let index = 1; index < sanitized.length; index += 1) {
      assert.ok(sanitized[index].date > sanitized[index - 1].date, `range ${rangeKey} broke order`);
    }
  });
});

test("RSI aligned to visible chart dates for all ranges", () => {
  const bitcoin = loadBitcoin();
  const multi = PsychologyEngine.buildMultiFrameRsi(bitcoin);

  RANGE_KEYS.forEach((rangeKey) => {
    INTERVAL_KEYS.forEach((intervalKey) => {
      const visible = RangeUtils.buildVisibleSeries(
        bitcoin,
        rangeKey,
        intervalKey,
        PsychologyEngine.aggregateSeries
      );
      const aligned = PsychologyEngine.alignRsiToVisible(visible, multi);

      assert.equal(aligned.twoDay.length, visible.length, `${rangeKey}/${intervalKey} twoDay rsi length`);
      assert.equal(aligned.weekly.length, visible.length, `${rangeKey}/${intervalKey} weekly rsi length`);
      assert.equal(aligned.monthly.length, visible.length, `${rangeKey}/${intervalKey} monthly rsi length`);

      aligned.twoDay.forEach((point, index) => {
        assert.equal(point.date, visible[index].date);
        assert.ok(point.value >= 0 && point.value <= 100);
      });
    });
  });
});

test("reference asset is bitcoin for psychology tuning", () => {
  assert.equal(PsychologyEngine.REFERENCE_ASSET, "bitcoin");
});

test("basic pro and simulation use the same unified psychology pipeline on bitcoin", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const date = daily[600].date;

  const basic = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { asOfDate: date });
  const pro = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, {
    asOfDate: date,
    enrichCache: enrichBitcoinCache
  });
  const simulation = buildSimWalkForwardCache(bitcoin, date);

  const basicZone = PsychologyEngine.getPsychologyZoneAtDate(basic, date);
  const proZone = PsychologyEngine.getPsychologyZoneAtDate(pro, date);
  const simZone = PsychologyEngine.getPsychologyZoneAtDate(simulation, date);

  assert.equal(proZone, basicZone, "pro enrich must not change zone labels");
  assert.equal(simZone, basicZone, "simulation must use the same zone algorithm as basic/pro");
});

test("psychology cache covers 10Y and projects to visible range", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  assert.ok(cache, "cache should build");
  assert.ok(cache.regions.length >= 2);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "3M", "1D", PsychologyEngine.aggregateSeries);
  const timeline = PsychologyEngine.projectPsychologyToSeries(cache, visible);
  assert.equal(timeline.length, visible.length);
  assert.ok(timeline.every((point) => point.zone));
});

test("reference assets build psychology cache (smoke only)", () => {
  const loadJson = (name) => JSON.parse(
    fs.readFileSync(path.join(root, `data/${name}.json`), "utf8")
  );

  ["gold", "ethereum", "sp500"].forEach((asset) => {
    const series = loadJson(asset);
    const cache = PsychologyEngine.buildUnifiedPsychologyCache(series);
    assert.ok(cache, `${asset} cache should build for reference`);
    assert.ok(cache.regions.length >= 1);
  });
});

test("market data merge dedupes by date", () => {
  const base = [
    { date: "2024-01-01", open: 1, high: 2, low: 0.5, price: 1.5 },
    { date: "2024-01-02", open: 2, high: 3, low: 1.5, price: 2.5 }
  ];
  const patch = [
    { date: "2024-01-02", open: 2, high: 4, low: 1.5, price: 3.5 },
    { date: "2024-01-03", open: 3, high: 5, low: 2.5, price: 4.5 }
  ];
  const merged = MarketDataService.mergeSeries(base, patch);
  assert.equal(merged.length, 3);
  assert.equal(merged[1].price, 3.5);
});

test("psychology cycle law maps elliott waves to market sentiment order", () => {
  const law = sharedCtx.ElliottEngine.PSYCHOLOGY_CYCLE_LAW;
  assert.equal(law.join(","), [
    "Disbelief",
    "Hope",
    "Optimism",
    "Belief",
    "Euphoria",
    "Complacency",
    "Anxiety",
    "Denial",
    "Panic",
    "Capitulation"
  ].join(","));

  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const bullRunZones = new Set();
  const checkpoints = ["2020-10-01", "2020-12-15", "2021-02-01", "2021-04-01"];

  checkpoints.forEach((date) => {
    const zone = PsychologyEngine.getPsychologyZoneAtDate(cache, date);
    if (zone) {
      bullRunZones.add(zone);
    }
  });

  assert.ok(bullRunZones.has("Hope") || bullRunZones.has("Optimism") || bullRunZones.has("Belief"));
});

test("bitcoin capitulation follows panic when price stops rising", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const capitulationRegions = cache.regions.filter((region) => region.zone === "Capitulation");

  assert.ok(capitulationRegions.length >= 1, "expected Capitulation after panic washouts");

  const panicThenCapitulation = cache.regions.some((region, index) => (
    index > 0
    && cache.regions[index - 1].zone === "Panic"
    && region.zone === "Capitulation"
  ));

  assert.ok(
    panicThenCapitulation || capitulationRegions.some((region) => region.waveId === "C"),
    "Capitulation should follow Panic or mark a flat tail after wave C"
  );
});

test("bitcoin aug 2022 bear decline avoids bullish psychology zones", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const forbidden = new Set(["Belief", "Euphoria", "Complacency", "Thrill", "Optimism", "Hope"]);
  const checkpoints = ["2022-08-22", "2022-08-26", "2022-09-05", "2022-09-12"];

  checkpoints.forEach((date) => {
    const zone = PsychologyEngine.getPsychologyZoneAtDate(cache, date);
    assert.ok(
      !forbidden.has(zone),
      `${date} should not map to bullish zone ${zone} while price was falling`
    );
  });
});

test("elliott regions span full weekly window", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  assert.equal(cache.regions[0].startDate, cache.rangeStart);
  assert.equal(cache.regions[cache.regions.length - 1].endDate, cache.rangeEnd);
});

test("dedupeByDate removes duplicate candles", () => {
  const out = RangeUtils.dedupeByDate([
    { date: "2024-01-01", price: 1 },
    { date: "2024-01-01", price: 2 },
    { date: "2024-01-02", price: 3 }
  ]);
  assert.equal(out.length, 2);
});

test("psychology cache round-trips through localStorage", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  PsychologyEngine.savePsychologyCache("bitcoin", cache);
  const loaded = PsychologyEngine.loadPsychologyCache("bitcoin");
  assert.ok(PsychologyEngine.isPsychologyCacheValid(loaded, bitcoin));
  assert.equal(loaded.rangeStart, cache.rangeStart);
  assert.equal(loaded.regionCount, cache.regionCount);
});

test("elliott overlay builds zigzag for visible range", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1Y", "1D", PsychologyEngine.aggregateSeries);
  const overlay = sharedCtx.ElliottEngine.buildVisibleWaveOverlay(cache, visible);

  assert.ok(overlay, "overlay should build");
  assert.ok(overlay.points.length >= 2);
  assert.ok(overlay.markers.length >= 1);
});

test("investment advice ranks zones from 10Y history", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const advice = sharedCtx.InvestmentAdvisor.buildRecommendation(
    cache,
    bitcoin,
    PsychologyEngine.buildMarketSnapshot(
      cache,
      bitcoin,
      RangeUtils.buildVisibleSeries(bitcoin, "1Y", "1D", PsychologyEngine.aggregateSeries)
    )
  );

  assert.ok(advice.hasAdvice);
  assert.ok(advice.safestZone?.zone);
  assert.ok(advice.mostEffectiveZone?.zone);
  assert.ok(advice.topAccumulateZones.length >= 1);
  assert.ok(advice.action);
  if (advice.avoidZones.length) {
    assert.ok(advice.safestZone.safety >= advice.avoidZones[0].safety);
  }
});

test("AppMode persists basic, ema, pro, and simulation in localStorage", () => {
  sharedCtx.localStorage.removeItem("priceac.app.mode");
  AppMode.setMode("ema");
  assert.equal(AppMode.getMode(), "ema");
  assert.equal(AppMode.isEma(), true);
  assert.equal(AppMode.getPsychologyModel(), "ema");
  assert.equal(AppMode.usesProAnalysis(), false);
  AppMode.setMode("pro");
  assert.equal(AppMode.getMode(), "pro");
  assert.equal(AppMode.isPro(), true);
  assert.equal(AppMode.usesProAnalysis(), true);
  AppMode.setMode("simulation");
  assert.equal(AppMode.isSimulation(), true);
  assert.equal(AppMode.usesProAnalysis(), true);
  assert.equal(AppMode.isPro(), false);
  AppMode.setMode("basic");
  assert.equal(AppMode.isBasic(), true);
  assert.equal(AppMode.usesProAnalysis(), false);
  assert.equal(AppMode.getPsychologyModel(), "elliott");
});

test("ema mode builds separate cache and enforces EMA/trend zone rules on bitcoin", () => {
  const bitcoin = loadBitcoin();
  const elliottCache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const emaCache = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" });
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D").slice(-PsychologyEngine.TEN_YEAR_DAYS);
  const ema50 = EmaPsychologyEngine.computeEmaSeries(daily, 50);
  const ema200 = EmaPsychologyEngine.computeEmaSeries(daily, 200);

  assert.equal(elliottCache.model, "elliott");
  assert.equal(emaCache.model, "ema");
  assert.ok(emaCache.regions.length >= 2);

  let checked = 0;
  emaCache.regions.forEach((region) => {
    const context = EmaPsychologyEngine.buildContext(daily, ema50, ema200, region.endDate);
    if (!context.ready || region.zone === "Observing") {
      return;
    }

    checked += 1;
    assert.ok(
      EmaPsychologyEngine.validateRegionRules(region, context),
      `Zone ${region.zone} vi phạm EMA/trend tại ${region.endDate}`
    );
  });

  assert.ok(checked >= 10, "expected enough EMA-validated regions");

  const hasDifference = emaCache.regions.some((region, index) => (
    region.zone !== elliottCache.regions[index]?.zone
  ));
  assert.ok(hasDifference, "EMA mode should remap at least one region vs Elliott");
});

test("ema psychology cache saves and loads with separate storage key", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" });

  PsychologyEngine.savePsychologyCache("bitcoin", cache, "ema");
  const loaded = PsychologyEngine.loadPsychologyCache("bitcoin", "ema");

  assert.ok(loaded);
  assert.equal(loaded.model, "ema");
  assert.ok(PsychologyEngine.isPsychologyCacheValid(loaded, bitcoin, "ema"));
  assert.ok(!PsychologyEngine.isPsychologyCacheValid(loaded, bitcoin, "elliott"));
  PsychologyEngine.clearPsychologyCache("bitcoin", "ema");
});

test("elliott validation annotates regions", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const enriched = ProAnalysis.enrichPsychologyCache(cache, bitcoin);

  assert.ok(enriched.regions.length >= 2);
  assert.ok("elliottValidated" in enriched.regions[0]);
  assert.ok(enriched.summary.validationNote);
  assert.ok(!enriched.regions[0].elliottLabel.includes("Giai đoạn"));
});

test("pro walk-forward ranking builds out-of-sample stats", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const walkForward = ProAnalysis.buildWalkForwardRanking(cache, bitcoin);

  assert.ok(walkForward.trainRegionCount >= 2);
  assert.ok(walkForward.testRegionCount >= 0);
  if (walkForward.testRanking) {
    assert.ok(walkForward.testRanking.safest?.zone);
  }
});

test("pro recommendation includes risk plan and mode", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "3M", "1D", PsychologyEngine.aggregateSeries);
  const snapshot = PsychologyEngine.buildMarketSnapshot(cache, bitcoin, visible);
  const advice = ProAnalysis.buildProRecommendation(cache, bitcoin, snapshot, visible);

  assert.ok(advice.hasAdvice);
  assert.equal(advice.mode, "pro");
  assert.ok(advice.riskPlan?.positionLabel);
  assert.ok(Number.isFinite(advice.riskPlan.invalidationPrice));
});

test("mode comparison detects basic vs pro advice", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1Y", "1D", PsychologyEngine.aggregateSeries);
  const snapshot = PsychologyEngine.buildMarketSnapshot(cache, bitcoin, visible);
  const basic = sharedCtx.InvestmentAdvisor.buildRecommendation(cache, bitcoin, snapshot);
  const pro = ProAnalysis.buildProRecommendation(cache, bitcoin, snapshot, visible);
  const comparison = ProAnalysis.buildModeComparison(basic, pro);

  assert.ok(comparison);
  assert.ok(comparison.basicAction);
  assert.ok(comparison.proAction);
});

test("pro elliott overlay uses enriched cache for validated markers", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "5Y", "1D", PsychologyEngine.aggregateSeries);
  const enriched = ProAnalysis.enrichPsychologyCache(cache, bitcoin);
  const rawValidated = sharedCtx.ElliottEngine.buildVisibleWaveOverlay(cache, visible, {
    validatedOnly: true
  });
  const enrichedValidated = sharedCtx.ElliottEngine.buildVisibleWaveOverlay(enriched, visible, {
    validatedOnly: true
  });

  assert.equal(rawValidated?.markers?.length ?? 0, 0);
  assert.ok((enrichedValidated?.markers?.length ?? 0) >= 1);
});

test("pro signal score and macro context build from 10Y data", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "3M", "1D", PsychologyEngine.aggregateSeries);
  const snapshot = PsychologyEngine.buildMarketSnapshot(cache, bitcoin, visible);
  const advice = ProAnalysis.buildProRecommendation(cache, bitcoin, snapshot, visible);

  assert.ok(advice.signal?.score >= 0 && advice.signal.score <= 100);
  assert.ok(["A", "B", "C", "D"].includes(advice.signal.grade));
  assert.equal(advice.signal.factors.length, 6);
  assert.ok(advice.macro?.summary);
  assert.ok(advice.walkForwardDetail?.trainRegionCount >= 1);
});

test("pro brief includes scenarios and analogs", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1Y", "1D", PsychologyEngine.aggregateSeries);
  const brief = ProAnalysis.buildProBrief(
    cache,
    bitcoin,
    PsychologyEngine.buildMarketSnapshot(cache, bitcoin, visible),
    visible,
    null,
    "accumulate"
  );

  assert.ok(brief.signal);
  assert.ok(brief.scenarios?.bullTarget);
  assert.ok("items" in brief.analogs);
});

test("pro signal score series aligns to visible chart", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "3M", "1D", PsychologyEngine.aggregateSeries);
  const series = ProAnalysis.buildSignalScoreSeries(
    cache,
    bitcoin,
    visible,
    { bitcoin: cache },
    { bitcoin },
    "bitcoin"
  );

  assert.equal(series.length, visible.length);
  series.forEach((point, index) => {
    assert.equal(point.date, visible[index].date);
    assert.ok(point.value >= 0 && point.value <= 100);
    assert.ok(["A", "B", "C", "D"].includes(point.grade));
  });
});

test("simulation mode builds timeline and cutoff date", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const end = daily.at(-120).date;
  const start = daily.at(-240).date;

  AppMode.setMode("simulation");

  ProSimulation.init({
    getContext: () => ({
      fullData: bitcoin,
      interval: "1D",
      hasCache: false
    }),
    refreshPsychology: (cursorDate) => buildSimWalkForwardCache(bitcoin, cursorDate),
    getBaselineCache: () => buildUnifiedBitcoinCache(bitcoin),
    onFrame: () => {}
  });

  assert.ok(ProSimulation.arm(start, end));
  assert.ok(ProSimulation.isActive());
  assert.equal(ProSimulation.getCutoffDate(), start);
  assert.equal(ProSimulation.getStatus().progress, 0);
  assert.ok(ProSimulation.getPsychologyCache()?.regions?.length >= 1);
  assert.equal(ProSimulation.getPsychologyCache().rangeEnd, start);

  ProSimulation.seekPercent(100);
  assert.equal(ProSimulation.getCutoffDate(), end);
  ProSimulation.stop();
  assert.ok(!ProSimulation.isActive());
  assert.ok(!ProSimulation.getPsychologyCache());
});

test("psychology compare uses zone at date for walk-forward vs 10Y", () => {
  const bitcoin = loadBitcoin();
  const baseline = PsychologyEngine.buildPsychologyCache(bitcoin);
  const walkForward = PsychologyEngine.buildPsychologyCache(bitcoin.slice(0, 400));
  const date = PsychologyEngine.aggregateSeries(bitcoin, "1D")[399].date;
  const comparison = PsychologyEngine.comparePsychologyAtDate(walkForward, baseline, date);

  assert.ok(comparison.walkForwardZone);
  assert.ok(comparison.baselineZone);
  assert.equal(typeof comparison.match, "boolean");
});

test("simulation accuracy tracks weekly zone match against 10Y baseline", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const baseline = PsychologyEngine.buildPsychologyCache(bitcoin);

  AppMode.setMode("simulation");
  ProSimulation.init({
    getContext: () => ({ fullData: bitcoin, interval: "1D", hasCache: false }),
    refreshPsychology: (cursorDate) => buildSimWalkForwardCache(bitcoin, cursorDate),
    getBaselineCache: () => baseline,
    onFrame: () => {}
  });

  const start = daily[300].date;
  const end = daily[330].date;
  ProSimulation.arm(start, end);

  const summary = ProSimulation.getAccuracySummaryForCursor(ProSimulation.getCutoffDate());
  assert.ok(summary.hasAccuracy);
  assert.ok(summary.percent >= 0 && summary.percent <= 100);
  assert.ok(summary.comparable >= 1);
});

test("simulation psychology refreshes on new week only", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  let refreshCount = 0;

  AppMode.setMode("simulation");
  ProSimulation.init({
    getContext: () => ({ fullData: bitcoin, interval: "1D", hasCache: false }),
    refreshPsychology: (cursorDate) => {
      refreshCount += 1;
      return buildSimWalkForwardCache(bitcoin, cursorDate);
    },
    onFrame: () => {}
  });

  const anchorWeek = PsychologyEngine.getWeekStart(daily[200].date);
  const sameWeek = daily.filter((point) => PsychologyEngine.getWeekStart(point.date) === anchorWeek);
  const start = sameWeek[0].date;
  const end = sameWeek[sameWeek.length - 1].date;

  ProSimulation.arm(start, end);
  const afterArm = refreshCount;

  ProSimulation.seekPercent(100);
  const afterSeek = refreshCount;

  assert.ok(afterArm >= 1);
  assert.equal(afterSeek, afterArm, "scrub should use precomputed weekly cache only");
});

test("daily blend adjusts unvalidated low-confidence zones", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const asOfDate = daily[620].date;
  const clipped = bitcoin.filter((point) => point.date <= asOfDate);
  let cache = PsychologyEngine.buildPsychologyCache(clipped);
  cache = ProAnalysis.enrichPsychologyCache(cache, clipped) || cache;

  const blended = PsychologyEngine.buildWalkForwardPsychologyCache(bitcoin, asOfDate, {
    enrichCache: (entry, series) => ProAnalysis.enrichPsychologyCache(entry, series),
    applyConfidenceGate: false,
    applyDailyBlend: true
  });

  assert.ok(blended);
  assert.ok(blended.regions.length >= 1);
});

test("weekly walk-forward accuracy report vs 10Y baseline", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const end = daily.at(-1).date;
  const start = daily[Math.max(0, daily.length - 730)].date;
  const report = PsychologyEngine.buildWalkForwardAccuracyReport(bitcoin, {
    startDate: start,
    endDate: end,
    minHistoryDays: 365,
    relaxedDistance: 2,
    enrichCache: enrichBitcoinCache
  });

  assert.ok(report, "report should build on bitcoin");
  assert.ok(report.legacy);
  assert.ok(report.enhanced);
  assert.ok(report.comparableWeeks >= 50, "need enough weekly checkpoints");
  assert.ok(report.accuracyPercent >= 0 && report.accuracyPercent <= 100);
  assert.ok(report.errorPercent >= 0 && report.errorPercent <= 100);
  assert.equal(
    Math.round((report.accuracyPercent + report.errorPercent) * 10) / 10,
    100,
    "accuracy + error should sum to 100"
  );
  assert.ok(report.relaxedAccuracyPercent >= report.accuracyPercent);
  assert.ok(report.improvement.accuracyDelta !== null);
  assert.ok(
    report.enhanced.accuracyPercent >= report.legacy.accuracyPercent,
    `enhanced accuracy ${report.enhanced.accuracyPercent}% should beat legacy ${report.legacy.accuracyPercent}%`
  );
  assert.ok(
    report.improvement.errorDelta >= 0,
    "enhanced pipeline should not increase error vs legacy"
  );

  const viaSimulation = (() => {
    AppMode.setMode("simulation");
    ProSimulation.init({
      getContext: () => ({ fullData: bitcoin, interval: "1D", hasCache: false }),
      refreshPsychology: (cursorDate) => buildSimWalkForwardCache(bitcoin, cursorDate),
      getBaselineCache: () => buildUnifiedBitcoinCache(bitcoin),
      onFrame: () => {}
    });
    ProSimulation.arm(start, end);
    return ProSimulation.getAccuracySummaryForCursor(end);
  })();

  assert.approx(viaSimulation.percent, report.accuracyPercent, 2);

  if (process.env.SIM_ACCURACY_REPORT === "1") {
    console.log("\n--- Simulation walk-forward vs 10Y (Bitcoin, ~2Y) ---");
    console.log(`Tuần so sánh: ${report.comparableWeeks}`);
    console.log(`Legacy: ${report.legacy.accuracyPercent}% · Enhanced: ${report.enhanced.accuracyPercent}% (+${report.improvement.accuracyDelta})`);
    console.log(`Khớp chính xác: ${report.accuracyPercent}% · sai số: ${report.errorPercent}%`);
    console.log(`Khớp lỏng: ${report.relaxedAccuracyPercent}% (+${report.improvement.relaxedAccuracyDelta})`);
    console.log("Lệch nhiều nhất:", report.mismatchPairs.slice(0, 5));
  }
});

test("weekly walk-forward accuracy report works on reference gold data", () => {
  const gold = loadGold();
  const report = PsychologyEngine.buildWalkForwardAccuracyReport(gold, {
    minHistoryDays: 180,
    relaxedDistance: 2
  });

  assert.ok(report, "gold report is reference-only smoke");
  assert.ok(report.comparableWeeks >= 20);
  assert.ok(Number.isFinite(report.accuracyPercent));
});

test("walk-forward enhancements apply confidence gate and hysteresis", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const asOfDate = daily[500].date;
  const clipped = bitcoin.filter((point) => point.date <= asOfDate);
  const raw = PsychologyEngine.buildPsychologyCache(clipped);
  const gated = PsychologyEngine.applyConfidenceGateToCache(raw, 100);

  assert.ok(raw);
  assert.ok(gated);
  assert.ok(gated.regions.every((region) => region.zone === "Observing"));

  const hysteresis = PsychologyEngine.createSimulationHysteresisState();
  const first = PsychologyEngine.applySimulationHysteresis(raw, asOfDate, hysteresis, 2);
  const secondDate = daily[507].date;
  const secondRaw = PsychologyEngine.buildPsychologyCache(
    bitcoin.filter((point) => point.date <= secondDate)
  );
  const held = PsychologyEngine.applySimulationHysteresis(secondRaw, secondDate, hysteresis, 2);
  const firstZone = PsychologyEngine.getPsychologyZoneAtDate(first, asOfDate);
  const heldZone = PsychologyEngine.getPsychologyZoneAtDate(held, secondDate);
  assert.equal(firstZone, heldZone, "hysteresis should hold zone for one week flip");
});

test("week-end checkpoints are not earlier than week-start checkpoints", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const start = daily[400].date;
  const end = daily[500].date;
  const weekStart = PsychologyEngine.buildWeeklyWalkForwardCheckpoints(daily, start, end, false);
  const weekEnd = PsychologyEngine.buildWeeklyWalkForwardCheckpoints(daily, start, end, true);

  weekEnd.forEach((endPoint) => {
    const startPoint = weekStart.find((item) => item.weekKey === endPoint.weekKey);
    assert.ok(startPoint);
    assert.ok(endPoint.asOfDate >= startPoint.asOfDate);
  });
});

test("pro daily rsi uses one decimal place", () => {
  const bitcoin = loadBitcoin();
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1M", "1D", PsychologyEngine.aggregateSeries);
  const aligned = ProAnalysis.alignRsiForPro(bitcoin, visible);

  aligned.twoDay.forEach((point) => {
    const decimals = String(point.value).includes(".")
      ? String(point.value).split(".")[1].length
      : 0;
    assert.ok(decimals <= 1, `RSI 1D has too many decimals: ${point.value}`);
  });
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
