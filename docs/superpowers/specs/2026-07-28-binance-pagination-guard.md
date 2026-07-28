# Binance Pagination Progress Guard

## Context

`fetch_klines_with_pagination` appends every full Binance page and advances its
cursor from the page's final timestamp. A full page whose final timestamp is
older than the request cursor leaves that cursor unchanged. Repeated stale
pages therefore append indefinitely and exhaust memory.

The existing exact-1000-record test constructs this condition: its repeated
mock page ends at `999000`, while the second request starts at `999001`.

## Goal

Make pagination fail fast when a non-empty full page cannot advance the request
cursor, while preserving successful pagination and the existing public return
type.

## Design

1. Calculate the next cursor from the final record of each full page.
2. Before the loop can reuse a cursor, verify that `next_start` is strictly
   greater than the cursor used for the request.
3. Raise a descriptive `RuntimeError` when that invariant is violated. This is
   preferable to returning partial, silently duplicated market data.
4. Update the function docstring to document this failure mode.
5. Correct the exact-page boundary fixture so it actually ends at the requested
   boundary, and add a regression test with two stale full pages that asserts
   the guard raises after the second request.

## Non-goals

- Deduplicating overlapping but still advancing pages.
- Changing Binance request semantics, retry policy, or rate limiting.
- Running the full test suite in one Python process.

## Acceptance criteria

- A stale second page causes a deterministic `RuntimeError` after two requests,
  without a third request or unbounded list growth.
- Normal single- and multi-page tests remain green.
- The targeted test file and scoped formatting/lint checks pass.
