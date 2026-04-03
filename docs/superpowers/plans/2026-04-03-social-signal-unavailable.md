# Social Signal Unavailable Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent missing Reddit coverage from being interpreted as retail sentiment in social reports and CIO recommendations.

**Architecture:** Keep the existing social-analysis flow, but add an explicit unavailable state for zero-coverage ingestion and propagate that state into the markdown report consumed by the CIO. Reinforce the same rule in the CIO system prompt so the LLM cannot infer capitulation or disinterest from absent Reddit data.

**Tech Stack:** Python 3.13, pytest, LangGraph, LangChain tools

---

## Chunk 1: Regression Tests

### Task 1: Social report unavailable state

**Files:**
- Modify: `tests/test_social_generate_report.py`
- Test: `tests/test_social_generate_report.py`

- [ ] **Step 1: Write the failing test**

```python
def test_generate_report_marks_zero_coverage_as_unavailable(...):
    ...
    assert report["signal_available"] is False
    assert report["coverage_status"] == "unavailable"
    assert report["sentiment"] == "unavailable"
    assert "excluded from retail sentiment judgment" in report["summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_social_generate_report.py -q`
Expected: FAIL because the social report still emits `neutral` and lacks unavailable-state fields.

### Task 2: CIO exclusion rule

**Files:**
- Modify: `tests/test_multi_agent_graph.py`
- Test: `tests/test_multi_agent_graph.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cio_node_includes_unavailable_social_exclusion_rule(...):
    ...
    assert "signal_available" in content
    assert "exclude" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_multi_agent_graph.py -q`
Expected: FAIL because the social markdown/prompt does not carry the unavailable-state exclusion rule.

## Chunk 2: Minimal Implementation

### Task 3: Unavailable social payload

**Files:**
- Modify: `app/social/nlp_tools.py`
- Modify: `app/social/generate_report.py`
- Test: `tests/test_social_generate_report.py`

- [ ] **Step 1: Implement the minimal unavailable payload**

```python
if no_usable_reddit_signal:
    return {
        "sentiment": "unavailable",
        "keywords": [],
        "summary": "... excluded from retail sentiment judgment ...",
        "signal_available": False,
        "coverage_status": "unavailable",
    }
```

- [ ] **Step 2: Preserve available coverage behavior**

```python
result.setdefault("signal_available", True)
result.setdefault("coverage_status", "available")
```

- [ ] **Step 3: Expose the state in social markdown**

```python
- **Signal available**: `no`
- **Coverage status**: `unavailable`
- **Interpretation**: Exclude from retail sentiment judgment.
```

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest tests/test_social_generate_report.py -q`
Expected: PASS

### Task 4: CIO synthesis guardrails

**Files:**
- Modify: `app/graph_multi.py`
- Test: `tests/test_multi_agent_graph.py`

- [ ] **Step 1: Add explicit CIO prompt constraints**

```python
"If the social report says signal_available=false or coverage_status=unavailable, "
"exclude it from retail sentiment judgment. Never infer capitulation or disinterest "
"from absent or sparse Reddit discussion."
```

- [ ] **Step 2: Include unavailable fields in fallback social formatting**

```python
f"- signal_available: {social_obj.get('signal_available')}"
f"- coverage_status: {social_obj.get('coverage_status')}"
```

- [ ] **Step 3: Run focused tests**

Run: `uv run pytest tests/test_multi_agent_graph.py -q`
Expected: PASS

## Chunk 3: Regression Verification

### Task 5: Combined verification

**Files:**
- Test: `tests/test_social_generate_report.py`
- Test: `tests/test_multi_agent_graph.py`

- [ ] **Step 1: Run the targeted regression suite**

Run: `uv run pytest tests/test_social_generate_report.py tests/test_multi_agent_graph.py -q`
Expected: PASS

- [ ] **Step 2: Review resulting diff for unintended scope**

Run: `git diff -- app/social/nlp_tools.py app/social/generate_report.py app/graph_multi.py tests/test_social_generate_report.py tests/test_multi_agent_graph.py`
Expected: Only the unavailable-state bugfix and regression coverage are present.
