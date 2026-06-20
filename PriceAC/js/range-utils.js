/* Pure helpers for calendar-based visible range filtering (unit-testable). */
var RangeUtils = (() => {
  const RANGE_DAY_COUNT = {
    "1M": 30,
    "3M": 90,
    "1Y": 365,
    "5Y": 365 * 5,
    "10Y": 365 * 10
  };

  const MS_PER_DAY = 86400000;
  const MIN_VISIBLE_POINTS = 2;

  const parseDateMs = (dateStr) => new Date(`${dateStr}T12:00:00Z`).getTime();

  const filterSeriesByDayRange = (dailySeries, dayCount) => {
    if (!dailySeries?.length || dayCount < 1) {
      return [];
    }

    const endMs = parseDateMs(dailySeries[dailySeries.length - 1].date);
    const startMs = endMs - (dayCount - 1) * MS_PER_DAY;

    return dailySeries.filter((point) => parseDateMs(point.date) >= startMs);
  };

  const ensureMinimumPoints = (inRange, dailySeries, dayCount) => {
    if (inRange.length >= MIN_VISIBLE_POINTS || !dailySeries.length) {
      return inRange;
    }

    const fallbackCount = Math.min(
      Math.max(dayCount, MIN_VISIBLE_POINTS),
      dailySeries.length
    );

    return dailySeries.slice(-fallbackCount);
  };

  const buildVisibleDailySlice = (dailySeries, rangeKey) => {
    const dayCount = RANGE_DAY_COUNT[rangeKey] ?? RANGE_DAY_COUNT["1M"];
    const inRange = filterSeriesByDayRange(dailySeries, dayCount);
    return ensureMinimumPoints(inRange, dailySeries, dayCount);
  };

  const buildVisibleSeries = (fullSeries, rangeKey, interval, aggregateSeries) => {
    const daily = aggregateSeries(fullSeries, "1D");

    if (!daily.length) {
      return [];
    }

    let slice = buildVisibleDailySlice(daily, rangeKey);
    let visible = aggregateSeries(slice, interval);

    if (interval !== "1D" && visible.length < MIN_VISIBLE_POINTS) {
      const stepDays = interval === "1W" ? 7 : 31;

      while (visible.length < MIN_VISIBLE_POINTS && slice.length < daily.length) {
        const nextLength = Math.min(slice.length + stepDays, daily.length);
        slice = daily.slice(-nextLength);
        visible = aggregateSeries(slice, interval);
      }
    }

    return visible;
  };

  const getVisibleSpanDays = (visibleSeries) => {
    if (!visibleSeries?.length) {
      return 0;
    }

    const start = parseDateMs(visibleSeries[0].date);
    const end = parseDateMs(visibleSeries[visibleSeries.length - 1].date);
    return Math.round((end - start) / MS_PER_DAY) + 1;
  };

  const dedupeByDate = (series) => {
    const seen = new Set();
    return series.filter((point) => {
      if (!point?.date || seen.has(point.date)) {
        return false;
      }

      seen.add(point.date);
      return true;
    });
  };

  const sortSeriesByDate = (series) => [...(series || [])].sort(
    (left, right) => left.date.localeCompare(right.date)
  );

  const sanitizeSeries = (series) => sortSeriesByDate(dedupeByDate(series));

  const isValidRangeKey = (rangeKey) => Object.prototype.hasOwnProperty.call(RANGE_DAY_COUNT, rangeKey);

  return {
    RANGE_DAY_COUNT,
    MIN_VISIBLE_POINTS,
    parseDateMs,
    filterSeriesByDayRange,
    ensureMinimumPoints,
    buildVisibleDailySlice,
    buildVisibleSeries,
    getVisibleSpanDays,
    dedupeByDate,
    sortSeriesByDate,
    sanitizeSeries,
    isValidRangeKey
  };
})();
