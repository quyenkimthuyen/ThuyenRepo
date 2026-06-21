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

const RANGE_KEYS = ["1M", "3M", "1Y", "5Y", "10Y"];
const INTERVAL_KEYS = ["1D", "1W", "1M"];

console.log("PriceAC tests\n");

const RangeUtils = loadEngine("js/range-utils.js", "RangeUtils");
loadEngine("js/elliott.js", "ElliottEngine");
const PsychologyEngine = loadEngine("js/psychology.js", "PsychologyEngine");
const EmaPsychologyEngine = loadEngine("js/ema-mode.js", "EmaPsychologyEngine");
const MarketDataService = loadEngine("js/market-data.js", "MarketDataService");
loadEngine("js/investment-advice.js", "InvestmentAdvisor");
const AppMode = loadEngine("js/app-mode.js", "AppMode");
const ProSimulation = loadEngine("js/pro-simulation.js", "ProSimulation");

const buildSimWalkForwardCache = (fullSeries, cursorDate) => PsychologyEngine.buildUnifiedPsychologyCache(
  fullSeries,
  { asOfDate: cursorDate, model: "ema" }
);

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

test("buildVisibleDailySlice enforces minimum points", () => {
  const daily = [{ date: "2024-06-18" }, { date: "2024-06-19" }];
  const slice = RangeUtils.buildVisibleDailySlice(daily, "1M");
  assert.equal(slice.length, 2);
});

test("isValidRangeKey rejects unknown ranges", () => {
  assert.ok(RangeUtils.isValidRangeKey("1M"));
  assert.ok(!RangeUtils.isValidRangeKey("1D"));
  assert.ok(!RangeUtils.isValidRangeKey("2D"));
  assert.ok(!RangeUtils.isValidRangeKey("1W"));
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
  const sequence = ["1M", "1Y", "3M", "5Y", "10Y"];

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

test("ema and simulation use the same unified psychology pipeline on bitcoin", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const date = daily[600].date;

  const ema = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { asOfDate: date, model: "ema" });
  const simulation = buildSimWalkForwardCache(bitcoin, date);

  const emaZone = PsychologyEngine.getPsychologyZoneAtDate(ema, date);
  const simZone = PsychologyEngine.getPsychologyZoneAtDate(simulation, date);

  assert.equal(simZone, emaZone, "simulation must use the same EMA zone algorithm");
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
  const legacyZones = ["Depression", "Anger", "Thrill"];

  assert.ok(advice.hasAdvice);
  assert.ok(advice.safestZone?.zone);
  assert.ok(advice.mostEffectiveZone?.zone);
  assert.ok(advice.topAccumulateZones.length >= 1);
  assert.ok(advice.action);
  assert.ok(PsychologyEngine.UNIFIED_CYCLE_ZONES.includes(advice.safestZone.zone));
  advice.zoneRanking.forEach((item) => {
    assert.ok(!legacyZones.includes(item.zone), `legacy zone ${item.zone} should not appear`);
    assert.ok(PsychologyEngine.UNIFIED_CYCLE_ZONES.includes(item.zone));
  });
  if (advice.avoidZones.length) {
    assert.ok(advice.safestZone.safety >= advice.avoidZones[0].safety);
  }
});

test("AppMode persists ema and simulation in localStorage", () => {
  sharedCtx.localStorage.removeItem("priceac.app.mode");
  AppMode.setMode("ema");
  assert.equal(AppMode.getMode(), "ema");
  assert.equal(AppMode.isEma(), true);
  assert.equal(AppMode.getPsychologyModel(), "ema");
  AppMode.setMode("simulation");
  assert.equal(AppMode.isSimulation(), true);
  assert.equal(AppMode.getPsychologyModel(), "ema");
  AppMode.setMode("ema");
  assert.equal(AppMode.isEma(), true);
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
    const context = EmaPsychologyEngine.buildContext(
      daily,
      ema50,
      ema200,
      new Map(),
      region.endDate
    );
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

test("ema mode splits long regions when EMA regime changes with confirmation", () => {
  const bitcoin = loadBitcoin();
  const elliottCache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const emaCache = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" });

  assert.ok(
    emaCache.regions.length >= elliottCache.regions.length,
    "weekly EMA refinement should not reduce region count"
  );
});

test("elliott bear macro maps wave 2 rallies to denial not optimism", () => {
  const bitcoin = loadBitcoin();
  const weekly = PsychologyEngine.aggregateSeries(bitcoin, "1W");
  const cache = PsychologyEngine.buildPsychologyCache(bitcoin);
  const bearWave2 = cache.regions.find((region) => (
    region.macroRegime === "bear" && region.waveId === "2"
  ));

  if (bearWave2) {
    assert.ok(
      ["Denial", "Anxiety", "Disbelief"].includes(bearWave2.zone),
      `bear wave 2 should be bearish psychology, got ${bearWave2.zone}`
    );
  }
});

test("psychology segments use lower opacity for low confidence zones", () => {
  const bitcoin = loadBitcoin();
  const cache = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" });
  const visible = RangeUtils.buildVisibleSeries(bitcoin, "1Y", "1D", PsychologyEngine.aggregateSeries);
  const timeline = PsychologyEngine.projectPsychologyToSeries(cache, visible);
  const segments = PsychologyEngine.buildPsychologySegments(visible, timeline);
  const low = segments.find((segment) => segment.lowConfidence);
  const high = segments.find((segment) => !segment.lowConfidence && segment.opacity);

  assert.ok(segments.length >= 1);
  if (low && high) {
    assert.ok(low.opacity < high.opacity, "low confidence segments should be more transparent");
  }
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
    getBaselineCache: () => PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" }),
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
  const baseline = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" });
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
  const baseline = PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" });

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

test("simulation freezes historical psychology zones as later weeks advance", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const week1Date = daily[420].date;
  const week2Date = daily[455].date;
  const sampleDate = daily[405].date;

  const cache1 = buildSimWalkForwardCache(bitcoin, week1Date);
  const cache2 = buildSimWalkForwardCache(bitcoin, week2Date);
  const hysteresis = PsychologyEngine.createSimulationHysteresisState();

  const display1 = PsychologyEngine.applySimulationHysteresis(cache1, week1Date, hysteresis);
  const frozen1 = PsychologyEngine.mergeFrozenPsychologyRegions([], display1, week1Date);
  const composed1 = PsychologyEngine.composeSimulationPsychologyCache(display1, frozen1, week1Date);
  const zoneAfterWeek1 = PsychologyEngine.getPsychologyZoneAtDate(composed1, sampleDate);

  const display2 = PsychologyEngine.applySimulationHysteresis(cache2, week2Date, hysteresis);
  const frozen2 = PsychologyEngine.mergeFrozenPsychologyRegions(frozen1, display2, week2Date);
  const composed2 = PsychologyEngine.composeSimulationPsychologyCache(display2, frozen2, week2Date);
  const zoneAfterWeek2 = PsychologyEngine.getPsychologyZoneAtDate(composed2, sampleDate);

  assert.ok(zoneAfterWeek1, "week 1 should resolve a psychology zone");
  assert.equal(
    zoneAfterWeek2,
    zoneAfterWeek1,
    "historical zone must stay frozen after later weekly checkpoints"
  );
});

test("daily blend can adjust zones on walk-forward cache", () => {
  const bitcoin = loadBitcoin();
  const daily = PsychologyEngine.aggregateSeries(bitcoin, "1D");
  const asOfDate = daily[620].date;

  const blended = PsychologyEngine.buildWalkForwardPsychologyCache(bitcoin, asOfDate, {
    model: "ema",
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
    model: "ema"
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
      getBaselineCache: () => PsychologyEngine.buildUnifiedPsychologyCache(bitcoin, { model: "ema" }),
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

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
