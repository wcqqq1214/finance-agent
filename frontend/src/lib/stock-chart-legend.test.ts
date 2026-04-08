import assert from "node:assert/strict";
import test from "node:test";

import type { OHLCRecord, StockInfo } from "./types";

async function loadModule() {
  const moduleUrl = new URL("./stock-chart-legend.ts", import.meta.url).href;
  return import(moduleUrl);
}

const latestBar: OHLCRecord = {
  date: "2026-04-08",
  open: 605.7,
  high: 629.91,
  low: 591.83,
  close: 620.425,
  volume: 22_377_485,
};

const liveQuote: StockInfo = {
  symbol: "META",
  name: "Meta Platforms Inc.",
  price: 620.425,
  change: 45.375,
  changePercent: 7.89,
};

test("latest stock market-day legend uses live quote day change percent for the newest bar", async () => {
  const { resolveLegendChangeMetrics } = await loadModule();

  const metrics = resolveLegendChangeMetrics({
    assetType: "stocks",
    hoveredTime: "2026-04-08",
    latestTime: "2026-04-08",
    ohlc: latestBar,
    liveQuote,
    currentUsMarketDate: "2026-04-08",
  });

  assert.deepEqual(metrics, {
    label: "Day",
    percent: 7.89,
    isUp: true,
  });
});

test("historical stock bars keep candle open-to-close legend percentage", async () => {
  const { resolveLegendChangeMetrics } = await loadModule();

  const metrics = resolveLegendChangeMetrics({
    assetType: "stocks",
    hoveredTime: "2026-04-07",
    latestTime: "2026-04-08",
    ohlc: latestBar,
    liveQuote,
    currentUsMarketDate: "2026-04-08",
  });

  assert.deepEqual(metrics, {
    label: null,
    percent: ((latestBar.close - latestBar.open) / latestBar.open) * 100,
    isUp: true,
  });
});
