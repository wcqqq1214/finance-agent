# Remove Squash Merge Stub Design

## Problem

The auto-dev workflow has already standardized on `ff_merge_to_wcq.sh` as the only integration entrypoint, but the repository still ships a retired `squash_merge_to_wcq.sh` compatibility stub plus a test that locks in that redirect behavior.

That leaves two problems:

- the tree still suggests the old script name is intentionally supported
- the test suite still treats transitional compatibility as part of the current contract

## Goal

Remove the obsolete squash-merge compatibility layer so the repository presents `ff_merge_to_wcq.sh` as the sole supported integration script.

## Scope

In scope:

- delete `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh`
- replace the redirect-style script contract test with a contract that the legacy script path no longer exists
- verify there are no remaining references to `squash_merge_to_wcq.sh` in the current workflow-facing repository files

Out of scope:

- rewriting historical design documents that describe the transition from squash merge to fast-forward integration
- changing the behavior or interface of `ff_merge_to_wcq.sh`
- broader workflow refactors unrelated to the retired stub

## Approach

Keep the cleanup intentionally small and explicit:

1. Add a failing test in `tests/scripts/test_auto_dev_workflow.py` asserting that `_script_path("squash_merge_to_wcq.sh")` does not exist.
2. Verify that test fails while the stub file is still present.
3. Delete the retired script file.
4. Remove the redirect-specific test that expected a nonzero exit and "Use ff_merge_to_wcq.sh instead." in stderr.
5. Re-run the focused script test file and a repository search for `squash_merge_to_wcq.sh`.

## Testing Strategy

- Red/green on the focused cleanup test in `tests/scripts/test_auto_dev_workflow.py`
- Run the full `tests/scripts/test_auto_dev_workflow.py` file after the cleanup
- Run a repository search to confirm current workflow-facing files no longer reference `squash_merge_to_wcq.sh`

## Risks and Mitigations

- Risk: a current workflow file still references the legacy name
  - Mitigation: run a final repository search and treat any hit as a blocker

- Risk: deleting the stub removes the friendly redirect for manual callers
  - Mitigation: accept this intentionally; the repository contract is being tightened so unsupported entrypoints fail by absence rather than by redirect

## Acceptance Criteria

- `.agents/skills/auto-dev-workflow/scripts/squash_merge_to_wcq.sh` is absent from the repository
- `tests/scripts/test_auto_dev_workflow.py` no longer encodes redirect behavior for the retired script
- focused script tests pass after the cleanup
- repository search finds no current workflow-facing references to `squash_merge_to_wcq.sh`
