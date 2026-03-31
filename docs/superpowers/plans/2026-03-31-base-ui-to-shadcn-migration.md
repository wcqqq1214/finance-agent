# base-ui → shadcn/ui Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all 10 `components/ui/` files that depend on `@base-ui/react` and `@radix-ui/react-*` with standard shadcn/ui components (new-york style, Zinc base color), removing the old dependencies entirely.

**Architecture:** Big-bang replacement on a dedicated branch — delete all 10 old UI files, run `shadcn add` to regenerate them, then fix prop API differences in consumer files. The import paths (`@/components/ui/*`) stay the same throughout, so only prop usage needs updating.

**Tech Stack:** Next.js 16, React 19, Tailwind v4 (CSS-first, no tailwind.config.ts), shadcn/ui new-york, class-variance-authority, clsx, tailwind-merge, lucide-react

---

## File Map

| Action | File |
|--------|------|
| Modify | `frontend/components.json` |
| Modify | `frontend/src/lib/utils.ts` |
| Modify | `frontend/src/app/globals.css` |
| Delete + Regenerate | `frontend/src/components/ui/button.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/input.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/tabs.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/accordion.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/badge.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/label.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/toast.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/toaster.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/card.tsx` |
| Delete + Regenerate | `frontend/src/components/ui/skeleton.tsx` |
| Fix consumers | `frontend/src/components/reports/ReportCard.tsx` |
| Fix consumers | `frontend/src/components/chat/ResultCard.tsx` |
| Fix consumers | `frontend/src/components/chat/ChatPanel.tsx` |
| Fix consumers | `frontend/src/components/asset/AssetSelector.tsx` |
| Fix consumers | `frontend/src/components/chart/TimeRangeSelector.tsx` |
| Fix consumers | `frontend/src/components/chart/KLineChart.tsx` |
| Verify | `frontend/src/app/layout.tsx` (Toaster mount) |

---

## Task 1: Create the migration branch

**Files:**
- No file changes — git operation only

- [ ] **Step 1: Create and switch to the migration branch**

Run from the repo root (`/home/wcqqq21/q-agents`):
```bash
git checkout -b feat/shadcn-migration
```
Expected output: `Switched to a new branch 'feat/shadcn-migration'`

---

## Task 2: Update components.json

**Files:**
- Modify: `frontend/components.json`

- [ ] **Step 1: Read the current components.json**

```bash
cat frontend/components.json
```

- [ ] **Step 2: Update style and baseColor**

Replace the entire file content with:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add components.json && git commit -m "chore(ui): update components.json to new-york style with zinc base color"
```

---

## Task 3: Verify lib/utils.ts has the cn utility

**Files:**
- Modify: `frontend/src/lib/utils.ts`

- [ ] **Step 1: Read the current utils.ts**

```bash
cat frontend/src/lib/utils.ts
```

The current file uses `extendTailwindMerge` with custom chart color groups. We need to preserve those custom extensions while ensuring the `cn` export is compatible with shadcn.

- [ ] **Step 2: Verify the file exports `cn` correctly**

The file should look like this (preserve the custom `extendTailwindMerge` config for chart colors):
```ts
import { type ClassValue, clsx } from "clsx"
import { extendTailwindMerge } from "tailwind-merge"

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "text-color": ["text-chart-up", "text-chart-down"],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

If the file already matches this pattern, no change needed. If it uses plain `twMerge` without the custom extension, add the `extendTailwindMerge` config to preserve chart color support.

- [ ] **Step 3: Commit only if changed**

```bash
cd frontend && git add src/lib/utils.ts && git commit -m "chore(ui): ensure cn utility preserves chart color tailwind-merge config"
```

---

## Task 4: Remove old dependencies and delete old UI files

**Files:**
- Delete: all 10 files in `frontend/src/components/ui/`
- Modify: `frontend/package.json` (via pnpm remove)

- [ ] **Step 1: Uninstall base-ui and old Radix deps**

```bash
cd frontend && pnpm remove @base-ui/react @radix-ui/react-label @radix-ui/react-toast
```
Expected: pnpm removes the packages and updates `package.json` and `pnpm-lock.yaml`.

- [ ] **Step 2: Delete all old UI component files**

```bash
rm frontend/src/components/ui/accordion.tsx \
   frontend/src/components/ui/badge.tsx \
   frontend/src/components/ui/button.tsx \
   frontend/src/components/ui/card.tsx \
   frontend/src/components/ui/input.tsx \
   frontend/src/components/ui/label.tsx \
   frontend/src/components/ui/skeleton.tsx \
   frontend/src/components/ui/tabs.tsx \
   frontend/src/components/ui/toast.tsx \
   frontend/src/components/ui/toaster.tsx
```

- [ ] **Step 3: Commit the deletions**

```bash
cd frontend && git add -A && git commit -m "chore(ui): remove @base-ui/react, old radix deps, and all old ui components"
```

---

## Task 5: Run shadcn init and inject Zinc theme into globals.css

**Files:**
- Modify: `frontend/src/app/globals.css`

**Context:** This project uses Tailwind v4 (CSS-first config — no `tailwind.config.ts`). The `shadcn init` command will try to inject CSS variables into `globals.css`. We handle this manually to avoid overwriting existing custom variables (chart colors, sidebar colors).

- [ ] **Step 1: Read the current globals.css to understand existing variables**

```bash
cat frontend/src/app/globals.css
```

Note the existing `:root` and `.dark` blocks — we will append to them, not replace them.

- [ ] **Step 2: Run shadcn init in non-interactive mode**

```bash
cd frontend && npx shadcn@latest init -d
```

The `-d` flag uses defaults. If it prompts interactively, answer: style = new-york, base color = zinc, CSS variables = yes.

**Important:** If the CLI writes a `tailwind.config.ts` file, delete it immediately — Tailwind v4 does not use it:
```bash
rm -f frontend/tailwind.config.ts
```

- [ ] **Step 3: Check what shadcn init wrote to globals.css**

```bash
cat frontend/src/app/globals.css
```

Verify that Zinc CSS variables were added (look for `--background`, `--foreground`, `--primary`, `--radius` etc. in oklch format). If shadcn init did NOT update globals.css (it sometimes skips if the file already has variables), manually add the Zinc new-york variables.

The required variables to add inside `:root` (if not already present):
```css
--background: oklch(1 0 0);
--foreground: oklch(0.141 0.005 285.823);
--card: oklch(1 0 0);
--card-foreground: oklch(0.141 0.005 285.823);
--popover: oklch(1 0 0);
--popover-foreground: oklch(0.141 0.005 285.823);
--primary: oklch(0.21 0.006 285.885);
--primary-foreground: oklch(0.985 0 0);
--secondary: oklch(0.967 0.001 286.375);
--secondary-foreground: oklch(0.21 0.006 285.885);
--muted: oklch(0.967 0.001 286.375);
--muted-foreground: oklch(0.552 0.016 285.938);
--accent: oklch(0.967 0.001 286.375);
--accent-foreground: oklch(0.21 0.006 285.885);
--destructive: oklch(0.577 0.245 27.325);
--border: oklch(0.92 0.004 286.32);
--input: oklch(0.92 0.004 286.32);
--ring: oklch(0.705 0.015 286.067);
--radius: 0.5rem;
```

And inside `.dark`:
```css
--background: oklch(0.141 0.005 285.823);
--foreground: oklch(0.985 0 0);
--card: oklch(0.21 0.006 285.885);
--card-foreground: oklch(0.985 0 0);
--popover: oklch(0.21 0.006 285.885);
--popover-foreground: oklch(0.985 0 0);
--primary: oklch(0.985 0 0);
--primary-foreground: oklch(0.21 0.006 285.885);
--secondary: oklch(0.274 0.006 286.033);
--secondary-foreground: oklch(0.985 0 0);
--muted: oklch(0.274 0.006 286.033);
--muted-foreground: oklch(0.705 0.015 286.067);
--accent: oklch(0.274 0.006 286.033);
--accent-foreground: oklch(0.985 0 0);
--destructive: oklch(0.704 0.191 22.216);
--border: oklch(1 0 0 / 10%);
--input: oklch(1 0 0 / 15%);
--ring: oklch(0.552 0.016 285.938);
```

- [ ] **Step 4: Add accordion and toast keyframes to globals.css (Tailwind v4)**

Since Tailwind v4 has no `tailwind.config.ts`, keyframes must live in `globals.css`. Append these after the existing variable blocks:

```css
@keyframes accordion-down {
  from { height: 0; }
  to { height: var(--radix-accordion-content-height); }
}

@keyframes accordion-up {
  from { height: var(--radix-accordion-content-height); }
  to { height: 0; }
}

@theme {
  --animate-accordion-down: accordion-down 0.2s ease-out;
  --animate-accordion-up: accordion-up 0.2s ease-out;
}
```

- [ ] **Step 5: Commit globals.css changes**

```bash
cd frontend && git add src/app/globals.css && git commit -m "chore(ui): inject zinc theme variables and accordion keyframes for shadcn new-york"
```

---

## Task 6: Generate all shadcn components

**Files:**
- Create: all 10 files in `frontend/src/components/ui/`

- [ ] **Step 1: Run shadcn add for all components**

```bash
cd frontend && npx shadcn@latest add button input tabs accordion badge label toast toaster card skeleton
```

When prompted to overwrite existing files, answer yes. This will:
- Install `@radix-ui/react-accordion`, `@radix-ui/react-tabs`, `@radix-ui/react-label`, `@radix-ui/react-toast` as peer deps
- Generate all 10 component files under `src/components/ui/`
- Also generate `src/hooks/use-toast.ts` if it doesn't exist

- [ ] **Step 2: Verify all 10 files were created**

```bash
ls frontend/src/components/ui/
```

Expected output includes: `accordion.tsx button.tsx badge.tsx card.tsx input.tsx label.tsx skeleton.tsx tabs.tsx toast.tsx toaster.tsx`

- [ ] **Step 3: Check if use-toast hook was generated**

```bash
ls frontend/src/hooks/
```

If `use-toast.ts` was generated, verify it exports `useToast` and `toast`. The existing consumers (`ChatPanel.tsx`, `AssetSelector.tsx`, `KLineChart.tsx`) import from `@/hooks/use-toast` — this path must exist.

- [ ] **Step 4: Commit generated components**

```bash
cd frontend && git add src/components/ui/ src/hooks/ package.json pnpm-lock.yaml && git commit -m "feat(ui): generate shadcn new-york components (button, input, tabs, accordion, badge, label, toast, toaster, card, skeleton)"
```

---

## Task 7: Fix Accordion prop API in ReportCard.tsx

**Files:**
- Modify: `frontend/src/components/reports/ReportCard.tsx`

**Context:** The old base-ui Accordion used `openMultiple` prop. shadcn Accordion uses `type="multiple"` or `type="single"`. The consumer at `ReportCard.tsx` uses `AccordionItem`, `AccordionTrigger`, `AccordionContent` — check if it passes `openMultiple` to the root `<Accordion>`.

- [ ] **Step 1: Read ReportCard.tsx**

```bash
cat frontend/src/components/reports/ReportCard.tsx
```

- [ ] **Step 2: Fix Accordion root props**

Find the `<Accordion>` root usage. If it has `openMultiple` prop, replace with `type="multiple"`. If it has no explicit type, add `type="single" collapsible`.

Example — if the file has:
```tsx
<Accordion openMultiple className="...">
```
Change to:
```tsx
<Accordion type="multiple" className="...">
```

If it has no `openMultiple`:
```tsx
<Accordion className="...">
```
Change to:
```tsx
<Accordion type="single" collapsible className="...">
```

- [ ] **Step 3: Verify AccordionItem value prop**

shadcn `AccordionItem` requires a `value` prop (string). The existing usage already passes `value={report.id}` — no change needed there.

- [ ] **Step 4: Run type-check to verify**

```bash
cd frontend && pnpm type-check 2>&1 | grep -i "ReportCard"
```

Expected: no errors for this file.

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/components/reports/ReportCard.tsx && git commit -m "fix(ui): update Accordion props in ReportCard for shadcn API"
```

---

## Task 8: Fix Tabs variant prop in AssetSelector.tsx

**Files:**
- Modify: `frontend/src/components/asset/AssetSelector.tsx`

**Context:** The old base-ui Tabs had a `variant` prop on `TabsList` (e.g., `variant="default"`). shadcn's `TabsList` does not have a `variant` prop — it uses a single fixed style. The `value`/`onValueChange` props on `<Tabs>` are identical between base-ui and shadcn.

- [ ] **Step 1: Read AssetSelector.tsx**

```bash
cat frontend/src/components/asset/AssetSelector.tsx
```

- [ ] **Step 2: Remove variant prop from TabsList**

Find `<TabsList variant="default">` and change to `<TabsList>`:
```tsx
// Before
<TabsList variant="default">

// After
<TabsList>
```

- [ ] **Step 3: Verify Tabs root props are unchanged**

The `<Tabs value={assetType} onValueChange={onAssetTypeChange}>` usage is identical in shadcn — no change needed.

- [ ] **Step 4: Run type-check**

```bash
cd frontend && pnpm type-check 2>&1 | grep -i "AssetSelector"
```

Expected: no errors for this file.

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/components/asset/AssetSelector.tsx && git commit -m "fix(ui): remove TabsList variant prop in AssetSelector for shadcn API"
```

---

## Task 9: Verify Badge usage in ResultCard.tsx and ReportCard.tsx

**Files:**
- Modify (if needed): `frontend/src/components/chat/ResultCard.tsx`
- Modify (if needed): `frontend/src/components/reports/ReportCard.tsx`

**Context:** The old badge used `useRender`/`mergeProps` internally but the consumer API was `<Badge variant="secondary">` and `<Badge variant="outline">`. shadcn Badge has the same `variant` prop API — no consumer changes expected. This task verifies that assumption.

- [ ] **Step 1: Read both files**

```bash
cat frontend/src/components/chat/ResultCard.tsx
cat frontend/src/components/reports/ReportCard.tsx
```

- [ ] **Step 2: Verify Badge usage**

Confirm both files use only `variant` and `className` props on `<Badge>`. If any file uses a `render` prop (from the old base-ui `useRender` pattern), remove it — shadcn Badge does not support a render prop.

Expected usage (no changes needed):
```tsx
<Badge variant="secondary" className="animate-pulse text-xs">...</Badge>
<Badge variant="outline" className="text-xs">...</Badge>
```

- [ ] **Step 3: Run type-check**

```bash
cd frontend && pnpm type-check 2>&1 | grep -iE "ResultCard|ReportCard"
```

Expected: no errors.

- [ ] **Step 4: Commit only if changes were made**

```bash
cd frontend && git add src/components/chat/ResultCard.tsx src/components/reports/ReportCard.tsx && git commit -m "fix(ui): remove render prop from Badge usage for shadcn API"
```

---

## Task 10: Verify Button usage in ChatPanel.tsx, AssetSelector.tsx, TimeRangeSelector.tsx

**Files:**
- Modify (if needed): `frontend/src/components/chat/ChatPanel.tsx`
- Modify (if needed): `frontend/src/components/asset/AssetSelector.tsx`
- Modify (if needed): `frontend/src/components/chart/TimeRangeSelector.tsx`

**Context:** The old base-ui Button used a render prop pattern internally. shadcn Button uses standard `variant` and `size` CVA props. Consumer-facing API is the same for standard usage, but any use of base-ui's `render` prop must be removed.

- [ ] **Step 1: Read all three files**

```bash
cat frontend/src/components/chat/ChatPanel.tsx
cat frontend/src/components/asset/AssetSelector.tsx
cat frontend/src/components/chart/TimeRangeSelector.tsx
```

- [ ] **Step 2: Check for render prop usage**

Search for any `render={` prop on `<Button>` elements. If found, remove it — shadcn Button renders a standard `<button>` element and does not accept a `render` prop.

- [ ] **Step 3: Verify variant and size props are valid**

shadcn new-york Button variants: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`
shadcn new-york Button sizes: `default`, `sm`, `lg`, `icon`

If any consumer uses `xs`, `icon-xs`, `icon-sm`, `icon-lg` sizes (which existed in the old base-ui button), update them:
- `xs` → `sm`
- `icon-xs` → `icon`
- `icon-sm` → `icon`
- `icon-lg` → `icon`

- [ ] **Step 4: Run type-check**

```bash
cd frontend && pnpm type-check 2>&1 | grep -iE "ChatPanel|AssetSelector|TimeRangeSelector"
```

Expected: no errors.

- [ ] **Step 5: Commit only if changes were made**

```bash
cd frontend && git add src/components/chat/ChatPanel.tsx src/components/asset/AssetSelector.tsx src/components/chart/TimeRangeSelector.tsx && git commit -m "fix(ui): update Button variant/size props for shadcn API"
```

---

## Task 11: Verify useToast hook compatibility in ChatPanel, AssetSelector, KLineChart

**Files:**
- Modify (if needed): `frontend/src/components/chat/ChatPanel.tsx`
- Modify (if needed): `frontend/src/components/asset/AssetSelector.tsx`
- Modify (if needed): `frontend/src/components/chart/KLineChart.tsx`

**Context:** All three files import `useToast` from `@/hooks/use-toast`. shadcn generates this hook at the same path. The `toast()` call API is identical. This task verifies the hook path and call signature are compatible.

- [ ] **Step 1: Read the generated use-toast hook**

```bash
cat frontend/src/hooks/use-toast.ts
```

Confirm it exports `useToast` and that `useToast()` returns `{ toast, ... }`.

- [ ] **Step 2: Check existing toast call signatures**

The existing calls look like:
```tsx
toast({ title: "...", description: "...", variant: "destructive" })
```

shadcn's `toast()` accepts `{ title, description, variant, action }` — identical API. No changes expected.

- [ ] **Step 3: Run type-check**

```bash
cd frontend && pnpm type-check 2>&1 | grep -iE "ChatPanel|AssetSelector|KLineChart"
```

Expected: no errors.

- [ ] **Step 4: Commit only if changes were made**

If no changes were needed, skip this commit.

---

## Task 11b: Restore card.tsx custom size prop and container queries

**Files:**
- Modify: `frontend/src/components/ui/card.tsx`

**Context:** The old `card.tsx` had a custom `size` prop (`"default" | "sm"`) and used `@container` queries for responsive layout. shadcn's generated `card.tsx` is a plain unstyled wrapper — it won't have these. Any consumer using `<Card size="sm">` will break.

- [ ] **Step 1: Check if any consumer uses the size prop**

```bash
grep -r 'Card.*size=' frontend/src/components/
```

- [ ] **Step 2: If size prop is used, add it back to the generated card.tsx**

Read the generated `frontend/src/components/ui/card.tsx`, then add the `size` variant using CVA:

```tsx
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const cardVariants = cva("rounded-xl border bg-card text-card-foreground shadow", {
  variants: {
    size: {
      default: "p-6",
      sm: "p-4",
    },
  },
  defaultVariants: { size: "default" },
})

// Add VariantProps<typeof cardVariants> to Card's props interface
```

- [ ] **Step 3: Run type-check**

```bash
cd frontend && pnpm type-check 2>&1 | grep -i "card"
```

- [ ] **Step 4: Commit if changed**

```bash
cd frontend && git add src/components/ui/card.tsx && git commit -m "fix(ui): restore card size variant after shadcn regeneration"
```

---

## Task 12: Verify Toaster is mounted in layout.tsx

**Files:**
- Verify (modify if needed): `frontend/src/app/layout.tsx`

**Context:** shadcn's toast system requires `<Toaster />` mounted at the app root. The exploration showed it's already imported and mounted in `layout.tsx`. This task confirms it still works after the component regeneration.

- [ ] **Step 1: Read layout.tsx**

```bash
cat frontend/src/app/layout.tsx
```

- [ ] **Step 2: Verify Toaster import and mount**

Confirm the file has:
```tsx
import { Toaster } from "@/components/ui/toaster"
// ...
<Toaster />
```

The import path `@/components/ui/toaster` is unchanged — shadcn generates `toaster.tsx` at the same location.

- [ ] **Step 3: No commit needed if unchanged**

If the file already has the correct import and mount, no change is needed.

---

## Task 13: Full lint and type-check pass

**Files:**
- Fix any remaining issues across all modified files

- [ ] **Step 1: Run ESLint**

```bash
cd frontend && pnpm lint
```

Fix any errors reported. Common issues after shadcn migration:
- Unused imports from old base-ui (remove them)
- `any` type violations from generated shadcn components (shadcn components are typed — these should not appear)

- [ ] **Step 2: Run TypeScript type-check**

```bash
cd frontend && pnpm type-check
```

Fix any remaining type errors. Common issues:
- Missing `type` prop on `<Accordion>` root (must be `"single"` or `"multiple"`)
- Invalid `variant` values on Button/Badge (check against shadcn's CVA definitions)

- [ ] **Step 3: Commit any fixes**

```bash
cd frontend && git add -A && git commit -m "fix(ui): resolve lint and type errors after shadcn migration"
```

---

## Task 14: Final verification

- [ ] **Step 1: Confirm @base-ui/react is removed**

```bash
grep "@base-ui" frontend/package.json
```

Expected: no output.

- [ ] **Step 2: Confirm old Radix direct deps are removed**

```bash
grep "@radix-ui/react-label\|@radix-ui/react-toast" frontend/package.json
```

Expected: no output (they are now managed as transitive deps by shadcn's Radix packages).

- [ ] **Step 3: Confirm all 10 UI files exist**

```bash
ls frontend/src/components/ui/
```

Expected: `accordion.tsx  badge.tsx  button.tsx  card.tsx  input.tsx  label.tsx  skeleton.tsx  tabs.tsx  toast.tsx  toaster.tsx`

- [ ] **Step 4: Run the dev server and smoke test**

```bash
cd frontend && pnpm dev
```

Open `http://localhost:3000` and manually verify:
- Accordion opens/closes with animation
- Toast notifications appear (trigger from chat or asset selector)
- Tabs switch correctly
- Buttons render with correct styles
- Input fields accept text

- [ ] **Step 5: Final commit if any last fixes**

```bash
cd frontend && git add -A && git commit -m "chore(ui): final cleanup after base-ui to shadcn migration"
```

---

## Success Criteria Checklist

- [ ] `@base-ui/react` not in `frontend/package.json`
- [ ] `@radix-ui/react-label` and `@radix-ui/react-toast` not as direct deps
- [ ] All 10 `components/ui/` files are shadcn new-york generated
- [ ] `pnpm lint` passes with zero errors
- [ ] `pnpm type-check` passes with zero errors
- [ ] Accordion, toast, tabs, button, input render correctly with animations
- [ ] No visual regressions in chat, reports, stock components
