/* Fetches 10 years of daily market data from Yahoo Finance into /data JSON files. */
const fs = require("fs");
const path = require("path");

const assets = [
  {
    key: "bitcoin",
    symbol: "BTC-USD",
    output: "bitcoin.json"
  },
  {
    key: "gold",
    symbol: "GC=F",
    output: "gold.json"
  }
];

const dataDir = path.join(__dirname, "..", "data");
const endDate = new Date();
const startDate = new Date(endDate);
startDate.setUTCFullYear(endDate.getUTCFullYear() - 10);

const toUnixSeconds = (date) => Math.floor(date.getTime() / 1000);

const yahooChartUrl = (symbol) => {
  const params = new URLSearchParams({
    period1: String(toUnixSeconds(startDate)),
    period2: String(toUnixSeconds(endDate)),
    interval: "1d",
    events: "history"
  });

  return `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${params}`;
};

const toDateKey = (timestamp) => new Date(timestamp * 1000).toISOString().slice(0, 10);

const roundPrice = (value) => Math.round(value * 100) / 100;

const normalizeSeries = (result) => {
  const timestamps = result.timestamp || [];
  const quote = result.indicators && result.indicators.quote && result.indicators.quote[0];
  const opens = quote && quote.open ? quote.open : [];
  const highs = quote && quote.high ? quote.high : [];
  const lows = quote && quote.low ? quote.low : [];
  const closes = quote && quote.close ? quote.close : [];

  return timestamps
    .map((timestamp, index) => ({
      date: toDateKey(timestamp),
      open: opens[index],
      high: highs[index],
      low: lows[index],
      price: closes[index]
    }))
    .filter((point) => Number.isFinite(point.price))
    .map((point) => ({
      date: point.date,
      open: roundPrice(point.open ?? point.price),
      high: roundPrice(point.high ?? point.price),
      low: roundPrice(point.low ?? point.price),
      price: roundPrice(point.price)
    }));
};

const fetchAsset = async (asset) => {
  const response = await fetch(yahooChartUrl(asset.symbol), {
    headers: {
      "User-Agent": "Mozilla/5.0 MarketPsychologyMap/1.0"
    }
  });

  if (!response.ok) {
    throw new Error(`${asset.symbol} request failed with ${response.status}`);
  }

  const payload = await response.json();
  const error = payload.chart && payload.chart.error;
  if (error) {
    throw new Error(`${asset.symbol} API error: ${error.description || error.code}`);
  }

  const result = payload.chart && payload.chart.result && payload.chart.result[0];
  if (!result) {
    throw new Error(`${asset.symbol} returned no chart result`);
  }

  const series = normalizeSeries(result);
  if (!series.length) {
    throw new Error(`${asset.symbol} returned no valid prices`);
  }

  const outputPath = path.join(dataDir, asset.output);
  fs.writeFileSync(outputPath, `${JSON.stringify(series, null, 2)}\n`);

  return {
    key: asset.key,
    symbol: asset.symbol,
    count: series.length,
    from: series[0].date,
    to: series[series.length - 1].date,
    output: path.relative(path.join(__dirname, ".."), outputPath)
  };
};

const main = async () => {
  fs.mkdirSync(dataDir, { recursive: true });
  const summaries = [];

  for (const asset of assets) {
    summaries.push(await fetchAsset(asset));
  }

  summaries.forEach((summary) => {
    console.log(
      `${summary.key} (${summary.symbol}): ${summary.count} daily points, ${summary.from} to ${summary.to}, wrote ${summary.output}`
    );
  });
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
