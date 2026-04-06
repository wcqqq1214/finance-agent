# Baseline Test Fixes Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a clean baseline in the isolated worktree by fixing the default database bootstrap assumptions and updating `crypto_klines` tests to match the current API contract.

**Architecture:** Keep production behavior explicit: database schema initialization stays in `init_db()`, while `get_conn()` creates missing parent directories for filesystem-backed SQLite paths so isolated databases can be opened reliably in fresh worktrees. Before relying on that in tests, confirm `get_conn()` still has the lazy fallback form `db_path: Optional[Path] = None` so monkeypatching `schema.DEFAULT_DB_PATH` is effective; if that signature ever changes to a bound default, pass `db_path` explicitly instead of patching the constant. In the database tests that currently assume a ready-made default DB, patch `app.database.schema.DEFAULT_DB_PATH` via the imported module object and call `init_db(db_path)` locally. Separately, update `crypto_klines` tests so they lock the actual public API contract: unsupported public `interval=1m` returns `400`, supported intervals include `15m/1h/4h/1d/1w/1M`, supported intraday intervals internally map to source bar `1m`, and overlapping cache rows never replace DB rows.

**Tech Stack:** Python 3.13, pytest, FastAPI TestClient, SQLite, Ruff

---

## Chunk 1: Default Database Bootstrap

### Task 1: Make default SQLite paths work in isolated worktrees

**Files:**
- Modify: `app/database/schema.py`
- Modify: `tests/database/test_crypto_ohlc.py`
- Modify: `tests/database/test_schema.py`
- Test: `tests/database/test_schema.py`
- Test: `tests/database/test_crypto_ohlc.py`

- [ ] **Step 1: Reproduce the current failures in the worktree**

Run: `uv run pytest tests/database/test_schema.py tests/database/test_crypto_ohlc.py -q`
Expected: `tests/database/test_schema.py` currently passes, while `tests/database/test_crypto_ohlc.py` errors in fixture setup with `sqlite3.OperationalError: unable to open database file` from `app/database/schema.py:get_conn()`.

- [ ] **Step 2: Confirm the helper signatures before patching tests**

Read: `app/database/schema.py`
Confirm:
- `get_conn()` is defined with `db_path: Optional[Path] = None`
- `init_db()` accepts an explicit `db_path`
- There is no import-time bound default path that would bypass a runtime monkeypatch

- [ ] **Step 3: Write the failing regression tests**

```python
def test_init_db_creates_missing_parent_directories(tmp_path):
    db_path = tmp_path / "nested" / "db" / "finance_schema.db"
    init_db(db_path)
    assert db_path.exists()
```

- [ ] **Step 4: Run tests to verify they fail for the expected reasons**

Run: `uv run pytest tests/database/test_schema.py tests/database/test_crypto_ohlc.py -q`
Expected: FAIL because `init_db()` cannot open nested DB paths in a fresh worktree and `tests/database/test_crypto_ohlc.py` still assumes an already-initialized default database.

- [ ] **Step 5: Implement the minimal bootstrap fix**

```python
if str(path) != ":memory:" and not str(path).startswith("file:"):
    path.parent.mkdir(parents=True, exist_ok=True)
```

```python
@pytest.fixture(autouse=True)
def isolated_crypto_db(tmp_path, monkeypatch):
    import app.database.schema as schema

    db_path = tmp_path / "finance_data.db"
    monkeypatch.setattr(schema, "DEFAULT_DB_PATH", db_path)
    init_db(db_path)
```

- [ ] **Step 6: Run focused tests to verify the fix**

Run: `uv run pytest tests/database/test_schema.py tests/database/test_crypto_ohlc.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/database/schema.py tests/database/test_schema.py tests/database/test_crypto_ohlc.py
git commit -m "fix(database): support isolated sqlite paths in worktrees"
```

## Chunk 2: Klines Test Contract Alignment

### Task 2: Update `crypto_klines` tests to the supported interval contract

**Files:**
- Modify: `tests/api/test_crypto_klines.py`
- Test: `tests/api/test_crypto_klines.py`

- [ ] **Step 1: Reproduce the current stale-contract failures**

Run: `uv run pytest tests/api/test_crypto_klines.py -q`
Expected: FAIL because the file still sends unsupported public `interval=1m` requests and still assumes overlapping hot-cache rows override DB rows.

- [ ] **Step 2: Verify the current contract in implementation before editing assertions**

Read: `app/api/routes/crypto_klines.py`
Confirm:
- Public API accepts only `15m`, `1h`, `4h`, `1d`, `1w`, `1M`
- Unsupported `interval` values return `400` with `detail` starting `Invalid interval`
- `15m`, `1h`, `4h` map to source bar `1m`
- Merge precedence is DB-first on overlap
- Confirm the cold-data call still passes `bar=` as a kwarg before asserting on `mock_cold.call_args.kwargs["bar"]`; if not, assert using the actual current call shape instead

- [ ] **Step 3: Update failing tests to encode the current contract**

Current contract to encode:
- Public API supports only `15m`, `1h`, `4h`, `1d`, `1w`, `1M`
- `15m`, `1h`, `4h` requests internally fetch source bar `1m` and aggregate
- Merge precedence is DB-first: hot cache only appends data after the DB tail; overlapping timestamps keep DB data
- Unsupported public `interval=1m` returns `400` and an `Invalid interval` detail message

```python
response = client.get("/api/crypto/klines?symbol=BTCUSDT&interval=15m")
```

```python
assert data[0]["close"] == 100.5  # DB-first merge keeps cold data on overlap
```

```python
response = client.get("/api/crypto/klines?symbol=BTCUSDT&interval=1m")
assert response.status_code == 400
assert response.json()["detail"].startswith("Invalid interval")
```

- [ ] **Step 4: Run the test file to verify the updated expectations still fail until all stale assumptions are removed**

Run: `uv run pytest tests/api/test_crypto_klines.py -q`
Expected: FAIL while the file still mixes unsupported `1m` requests or stale "hot data wins" assertions.

- [ ] **Step 5: Finish the minimal test-only alignment**

```python
assert mock_cold.call_args.kwargs["bar"] == "1m"
assert response.status_code == 200
```

Assert only stable response fields: `timestamp`, `date`, `open`, `high`, `low`, `close`, `volume`.
Use timestamps that produce stable, non-collapsing assertions for the requested supported interval.

- [ ] **Step 6: Run focused tests**

Run: `uv run pytest tests/api/test_crypto_klines.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/api/test_crypto_klines.py
git commit -m "test(api): align crypto klines coverage with current contract"
```

## Chunk 3: Regression Verification

### Task 3: Verify the repaired baseline slices together

**Files:**
- Test: `tests/database/test_schema.py`
- Test: `tests/database/test_crypto_ohlc.py`
- Test: `tests/api/test_crypto_klines.py`

- [ ] **Step 1: Run the targeted regression suite**

Run: `uv run pytest tests/database/test_schema.py tests/database/test_crypto_ohlc.py tests/api/test_crypto_klines.py -q`
Expected: PASS

- [ ] **Step 2: Run formatting and lint checks on touched Python files**

Run: `uv run ruff check app/database/schema.py tests/database/test_schema.py tests/database/test_crypto_ohlc.py tests/api/test_crypto_klines.py`
Expected: PASS

Run: `uv run ruff format --check app/database/schema.py tests/database/test_schema.py tests/database/test_crypto_ohlc.py tests/api/test_crypto_klines.py`
Expected: PASS

- [ ] **Step 3: Review the diff for unintended scope**

Run: `git diff -- app/database/schema.py tests/database/test_schema.py tests/database/test_crypto_ohlc.py tests/api/test_crypto_klines.py`
Expected: Only the database bootstrap fix and test contract alignment are present.
