# Volume Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a synchronized volume histogram below the K-line candlestick chart in `KLineChart.tsx`, with a floating legend that shows the volume value on crosshair hover.

**Architecture:** Single `lightweight-charts` chart instance with two price scales — `'right'` for the candlestick (top 75–80%) and `'volume'` for the histogram (bottom 20–25%). A `legendRef` DOM node is updated directly via `subscribeCrosshairMove` to avoid React re-renders on mouse move.

**Tech Stack:** React (useRef, useEffect), lightweight-charts v5 (HistogramSeries, priceScale, subscribeCrosshairMove), Tailwind CSS

---

## File Map

| File | Change |
|------|--------|
| `frontend/src/components/chart/KLineChart.tsx` | Modify — add volume series, price scale margins, legend ref, crosshair subscription |

No new files. No other files touched.

---

### Task 1: Add `legendRef` and update JSX chart container

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx`

The current JSX renders the chart as:
```tsx
<div ref={chartContainerRef} className="flex-1" />
```

This needs to become a `relative` wrapper so the legend can be absolutely positioned inside it.

- [ ] **Step 1: Add `legendRef` to the component**

In `KLineChart.tsx`, find the existing refs block (around line 87–88):
```ts
const chartContainerRef = useRef<HTMLDivElement>(null);
const chartRef = useRef<IChartApi | null>(null);
```

Add `legendRef` immediately after:
```ts
const legendRef = useRef<HTMLDivElement>(null);
```

- [ ] **Step 2: Replace the chart container JSX**

Find (around line 391):
```tsx
<div ref={chartContainerRef} className="flex-1" />
```

Replace with:
```tsx
<div className="flex-1 relative">
  <div ref={chartContainerRef} className="absolute inset-0" />
  <div
    ref={legendRef}
    className="absolute top-2 left-2 z-10 hidden text-xs font-mono bg-background/80 px-1.5 py-0.5 rounded pointer-events-none"
  />
</div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors related to `legendRef`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat(chart): add legend ref and relative container for volume tooltip"
```

---

### Task 2: Add `HistogramSeries` import and volume series

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx`

- [ ] **Step 1: Add `HistogramSeries` to the import**

Find line 4:
```ts
import { createChart, IChartApi, CandlestickData, ISeriesApi, CandlestickSeries } from 'lightweight-charts';
```

Replace with:
```ts
import { createChart, IChartApi, CandlestickData, ISeriesApi, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
```

- [ ] **Step 2: Add `priceScaleId` to the candlestick series and apply right-scale margins**

Find the `addSeries` call (around line 230):
```ts
const series = chart.addSeries(CandlestickSeries, {
  upColor: '#22c55e',
  downColor: '#ef4444',
  wickUpColor: '#22c55e',
  wickDownColor: '#ef4444',
});
```

Replace with:
```ts
const series = chart.addSeries(CandlestickSeries, {
  upColor: '#22c55e',
  downColor: '#ef4444',
  wickUpColor: '#22c55e',
  wickDownColor: '#ef4444',
  priceScaleId: 'right',
});

chart.priceScale('right').applyOptions({
  scaleMargins: {
    top: 0.1,
    bottom: 0.25,
  },
});
```

- [ ] **Step 3: Add volume series after the candlestick series block**

Immediately after the `chart.priceScale('right').applyOptions(...)` block, add:
```ts
const volumeSeries = chart.addSeries(HistogramSeries, {
  priceScaleId: 'volume',
  priceFormat: { type: 'volume' },
});

chart.priceScale('volume').applyOptions({
  scaleMargins: {
    top: 0.8,
    bottom: 0,
  },
});
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat(chart): add volume histogram series with custom price scale"
```

---

### Task 3: Map volume data and feed it to the series

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx`

The existing data mapping loop (around line 242–264) builds `formattedData` for the candlestick series. We add a parallel `volumeData` array in the same loop.

- [ ] **Step 1: Replace the data mapping block**

Find:
```ts
const formattedData: CandlestickData[] = ohlcData.map((d) => {
  if (isIntradayData) {
    const time = Math.floor(new Date(d.date).getTime() / 1000);
    return {
      time: time as any,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    };
  } else {
    const time = d.date.split('T')[0];
    return {
      time: time as any,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    };
  }
});
```

Replace with:
```ts
const formattedData: CandlestickData[] = [];
const volumeData: { time: any; value: number; color: string }[] = [];

for (const d of ohlcData) {
  const time = isIntradayData
    ? (Math.floor(new Date(d.date).getTime() / 1000) as any)
    : (d.date.split('T')[0] as any);

  formattedData.push({ time, open: d.open, high: d.high, low: d.low, close: d.close });
  volumeData.push({
    time,
    value: d.volume,
    color: d.close >= d.open ? 'rgba(34, 197, 94, 0.6)' : 'rgba(239, 68, 68, 0.6)',
  });
}
```

- [ ] **Step 2: Feed volume data to the series**

Find:
```ts
series.setData(formattedData);
```

Add immediately after:
```ts
volumeSeries.setData(volumeData);
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat(chart): map and set volume data with per-bar color"
```

---

### Task 4: Add crosshair subscription for floating legend

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx`

- [ ] **Step 1: Add `formatVolume` helper and crosshair subscription**

Find:
```ts
series.setData(formattedData);
volumeSeries.setData(volumeData);
```

Add immediately after:
```ts
const formatVolume = (vol: number): string => {
  if (vol >= 1_000_000) return (vol / 1_000_000).toFixed(2) + 'M';
  if (vol >= 1_000) return (vol / 1_000).toFixed(2) + 'K';
  return vol.toFixed(2);
};

chart.subscribeCrosshairMove((param) => {
  const legend = legendRef.current;
  if (!legend) return;

  if (
    !param.time ||
    param.point === undefined ||
    param.point.x < 0 ||
    param.point.y < 0
  ) {
    legend.style.display = 'none';
    return;
  }

  const volData = param.seriesData.get(volumeSeries) as { value: number } | undefined;
  if (volData) {
    legend.style.display = 'block';
    legend.textContent = `Vol  ${formatVolume(volData.value)}`;
  } else {
    legend.style.display = 'none';
  }
});
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "feat(chart): add crosshair subscription for volume floating legend"
```

---

### Task 5: Manual verification checklist

Start the dev server (run this yourself in a terminal — do not run via tool):
```
cd frontend && npm run dev
```

Open the app and select a crypto asset (e.g. BTC-USD) with any time range.

- [ ] Volume bars appear in the bottom ~20% of the chart area
- [ ] Green bars correspond to up-candles, red bars to down-candles
- [ ] Moving the mouse over the chart shows `Vol  1.23K` (or similar) in the top-left corner
- [ ] Moving the mouse off the chart hides the legend
- [ ] Scrolling and zooming keeps volume bars aligned with candles
- [ ] Crosshair line spans both the candlestick and volume regions
- [ ] Switch to a stock asset — chart still works, no regression
- [ ] Switch time ranges (15M, 1H, 4H, 1D) — chart reloads correctly each time

- [ ] **Final commit if any tweaks were made during verification**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "fix(chart): volume chart manual verification tweaks"
```
