/* Fetch latest daily quotes (Yahoo Finance) and merge into local series + localStorage patches. */
var MarketDataService = (() => {
  const symbols = {
    bitcoin: "BTC-USD",
    gold: "GC=F"
  };

  const PATCH_PREFIX = "priceac.market.patch.v1.";

  const roundPrice = (value) => Math.round(value * 100) / 100;

  const normalizePoint = (point) => {
    const close = point.close ?? point.price;
    return {
      date: point.date,
      open: roundPrice(point.open ?? close),
      high: roundPrice(point.high ?? close),
      low: roundPrice(point.low ?? close),
      close: roundPrice(close),
      price: roundPrice(close)
    };
  };

  const mergeSeries = (baseSeries, incomingSeries) => {
    const byDate = new Map();

    (baseSeries || []).forEach((point) => {
      byDate.set(point.date, normalizePoint(point));
    });

    (incomingSeries || []).forEach((point) => {
      byDate.set(point.date, normalizePoint(point));
    });

    return Array.from(byDate.values()).sort((left, right) => left.date.localeCompare(right.date));
  };

  const loadPatches = (asset) => {
    try {
      const raw = localStorage.getItem(`${PATCH_PREFIX}${asset}`);
      return raw ? JSON.parse(raw) : [];
    } catch (error) {
      console.warn("Không đọc được bản vá giá", error);
      return [];
    }
  };

  const savePatches = (asset, patches) => {
    try {
      localStorage.setItem(`${PATCH_PREFIX}${asset}`, JSON.stringify(patches));
    } catch (error) {
      console.warn("Không lưu được bản vá giá", error);
    }
  };

  const applyPatches = (asset, baseSeries) => mergeSeries(baseSeries, loadPatches(asset));

  const parseYahooSeries = (payload) => {
    const result = payload?.chart?.result?.[0];
    if (!result) {
      return [];
    }

    const timestamps = result.timestamp || [];
    const quote = result.indicators?.quote?.[0] || {};
    const opens = quote.open || [];
    const highs = quote.high || [];
    const lows = quote.low || [];
    const closes = quote.close || [];

    return timestamps
      .map((timestamp, index) => {
        const price = closes[index];
        if (!Number.isFinite(price)) {
          return null;
        }

        return normalizePoint({
          date: new Date(timestamp * 1000).toISOString().slice(0, 10),
          open: opens[index],
          high: highs[index],
          low: lows[index],
          price
        });
      })
      .filter(Boolean);
  };

  const fetchYahooDaily = async (symbol, period1, period2) => {
    const params = new URLSearchParams({
      period1: String(period1),
      period2: String(period2),
      interval: "1d",
      events: "history"
    });
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${params}`;

    const response = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 MarketPsychologyMap/1.0"
      }
    });

    if (!response.ok) {
      throw new Error(`Yahoo Finance ${response.status}`);
    }

    const payload = await response.json();
    const error = payload?.chart?.error;

    if (error) {
      throw new Error(error.description || error.code || "Yahoo API error");
    }

    return parseYahooSeries(payload);
  };

  const fetchLatestForAsset = async (asset, currentSeries) => {
    const symbol = symbols[asset];
    if (!symbol) {
      throw new Error(`Không hỗ trợ tài sản: ${asset}`);
    }

    const lastDate = currentSeries.at(-1)?.date;
    const period2 = Math.floor(Date.now() / 1000);
    const period1 = lastDate
      ? Math.floor(new Date(`${lastDate}T00:00:00Z`).getTime() / 1000) - 14 * 86400
      : period2 - 30 * 86400;

    return fetchYahooDaily(symbol, period1, period2);
  };

  const updateAsset = async (asset, currentSeries) => {
    const fetched = await fetchLatestForAsset(asset, currentSeries);

    if (!fetched.length) {
      throw new Error("Không có giá mới");
    }

    const merged = mergeSeries(currentSeries, fetched);
    const patches = mergeSeries(loadPatches(asset), fetched);
    savePatches(asset, patches);

    return {
      series: merged,
      added: Math.max(merged.length - currentSeries.length, 0),
      updatedTo: merged.at(-1)?.date,
      fetchedCount: fetched.length
    };
  };

  return {
    symbols,
    mergeSeries,
    applyPatches,
    fetchLatestForAsset,
    updateAsset,
    loadPatches,
    savePatches
  };
})();
