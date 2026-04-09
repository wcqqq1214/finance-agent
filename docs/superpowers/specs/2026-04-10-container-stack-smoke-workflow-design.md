# Container Stack Smoke Workflow Design

## Goal

Repair `.github/workflows/container-stack-smoke.yml` so GitHub Actions accepts the workflow and still exercises the container smoke flow across Linux, macOS, and Windows.

## Root Cause

The workflow uses `matrix.shell` in step-level `shell:` fields. GitHub Actions rejects that context in this position during workflow validation, so the file is invalid before any job starts.

## Recommended Approach

Keep the matrix exactly where it already works and delete the illegal step-level `shell:` expressions.

- Leave `matrix.os` for job naming and `runs-on`
- Keep the per-OS command strings already stored in the matrix
- Let each GitHub-hosted runner use its default shell for `run:` steps

This is the smallest change that preserves the existing three-OS coverage while removing the field GitHub rejects during validation.

## Testing

- Add a regression test that fails if any step `shell:` references `${{ matrix.* }}`
- Run the targeted pytest file to prove the new test fails before the YAML change
- Re-run the targeted pytest file after the YAML change to confirm the regression is fixed
