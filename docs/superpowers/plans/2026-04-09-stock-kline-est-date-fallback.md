# Stock K-Line EST Fallback Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure stock K-line responses include the latest daily candle based on America/New_York by switching refreshes to MCP and adding a read-time freshness fallback.

**Architecture:** The backend keeps daily stock persistence and response generation in sync around a shared America/New_York market-date rule. The updater writes latest daily rows through MCP, and the OHLC route heals stale database results by fetching and merging newer rows when the DB lags.

**Tech Stack:** FastAPI, Python 3.13, uv, pytest, Ruff, MCP market-data client

---

## Chunk 1: Stock updater MCP migration

### Task 1: Add failing stock updater regression coverage

**Files:**
- Modify: `tests/services/test_stock_updater.py`
- Modify: `app/services/stock_updater.py`

- [ ] **Step 1: Write the failing test**

Add a test that patches `call_get_stock_history` and asserts the updater-side helper returns normalized daily rows without calling `yfinance`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_stock_updater.py -q`
Expected: FAIL because the MCP-backed helper/update path does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Introduce a recent-history MCP helper in `app/services/stock_updater.py` and route `update_stocks_intraday_sync()` through it.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_stock_updater.py -q`
Expected: PASS

## Chunk 2: OHLC route freshness fallback

### Task 2: Add failing OHLC route regression coverage

**Files:**
- Create: `tests/api/test_stock_ohlc_route.py`
- Modify: `app/api/routes/ohlc.py`

- [ ] **Step 1: Write the failing test**

Add tests covering:
- EST market-date helper behavior
- stale DB rows healed by MCP-fetched April 8 row
- deduplication when the fallback returns a date already in the DB result

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_stock_ohlc_route.py -q`
Expected: FAIL because the fallback/merge helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add route helpers to compute the current America/New_York date, fetch/merge newer daily rows from MCP, optionally heal the DB with overwrite upserts, and return the combined daily response.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_stock_ohlc_route.py -q`
Expected: PASS

## Chunk 3: Scoped verification

### Task 3: Verify the full bugfix slice

**Files:**
- Modify: `app/services/stock_updater.py`
- Modify: `app/api/routes/ohlc.py`
- Modify: `tests/services/test_stock_updater.py`
- Create: `tests/api/test_stock_ohlc_route.py`

- [ ] **Step 1: Run focused backend tests**

Run: `uv run pytest tests/services/test_stock_updater.py tests/api/test_stock_ohlc_route.py tests/test_stock_routes.py -q`
Expected: PASS

- [ ] **Step 2: Run scoped lint and format checks**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha 8e602f07133ca0330f3246b6a67054702e22ab2d --diff-target worktree --cmd 'uv run pytest tests/services/test_stock_updater.py tests/api/test_stock_ohlc_route.py tests/test_stock_routes.py -q'`
Expected: PASS

- [ ] **Step 3: Run final gate for changed files**

Run: `bash .agents/skills/auto-dev-workflow/scripts/run_final_gate.sh --base-sha 8e602f07133ca0330f3246b6a67054702e22ab2d`
Expected: PASS once the new regression file is present and all changed non-integration tests are green.
