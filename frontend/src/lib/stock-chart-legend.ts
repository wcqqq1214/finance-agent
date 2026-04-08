import type { OHLCRecord, StockInfo } from "./types";

type ChartTime =
  | number
  | string
  | { year: number; month: number; day: number }
  | null
  | undefined;

interface ResolveLegendChangeMetricsParams {
  assetType: "crypto" | "stocks";
  hoveredTime: ChartTime;
  latestTime: ChartTime;
  ohlc: Pick<OHLCRecord, "open" | "close">;
  liveQuote?: StockInfo | null;
  currentUsMarketDate: string;
}

export interface LegendChangeMetrics {
  label: string | null;
  percent: number;
  isUp: boolean;
}

function isBusinessDay(
  time: ChartTime,
): time is { year: number; month: number; day: number } {
  return (
    typeof time === "object" &&
    time !== null &&
    "year" in time &&
    "month" in time &&
    "day" in time
  );
}

function areTimesEqual(left: ChartTime, right: ChartTime): boolean {
  if (left === right) {
    return true;
  }
  if (isBusinessDay(left) && isBusinessDay(right)) {
    return (
      left.year === right.year &&
      left.month === right.month &&
      left.day === right.day
    );
  }
  return false;
}

export function resolveLegendChangeMetrics({
  assetType,
  hoveredTime,
  latestTime,
  ohlc,
  liveQuote,
  currentUsMarketDate,
}: ResolveLegendChangeMetricsParams): LegendChangeMetrics {
  const candleChange = ohlc.close - ohlc.open;
  const candlePercent = ohlc.open === 0 ? 0 : (candleChange / ohlc.open) * 100;
  const candleMetrics: LegendChangeMetrics = {
    label: null,
    percent: candlePercent,
    isUp: candleChange >= 0,
  };

  const latestDateString =
    typeof latestTime === "string"
      ? latestTime.split("T")[0]
      : isBusinessDay(latestTime)
        ? `${latestTime.year}-${String(latestTime.month).padStart(2, "0")}-${String(latestTime.day).padStart(2, "0")}`
        : null;

  if (
    assetType !== "stocks" ||
    !areTimesEqual(hoveredTime, latestTime) ||
    latestDateString !== currentUsMarketDate ||
    liveQuote?.changePercent === undefined
  ) {
    return candleMetrics;
  }

  const quoteDirection = liveQuote.change ?? liveQuote.changePercent;
  return {
    label: "Day",
    percent: liveQuote.changePercent,
    isUp: quoteDirection >= 0,
  };
}
