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
  fetch: global.fetch
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

const RANGE_KEYS = ["1D", "1W", "1M", "3M", "1Y", "5Y", "10Y"];
const INTERVAL_KEYS = ["1D", "1W", "1M"];

console.log("PriceAC tests\n");

const RangeUtils = loadEngine("js/range-utils.js", "RangeUtils");
loadEngine("js/elliott.js", "ElliottEngine");
const PsychologyEngine = loadEngine("js/psychology.js", "PsychologyEngine");
const MarketDataService = loadEngine("js/market-data.js", "MarketDataService");

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

      assert.equal(aligned.daily.length, visible.length, `${rangeKey}/${intervalKey} daily rsi length`);
      assert.equal(aligned.weekly.length, visible.length, `${rangeKey}/${intervalKey} weekly rsi length`);
      assert.equal(aligned.monthly.length, visible.length, `${rangeKey}/${intervalKey} monthly rsi length`);

      aligned.daily.forEach((point, index) => {
        assert.equal(point.date, visible[index].date);
        assert.ok(point.value >= 0 && point.value <= 100);
      });
    });
  });
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

test("psychology cache works for gold dataset", () => {
  const gold = loadGold();
  const cache = PsychologyEngine.buildPsychologyCache(gold);
  assert.ok(cache, "gold cache should build");
  assert.ok(cache.weekCount >= 50);
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
  overlay.markers.forEach((marker) => {
    assert.ok(marker.text);
    assert.ok(marker.time >= visible[0].date && marker.time <= visible[visible.length - 1].date);
  });
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
