# Frontend Gitignore Consolidation Design

## Summary

Consolidate `frontend/.gitignore` into the repository root `.gitignore` so the repo has a single ignore entry point while preserving the current ignore behavior for paths under `frontend/`.

## Problem

The repository currently splits ignore rules between the root `.gitignore` and `frontend/.gitignore`.
That duplication makes maintenance harder and forces readers to inspect two files to understand the effective ignore set for frontend artifacts.

## Goals

- Move frontend-specific ignore rules into the root `.gitignore`
- Preserve existing ignore behavior for representative frontend paths
- Remove `frontend/.gitignore` after the root file fully covers its semantics

## Non-Goals

- Change which frontend artifacts are ignored
- Restructure unrelated root ignore rules
- Introduce new tooling or CI checks

## Approach

Translate each rule from `frontend/.gitignore` into an equivalent root-scoped pattern.
Rules that were rooted at the frontend directory, such as `/node_modules` and `/.next/`, become `frontend/node_modules/` and `frontend/.next/`.
Rules without a leading slash that previously matched anywhere inside the frontend subtree, such as `.env*`, `*.pem`, `*.tsbuildinfo`, and `next-env.d.ts`, become paired root rules that cover both `frontend/<name>` and `frontend/**/<name>` where needed.

The `.yarn/*` allowlist behavior will be preserved by moving the ignore rule and its negations together so `frontend/.yarn/patches`, `plugins`, `releases`, and `versions` remain unignored.

## Verification

Use `git check-ignore -v` on representative frontend paths before and after the change.
The post-change result should still report those paths as ignored, but the matching source should move from `frontend/.gitignore` to the root `.gitignore`.
Also verify that allowlisted `.yarn` paths remain not ignored after deleting `frontend/.gitignore`.
