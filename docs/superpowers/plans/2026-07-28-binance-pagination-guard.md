# Implementation Plan: Binance Pagination Progress Guard

## Task 1 — Capture the regression

1. Correct the existing exact-1000-record fixture so its final timestamp equals
   `end_time`, preserving the one-request boundary assertion.
2. Add a regression test that returns the same full page twice and expects a
   descriptive `RuntimeError` after exactly two requests.
3. Run the regression test alone. It must fail before production code changes.

Verification:

```bash
uv run python -m pytest tests/services/test_binance_pagination.py::test_rejects_stale_full_page_without_progress -q
```

## Task 2 — Add the guard

1. For a non-empty full page, derive `next_start` from its final timestamp.
2. Reject a page when `next_start <= current_start`, before appending it.
3. Update the public docstring with the new `RuntimeError` condition.
4. Run the entire pagination test module and Ruff on the changed Python paths.

Verification:

```bash
uv run python -m pytest tests/services/test_binance_pagination.py -q
uv run ruff check app/services/binance_client.py tests/services/test_binance_pagination.py
uv run ruff format --check app/services/binance_client.py tests/services/test_binance_pagination.py
```

## Task 3 — Review, commit, and merge

1. Perform a targeted code review against the specification.
2. Run the workflow scoped checks and commit the isolated task.
3. Run the final gate, then fast-forward the verified branch into `wcq`.
