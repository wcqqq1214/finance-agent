# Stock Chart Matches Card Quote Design

## Problem

The stock card and K-line chart can temporarily show different "latest prices" even when both are correct within their own refresh cycle. The root cause is that:

- `AssetSelector` fetches quote cards independently.
- `KLineChart` fetches OHLC data independently.
- The two requests complete at different times and do not share a synchronized quote snapshot.

The result is a visible mismatch between the selected stock card price and the chart's latest candle close.

## Goal

Make the selected stock K-line chart use the exact same live quote value currently displayed in the selected stock card, so the latest displayed chart price matches the card price.

## Approach

- Lift the selected stock's quote into `frontend/src/app/page.tsx`.
- Extend `AssetSelector` to report the currently selected stock quote upward whenever the selected asset or stock quotes change.
- Extend `KLineChart` to accept that live quote prop and overlay it onto the last stock daily bar for display purposes.

## Scope

- `frontend/src/app/page.tsx`
- `frontend/src/components/asset/AssetSelector.tsx`
- `frontend/src/components/chart/KLineChart.tsx`
- matching lightweight source-based frontend tests
