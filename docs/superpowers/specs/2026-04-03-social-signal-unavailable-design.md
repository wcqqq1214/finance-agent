# Social Signal Unavailable Design

**Problem**

When Reddit ingestion captures no usable coverage, the current pipeline still emits a neutral social sentiment summary. The CIO layer can then over-interpret missing Reddit data as evidence of retail disinterest or capitulation, which is not justified because Reddit coverage may be missing, sparse, or noisy.

**Goal**

When Reddit coverage is unavailable, the social module must explicitly mark the signal as unavailable, and the CIO synthesis must exclude that signal from retail sentiment judgment.

**Design**

## Scope

- Fix the structured social report so zero-coverage Reddit ingestion is represented as unavailable rather than neutral sentiment.
- Surface the unavailable state in the markdown report that the CIO consumes.
- Add CIO prompt constraints so missing Reddit coverage cannot be converted into a retail sentiment conclusion.

## Behavior

1. If Reddit ingestion yields no usable coverage for the last 24 hours, the social report must:
   - mark the social signal as unavailable
   - state that it is excluded from retail sentiment judgment
   - avoid keywords or summaries that look like a real sentiment read
2. If Reddit coverage exists, the social report keeps the existing sentiment-analysis path.
3. The CIO prompt must explicitly forbid inferring retail capitulation, disinterest, or any other retail sentiment from missing or sparse Reddit discussion.

## Data Contract Changes

- Extend the social NLP/report payload with:
  - `signal_available: bool`
  - `coverage_status: "available" | "unavailable"`
- Allow the social sentiment label to carry `unavailable` for no-signal cases so downstream consumers can distinguish it from a true neutral reading.

## Files

- Modify `app/social/nlp_tools.py` to produce explicit unavailable payloads for empty Reddit input.
- Modify `app/social/generate_report.py` to override zero post/comment coverage to unavailable and expose the state in markdown.
- Modify `app/graph_multi.py` to reinforce exclusion rules in CIO synthesis and fallback social formatting.
- Add regression tests in `tests/test_social_generate_report.py` and `tests/test_multi_agent_graph.py`.

## Risks

- Downstream consumers may have assumed all social sentiments are one of the five original labels. Tests must cover the new `unavailable` state.
- The CIO still uses an LLM, so the prompt and markdown report both need the unavailable rule to reduce over-inference.

## Test Strategy

- Red-green test for zero-coverage social reports producing unavailable output.
- Red-green test for CIO prompt context including the unavailable signal and explicit exclusion rule.
