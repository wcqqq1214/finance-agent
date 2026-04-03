# Report Card Copy Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the reports card UI so tab labels are English and the query line does not repeat the active ticker symbol.

**Architecture:** Keep the UI change localized to the reports card. Add a minimal regression test first, then extract query cleanup into a small helper used by the card so the display rule stays explicit and easy to extend.

**Tech Stack:** Next.js 16, React 19, TypeScript, Node test runner

---

## Chunk 1: Report Card Copy

### Task 1: Lock the current requirement with a failing regression test

**Files:**
- Create: `frontend/src/components/reports/ReportCard.test.ts`
- Test: `frontend/src/components/reports/ReportCard.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
test("report card tabs use english copy", () => {
  // Assert the source contains english tab labels.
})

test("report card query line does not render raw report.query", () => {
  // Assert the source no longer interpolates raw query text directly.
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test --experimental-strip-types frontend/src/components/reports/ReportCard.test.ts`
Expected: FAIL because the current source still uses Chinese tab labels and directly renders `report.query`.

### Task 2: Implement the display cleanup

**Files:**
- Create: `frontend/src/components/reports/report-card-helpers.ts`
- Modify: `frontend/src/components/reports/ReportCard.tsx`
- Test: `frontend/src/components/reports/ReportCard.test.ts`

- [ ] **Step 3: Write minimal implementation**

```ts
export function getReportQueryDisplay(query: string, symbol: string): string {
  // Remove standalone occurrences of the symbol and trim leftover punctuation.
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test --experimental-strip-types frontend/src/components/reports/ReportCard.test.ts`
Expected: PASS

### Task 3: Verify the touched frontend slice

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 5: Run targeted verification**

Run: `cd frontend && pnpm lint src/components/reports/ReportCard.tsx src/components/reports/report-card-helpers.ts src/components/reports/ReportCard.test.ts`
Expected: PASS

- [ ] **Step 6: Run type checking**

Run: `cd frontend && pnpm type-check`
Expected: PASS
