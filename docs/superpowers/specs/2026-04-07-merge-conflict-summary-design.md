# Merge Conflict Summary Design

## Goal

When `squash_merge_to_wcq.sh` hits a squash-merge conflict in its temporary integration worktree, it should emit a structured summary of the conflicted file paths before exiting.

## Scope

- Touch only the workflow merge script and its script-level tests.
- Do not change the isolation model, merge strategy, cleanup behavior, or final-gate behavior.
- Do not add retry or auto-resolution logic.

## Design

The merge script already performs the squash merge inside a disposable integration worktree. On merge failure, it will inspect that temporary worktree for unmerged paths via `git diff --name-only --diff-filter=U`, normalize the list, and append it to the fatal error output.

The error contract should remain human-readable while being easy for an agent to parse. The message will keep the existing high-level failure sentence, then add a `CONFLICT_FILES:` section with one path per line.

## Testing

Add a script-level regression test that creates:

1. a new `wcq` base commit that changes `README.md`
2. a feature branch created from the previous commit
3. a conflicting `README.md` change on that feature branch

Running `squash_merge_to_wcq.sh` with the current `wcq` base SHA should then fail during the squash merge and include `CONFLICT_FILES:` plus `README.md` in stderr.
