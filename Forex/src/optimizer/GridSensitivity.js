/**
 * Aggregate grid-search results for per-parameter sensitivity charts.
 * @module optimizer/GridSensitivity
 */

/** @typedef {import('./GridSearchEngine.js').GridSearchEntry} GridSearchEntry */

/** Minimum avg trades per param bucket to plot a point. */
export const MIN_TRADES_PER_SENSITIVITY_POINT = 5;

/**
 * @typedef {Object} SensitivityPoint
 * @property {number|string} paramValue
 * @property {number} winRate
 * @property {number} expectancy
 * @property {number} avgTrades
 * @property {number} sampleCount
 */

/**
 * Param keys whose values differ across grid entries.
 * @param {GridSearchEntry[]} entries
 * @returns {string[]}
 */
export function getVaryingParamKeys(entries) {
  if (!entries.length) return [];

  /** @type {Set<string>} */
  const keys = new Set();
  for (const entry of entries) {
    for (const key of Object.keys(entry.params)) keys.add(key);
  }

  /** @type {string[]} */
  const varying = [];
  for (const key of keys) {
    const values = new Set(entries.map((e) => String(e.params[key])));
    if (values.size > 1) varying.push(key);
  }

  return varying.sort();
}

/**
 * @param {number[]} values
 * @returns {number}
 */
function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * @param {string|number} raw
 * @returns {number|string}
 */
function parseParamValue(raw) {
  const num = Number(raw);
  return Number.isNaN(num) ? raw : num;
}

/**
 * Build averaged WR / expectancy series for one parameter.
 * @param {GridSearchEntry[]} entries
 * @param {string} paramKey
 * @param {number} [minTrades]
 * @returns {SensitivityPoint[]}
 */
export function buildSensitivitySeries(entries, paramKey, minTrades = MIN_TRADES_PER_SENSITIVITY_POINT) {
  /** @type {Map<string, { winRate: number[], expectancy: number[], trades: number[] }>} */
  const groups = new Map();

  for (const entry of entries) {
    const value = entry.params[paramKey];
    if (value === undefined || value === null) continue;

    const key = String(value);
    if (!groups.has(key)) {
      groups.set(key, { winRate: [], expectancy: [], trades: [] });
    }

    const bucket = groups.get(key);
    const { stats } = entry.result;
    bucket.winRate.push(stats.winRate);
    bucket.expectancy.push(stats.expectancy);
    bucket.trades.push(stats.totalTrades);
  }

  /** @type {SensitivityPoint[]} */
  const points = [];

  for (const [key, bucket] of groups) {
    if (!bucket.winRate.length) continue;

    const avgTrades = average(bucket.trades);
    if (avgTrades < minTrades) continue;

    points.push({
      paramValue: parseParamValue(key),
      winRate: average(bucket.winRate),
      expectancy: average(bucket.expectancy),
      avgTrades: Math.round(avgTrades),
      sampleCount: bucket.winRate.length,
    });
  }

  points.sort((a, b) => {
    if (typeof a.paramValue === 'number' && typeof b.paramValue === 'number') {
      return a.paramValue - b.paramValue;
    }
    return String(a.paramValue).localeCompare(String(b.paramValue));
  });

  return points;
}
