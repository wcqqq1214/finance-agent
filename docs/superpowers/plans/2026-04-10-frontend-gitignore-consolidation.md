# Frontend Gitignore Consolidation Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `frontend/.gitignore` into the repository root `.gitignore` without changing frontend ignore behavior.

**Architecture:** Keep one repository-level ignore file and translate frontend-local patterns into root-scoped equivalents. Verify equivalence with `git check-ignore -v` against representative ignored and unignored frontend paths before deleting the child file.

**Tech Stack:** Git ignore pattern semantics, shell verification commands

---

## Chunk 1: Capture Current Ignore Behavior

### Task 1: Record the current ignore semantics

**Files:**
- Modify: `.gitignore`
- Delete: `frontend/.gitignore`
- Reference: `docs/superpowers/specs/2026-04-10-frontend-gitignore-consolidation-design.md`

- [ ] **Step 1: Run baseline ignore checks**

Run:
```bash
git check-ignore -v \
  frontend/node_modules/pkg \
  frontend/.next/cache \
  frontend/out/index.html \
  frontend/.env.local \
  frontend/subdir/.env.production \
  frontend/.vercel/project.json \
  frontend/subdir/.vercel/project.json \
  frontend/.pnp.cjs \
  frontend/subdir/.pnp.data.json \
  frontend/coverage/lcov.info \
  frontend/build/app.js \
  frontend/subdir/cert.pem \
  frontend/subdir/yarn-error.log \
  frontend/next-env.d.ts \
  frontend/subdir/next-env.d.ts \
  frontend/tsconfig.tsbuildinfo \
  frontend/subdir/cache.tsbuildinfo
```
Expected: each path is ignored by `frontend/.gitignore`.

- [ ] **Step 2: Confirm the `.yarn` allowlist remains unignored today**

Run:
```bash
git check-ignore -v \
  frontend/.yarn/releases/yarn.js \
  frontend/.yarn/patches/a.patch \
  frontend/.yarn/plugins/a.js \
  frontend/.yarn/versions/a.yml
```
Expected: exit code `1` and no output.

## Chunk 2: Migrate Patterns

### Task 2: Translate frontend-local rules into root-scoped rules

**Files:**
- Modify: `.gitignore`
- Delete: `frontend/.gitignore`

- [ ] **Step 1: Add missing frontend-specific rules to the root `.gitignore`**

Add root-scoped patterns for:
- `frontend/.pnp`
- `frontend/.pnp.*`
- `frontend/.yarn/*` with allowlist negations
- `frontend/coverage/`
- `frontend/build/`
- `frontend/.env*` plus nested descendant coverage
- `frontend/*.pem` plus nested descendant coverage
- frontend package-manager debug logs
- `frontend/*.tsbuildinfo` plus nested descendant coverage
- `frontend/next-env.d.ts` plus nested descendant coverage

- [ ] **Step 2: Delete `frontend/.gitignore`**

Expected: only the root `.gitignore` remains responsible for ignore behavior.

## Chunk 3: Verify Equivalent Behavior

### Task 3: Re-run ignore checks after migration

**Files:**
- Modify: `.gitignore`
- Delete: `frontend/.gitignore`

- [ ] **Step 1: Re-run the ignored-path verification**

Run the same baseline command from Task 1.
Expected: ignored paths are still ignored, now by the root `.gitignore`.

- [ ] **Step 2: Re-run the `.yarn` allowlist verification**

Run the same allowlist command from Task 1.
Expected: exit code `1` and no output.

- [ ] **Step 3: Review the diff**

Run:
```bash
git diff -- .gitignore frontend/.gitignore docs/superpowers/specs/2026-04-10-frontend-gitignore-consolidation-design.md docs/superpowers/plans/2026-04-10-frontend-gitignore-consolidation.md
```
Expected: root `.gitignore` absorbs the frontend rules, `frontend/.gitignore` is deleted, and the spec/plan describe the change accurately.
