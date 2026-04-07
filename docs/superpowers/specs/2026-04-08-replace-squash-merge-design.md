# Replace Squash Merge Design

**Problem**

The repository-local auto-dev workflow currently requires task-sized commits on the feature branch, but then discards that task history by funneling the branch through `squash_merge_to_wcq.sh`. That makes `wcq` lose the exact reviewable and bisectable commits the workflow just forced the agent to create.

**Goal**

Keep the existing isolated-worktree workflow and drift protection, but replace the final squash step with a verified fast-forward integration that preserves the feature branch's task commits in `wcq`.

**Design**

## Scope

- Replace the final integration script and all workflow references that currently require a squash merge.
- Preserve the current preconditions:
  - integration starts from clean local `wcq`
  - `wcq` must still match the recorded `BASE_SHA`
  - the feature worktree must be clean
- Preserve the existing final-gate behavior: verify the exact commit that will land on `wcq` before updating `wcq`.
- Keep local cleanup behavior: remove the feature worktree and delete the feature branch after successful integration.

## Non-Goals

- Do not change the task-level commit workflow.
- Do not add remote push behavior.
- Do not relax the current drift guard by auto-rebasing when `wcq` has moved.
- Do not rewrite older feature history during integration.

## Integration Strategy

An early idea was `rebase + ff`, but that is unnecessary in this repository. The workflow already refuses drift by checking that local `wcq` still equals `BASE_SHA`. If that guard passes, the feature branch is expected to be a descendant of `wcq`, so a plain fast-forward is enough.

That gives the desired result with less risk:

1. Validate that `wcq` is still at `BASE_SHA`.
2. Validate that the feature worktree path is a real worktree on the expected branch and is clean.
3. Create a temporary detached integration worktree at the feature branch tip.
4. Run the existing `run_final_gate.sh --base-sha <BASE_SHA>` inside that detached worktree.
5. If the gate passes, update local `wcq` with `git merge --ff-only <branch>`.
6. Remove the feature worktree and delete the feature branch locally.

This preserves the exact task commits that were reviewed on the feature branch while keeping `wcq` linear.

## Script Contract

Add `ff_merge_to_wcq.sh` as the new canonical integration script.

### Inputs

- `--branch <feature-branch>`
- `--base-sha <sha>`
- `--worktree <path>`

`--message` is removed because no integration commit is created during a fast-forward.

### Required behavior

- Fail if run outside clean `wcq`.
- Fail if `wcq` drifted from `BASE_SHA`.
- Fail if the supplied worktree path is not a worktree for the target branch.
- Fail if the feature worktree is dirty.
- Fail if `wcq` cannot be fast-forwarded to the feature branch.
- Run the final gate against the exact feature-branch commit in a temporary detached worktree before updating `wcq`.
- On success, fast-forward `wcq`, remove the feature worktree, and delete the feature branch.

## Testing Strategy

Update `tests/scripts/test_auto_dev_workflow.py` so the script-level contract is enforced by tests:

- drifted-base refusal still fails
- invalid worktree path still fails
- successful integration fast-forwards and cleans up
- non-fast-forward integration fails with a clear message
- old squash-only expectations, such as synthesized merge messages, are removed

The tests should continue using temporary repos and stubbed final-gate scripts so they stay deterministic and fast.

## Documentation Changes

Update every workflow-facing reference from "squash merge" to "fast-forward integration":

- `.agents/skills/auto-dev-workflow/SKILL.md`
- `.agents/skills/auto-dev-workflow/references/workflow-contract.md`
- `.agents/skills/auto-dev-workflow/references/claude-code-adapter.md`
- `.agents/skills/auto-dev-workflow/references/gstack-adapter.md`
- `.agents/skills/auto-dev-workflow/agents/openai.yaml`

The language should make two things explicit:

1. task commits are preserved in `wcq`
2. drift is still a hard stop rather than an implicit rebase

## Compatibility Transition

Keep `squash_merge_to_wcq.sh` for one transition cycle as a compatibility stub that exits nonzero and tells callers to use `ff_merge_to_wcq.sh`.

That keeps manual callers from silently running outdated semantics while still making the new script name explicit across the repository.

## Risks and Mitigations

- **Risk:** the feature branch might not be a descendant of `wcq` even when the branch name/worktree look valid.
  - **Mitigation:** rely on `git merge --ff-only` as the authoritative safety gate and report a specific fast-forward failure.
- **Risk:** removing `--message` breaks callers that still pass it.
  - **Mitigation:** update every in-repo reference and test to the new interface in the same change, and make the legacy script fail with a redirect message.
- **Risk:** preserving all task commits also preserves spec/plan commits.
  - **Mitigation:** accept this as intentional workflow history; it is a direct consequence of choosing traceable branch history over squash compression.
