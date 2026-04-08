# Stock Chart Matches Card Quote Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the stock chart's latest displayed price match the selected stock card quote by sharing the same live quote snapshot.

**Architecture:** Page-level state will hold the selected stock quote. The asset selector owns quote fetching and reports the selected quote upward; the chart consumes that quote to overlay the latest visible stock candle.

**Tech Stack:** Next.js 16, React 19, TypeScript strict mode, node:test source-based frontend tests

---

### Task 1: Add failing tests

**Files:**
- Create: `frontend/src/app/page.test.ts`
- Modify: `frontend/src/components/asset/AssetSelector.test.ts`
- Modify: `frontend/src/components/chart/KLineChart.test.ts`

- [ ] **Step 1: Write failing tests for shared selected quote state and chart overlay logic**
- [ ] **Step 2: Run `cd frontend && node --test src/app/page.test.ts src/components/asset/AssetSelector.test.ts src/components/chart/KLineChart.test.ts` and confirm failure**
- [ ] **Step 3: Implement the minimal frontend state lift and chart overlay**
- [ ] **Step 4: Re-run the same frontend tests and confirm pass**

### Task 2: Verify frontend slice

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/asset/AssetSelector.tsx`
- Modify: `frontend/src/components/chart/KLineChart.tsx`

- [ ] **Step 1: Run `cd frontend && node --test src/app/page.test.ts src/components/asset/AssetSelector.test.ts src/components/chart/KLineChart.test.ts`**
- [ ] **Step 2: Run `bash .agents/skills/auto-dev-workflow/scripts/run_scoped_checks.sh --base-sha c668b11b5b3ca771de6dda1270c814791c5b3b31 --diff-target worktree --cmd 'cd frontend && node --test src/app/page.test.ts src/components/asset/AssetSelector.test.ts src/components/chart/KLineChart.test.ts'`**
- [ ] **Step 3: Commit and run `bash .agents/skills/auto-dev-workflow/scripts/run_final_gate.sh --base-sha c668b11b5b3ca771de6dda1270c814791c5b3b31`**
