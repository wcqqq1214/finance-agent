# Home Page Asset Type Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add crypto/stocks toggle UI to Home page and rename StockSelector to AssetSelector

**Architecture:** Rename StockSelector component to AssetSelector, add Tabs component to header for crypto/stocks toggle, lift asset type state to Home page for future extensibility

**Tech Stack:** React, TypeScript, Next.js, Base UI Tabs component

**Spec:** `docs/superpowers/specs/2026-03-20-home-page-asset-type-toggle-design.md`

---

## File Structure

**Files to Create:**
- `frontend/src/components/asset/AssetSelector.tsx` (renamed from StockSelector)

**Files to Modify:**
- `frontend/src/app/page.tsx` - Update imports, add assetType state, rename variables
- `frontend/src/components/stock/StockSelector.tsx` - Will be moved/renamed

**Files to Delete:**
- `frontend/src/components/stock/StockSelector.tsx` (after moving content)

---

## Task 1: Create asset directory and move StockSelector

**Files:**
- Create: `frontend/src/components/asset/` (directory)
- Move: `frontend/src/components/stock/StockSelector.tsx` → `frontend/src/components/asset/AssetSelector.tsx`

- [ ] **Step 1: Create asset directory**

```bash
mkdir -p frontend/src/components/asset
```

- [ ] **Step 2: Copy StockSelector to new location**

```bash
cp frontend/src/components/stock/StockSelector.tsx frontend/src/components/asset/AssetSelector.tsx
```

- [ ] **Step 3: Verify file was copied**

Run: `ls -la frontend/src/components/asset/`
Expected: AssetSelector.tsx exists

- [ ] **Step 4: Commit the file copy**

```bash
git add frontend/src/components/asset/AssetSelector.tsx
git commit -m "chore: copy StockSelector to asset directory as AssetSelector"
```

---

## Task 2: Rename component and props in AssetSelector

**Files:**
- Modify: `frontend/src/components/asset/AssetSelector.tsx`

- [ ] **Step 1: Rename interface from StockSelectorProps to AssetSelectorProps**

Replace:
```typescript
interface StockSelectorProps {
  selectedStock: string | null;
  onStockSelect: (symbol: string) => void;
}
```

With:
```typescript
interface AssetSelectorProps {
  selectedAsset: string | null;
  onAssetSelect: (symbol: string) => void;
  assetType: 'crypto' | 'stocks';
  onAssetTypeChange: (type: 'crypto' | 'stocks') => void;
}
```

- [ ] **Step 2: Rename function from StockSelector to AssetSelector**

Replace:
```typescript
export function StockSelector({ selectedStock, onStockSelect }: StockSelectorProps) {
```

With:
```typescript
export function AssetSelector({
  selectedAsset,
  onAssetSelect,
  assetType,
  onAssetTypeChange
}: AssetSelectorProps) {
```

- [ ] **Step 3: Update all selectedStock references to selectedAsset**

Replace all occurrences of:
- `selectedStock === stock.symbol` → `selectedAsset === stock.symbol`
- `onStockSelect(stock.symbol)` → `onAssetSelect(stock.symbol)`

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors related to AssetSelector

- [ ] **Step 5: Commit the renaming**

```bash
git add frontend/src/components/asset/AssetSelector.tsx
git commit -m "refactor: rename StockSelector to AssetSelector with new props"
```

---

## Task 3: Add Tabs UI to AssetSelector header

**Files:**
- Modify: `frontend/src/components/asset/AssetSelector.tsx`

- [ ] **Step 1: Add Tabs imports at the top**

Add after existing imports:
```typescript
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
```

- [ ] **Step 2: Replace header section with Tabs**

Replace:
```tsx
<div className="flex items-center justify-between">
  <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
    Stocks
  </h2>
  <Button
    variant="ghost"
    size="icon"
    className="h-6 w-6"
    onClick={() => fetchQuotes(true)}
    disabled={refreshing}
  >
    <RefreshCw className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} />
  </Button>
</div>
```

With:
```tsx
<div className="flex items-center justify-between">
  <Tabs value={assetType} onValueChange={onAssetTypeChange}>
    <TabsList variant="default">
      <TabsTrigger value="crypto">Crypto</TabsTrigger>
      <TabsTrigger value="stocks">Stocks</TabsTrigger>
    </TabsList>
  </Tabs>
  <Button
    variant="ghost"
    size="icon"
    className="h-6 w-6"
    onClick={() => fetchQuotes(true)}
    disabled={refreshing}
  >
    <RefreshCw className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} />
  </Button>
</div>
```

- [ ] **Step 3: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit the Tabs UI addition**

```bash
git add frontend/src/components/asset/AssetSelector.tsx
git commit -m "feat: add crypto/stocks toggle tabs to AssetSelector header"
```

---

## Task 4: Update Home page imports and state

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Update import statement**

Replace:
```typescript
import { StockSelector } from '@/components/stock/StockSelector';
```

With:
```typescript
import { AssetSelector } from '@/components/asset/AssetSelector';
```

- [ ] **Step 2: Add assetType state**

Add after the existing useState:
```typescript
const [assetType, setAssetType] = useState<'crypto' | 'stocks'>('stocks');
```

- [ ] **Step 3: Rename selectedStock to selectedAsset**

Replace:
```typescript
const [selectedStock, setSelectedStock] = useState<string | null>(null);
```

With:
```typescript
const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
```

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit the state changes**

```bash
git add frontend/src/app/page.tsx
git commit -m "refactor: add assetType state and rename selectedStock to selectedAsset"
```

---

## Task 5: Update Home page component usage

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Update AssetSelector props**

Replace:
```tsx
<StockSelector
  selectedStock={selectedStock}
  onStockSelect={setSelectedStock}
/>
```

With:
```tsx
<AssetSelector
  selectedAsset={selectedAsset}
  onAssetSelect={setSelectedAsset}
  assetType={assetType}
  onAssetTypeChange={setAssetType}
/>
```

- [ ] **Step 2: Update KLineChart prop**

Replace:
```tsx
<KLineChart selectedStock={selectedStock} />
```

With:
```tsx
<KLineChart selectedStock={selectedAsset} />
```

- [ ] **Step 3: Update ChatPanel prop**

Replace:
```tsx
<ChatPanel selectedStock={selectedStock} />
```

With:
```tsx
<ChatPanel selectedStock={selectedAsset} />
```

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit the component usage updates**

```bash
git add frontend/src/app/page.tsx
git commit -m "refactor: update Home page to use AssetSelector with new props"
```

---

## Task 6: Delete old StockSelector file

**Files:**
- Delete: `frontend/src/components/stock/StockSelector.tsx`

- [ ] **Step 1: Verify AssetSelector is working**

Run: `cd frontend && npm run dev`
Expected: Dev server starts without errors

- [ ] **Step 2: Delete old StockSelector file**

```bash
git rm frontend/src/components/stock/StockSelector.tsx
```

- [ ] **Step 3: Commit the deletion**

```bash
git commit -m "chore: remove old StockSelector file after migration to AssetSelector"
```

---

## Task 7: Manual testing

**Files:**
- Test: All modified files

- [ ] **Step 1: Start dev server**

Run: `cd frontend && npm run dev`
Expected: Server starts on http://localhost:3000

- [ ] **Step 2: Test Tabs render**

Action: Open http://localhost:3000 in browser
Expected: See "Crypto" and "Stocks" tabs in the asset selector header

- [ ] **Step 3: Test tab switching**

Action: Click "Crypto" tab, then "Stocks" tab
Expected: Active tab changes visually (background color changes)

- [ ] **Step 4: Test refresh button**

Action: Click the refresh icon button
Expected: Button shows spinning animation, stocks refresh

- [ ] **Step 5: Test stock selection**

Action: Click on a stock card
Expected: Stock card becomes selected (visual highlight)

- [ ] **Step 6: Check console for errors**

Action: Open browser DevTools console
Expected: No errors or warnings

- [ ] **Step 7: Document testing results**

Create a comment or note confirming all tests passed

---

## Task 8: Final verification and cleanup

**Files:**
- Verify: All modified files

- [ ] **Step 1: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 2: Run linter**

Run: `cd frontend && npm run lint`
Expected: No errors (or only pre-existing warnings)

- [ ] **Step 3: Verify git status**

Run: `git status`
Expected: Working tree clean, all changes committed

- [ ] **Step 4: Review commit history**

Run: `git log --oneline -8`
Expected: See all 7 commits from this implementation

- [ ] **Step 5: Create summary comment**

Document:
- All tasks completed
- All tests passed
- Ready for code review

---

## Notes

**Testing Strategy:**
- This is a UI-only change with no business logic
- Manual testing is sufficient (no automated tests needed)
- Focus on visual verification and interaction testing

**Future Work:**
- Add crypto data fetching logic
- Conditionally render different content based on assetType
- Add crypto-specific components

**Dependencies:**
- Tabs component from `@/components/ui/tabs` (already exists)
- Base UI React library (already installed)

