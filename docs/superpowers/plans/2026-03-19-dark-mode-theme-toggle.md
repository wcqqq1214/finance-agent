# Dark Mode Theme Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a theme toggle system that defaults to system preference with manual override capability

**Architecture:** Use next-themes library to manage theme state with localStorage persistence. ThemeProvider wraps the app, ThemeToggle button in navbar switches between light/dark modes. CSS variables already defined in globals.css automatically switch based on `.dark` class.

**Tech Stack:** Next.js 16, next-themes, Tailwind CSS v4, lucide-react icons, TypeScript

---

## File Structure

**New Files:**
- `frontend/src/components/providers/ThemeProvider.tsx` - Client component wrapping next-themes provider
- `frontend/src/components/layout/ThemeToggle.tsx` - Theme toggle button component

**Modified Files:**
- `frontend/src/app/layout.tsx` - Add ThemeProvider wrapper and suppressHydrationWarning
- `frontend/src/components/layout/Navbar.tsx` - Add ThemeToggle to right side
- `frontend/package.json` - Add next-themes dependency

---

### Task 0: Pre-Implementation Verification

**Files:**
- Read: `frontend/package.json`
- Read: `frontend/src/app/globals.css`
- Read: `frontend/src/components/layout/Navbar.tsx`

- [ ] **Step 1: Verify lucide-react is installed**

```bash
cd /home/wcqqq21/finance-agent/frontend
npm list lucide-react
```

Expected: Shows lucide-react is already installed

- [ ] **Step 2: Verify dark mode CSS exists**

```bash
grep -A 5 "\.dark {" src/app/globals.css
```

Expected: Shows dark mode CSS variables defined

- [ ] **Step 3: Verify Navbar structure**

```bash
cat src/components/layout/Navbar.tsx | grep -A 2 "justify-between"
```

Expected: Shows existing navbar layout structure

- [ ] **Step 4: Verify Next.js version**

```bash
npm list next
```

Expected: Shows Next.js 16.x.x

---

### Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install next-themes package**

```bash
cd /home/wcqqq21/finance-agent/frontend
npm install next-themes
```

Expected: Package installed successfully, package.json and package-lock.json updated

- [ ] **Step 2: Verify installation**

```bash
npm list next-themes
```

Expected: Shows next-themes version installed

- [ ] **Step 3: Commit dependency**

```bash
cd /home/wcqqq21/finance-agent
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add next-themes for theme management"
```

---

### Task 2: Create ThemeProvider Component

**Files:**
- Create: `frontend/src/components/providers/ThemeProvider.tsx`

- [ ] **Step 1: Create providers directory**

```bash
mkdir -p /home/wcqqq21/finance-agent/frontend/src/components/providers
```

- [ ] **Step 2: Create ThemeProvider component**

Create `/home/wcqqq21/finance-agent/frontend/src/components/providers/ThemeProvider.tsx`:

```typescript
'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { type ThemeProviderProps } from 'next-themes/dist/types';

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd /home/wcqqq21/finance-agent/frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 4: Commit ThemeProvider**

```bash
cd /home/wcqqq21/finance-agent
git add frontend/src/components/providers/ThemeProvider.tsx
git commit -m "feat: add ThemeProvider wrapper component"
```

---

### Task 3: Create ThemeToggle Component

**Files:**
- Create: `frontend/src/components/layout/ThemeToggle.tsx`

- [ ] **Step 1: Create ThemeToggle component**

Create `/home/wcqqq21/finance-agent/frontend/src/components/layout/ThemeToggle.tsx`:

```typescript
'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <button
        className="inline-flex items-center justify-center rounded-md p-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        aria-label="切换主题"
      >
        <Sun className="h-5 w-5" />
      </button>
    );
  }

  const isDark = resolvedTheme === 'dark';

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="inline-flex items-center justify-center rounded-md p-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
      aria-label={isDark ? '切换到浅色模式' : '切换到暗黑模式'}
    >
      {isDark ? (
        <Sun className="h-5 w-5 transition-transform hover:rotate-12" />
      ) : (
        <Moon className="h-5 w-5 transition-transform hover:-rotate-12" />
      )}
    </button>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd /home/wcqqq21/finance-agent/frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 3: Commit ThemeToggle**

```bash
cd /home/wcqqq21/finance-agent
git add frontend/src/components/layout/ThemeToggle.tsx
git commit -m "feat: add ThemeToggle button component"
```

---

### Task 4: Update Layout with ThemeProvider

**Files:**
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Add ThemeProvider to layout**

Modify `/home/wcqqq21/finance-agent/frontend/src/app/layout.tsx`:

```typescript
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { ThemeProvider } from "@/components/providers/ThemeProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Finance Agent",
  description: "Multi-agent financial analysis system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          storageKey="finance-agent-theme"
          disableTransitionOnChange={false}
        >
          <Navbar />
          <main className="flex-1 container mx-auto px-4 py-8">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd /home/wcqqq21/finance-agent/frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 3: Commit layout changes**

```bash
cd /home/wcqqq21/finance-agent
git add frontend/src/app/layout.tsx
git commit -m "feat: integrate ThemeProvider in root layout"
```

---

### Task 5: Update Navbar with ThemeToggle

**Files:**
- Modify: `frontend/src/components/layout/Navbar.tsx`

- [ ] **Step 1: Add ThemeToggle to Navbar**

Modify `/home/wcqqq21/finance-agent/frontend/src/components/layout/Navbar.tsx`:

```typescript
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { ThemeToggle } from './ThemeToggle';

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/query', label: 'Query' },
  { href: '/reports', label: 'Reports' },
  { href: '/system', label: 'System' },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b bg-background">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="text-xl font-bold">
              Finance Agent
            </Link>
            <div className="flex gap-6">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'text-sm font-medium transition-colors hover:text-primary',
                    pathname === item.href
                      ? 'text-foreground'
                      : 'text-muted-foreground'
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd /home/wcqqq21/finance-agent/frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 3: Commit Navbar changes**

```bash
cd /home/wcqqq21/finance-agent
git add frontend/src/components/layout/Navbar.tsx
git commit -m "feat: add ThemeToggle button to Navbar"
```

---

### Task 6: Verify Production Build

**Files:**
- Build: All components

- [ ] **Step 1: Run production build**

```bash
cd /home/wcqqq21/finance-agent/frontend
npm run build
```

Expected: Build completes successfully with no errors

- [ ] **Step 2: Check for hydration warnings**

Review build output for any hydration mismatch warnings.

Expected: No hydration warnings (suppressHydrationWarning should prevent them)

- [ ] **Step 3: Test production build locally**

```bash
npm run start
```

Visit http://localhost:3000 and verify theme toggle works in production mode.

Expected: Theme toggle functions correctly in production build

---

### Task 7: Manual Testing - Basic Functionality

**Files:**
- Test: All components in browser

- [ ] **Step 1: Start development server**

```bash
cd /home/wcqqq21/finance-agent/frontend
npm run dev
```

Expected: Server starts on http://localhost:3000

- [ ] **Step 2: Test first visit with dark system theme**

1. Open browser DevTools → Application → Local Storage
2. Clear `finance-agent-theme` key if exists
3. Set system to dark mode (OS settings)
4. Visit http://localhost:3000
5. Verify: App loads in dark mode, no flash

Expected: Dark mode applied immediately

- [ ] **Step 3: Test first visit with light system theme**

1. Clear localStorage `finance-agent-theme`
2. Set OS to light mode
3. Refresh page
4. Verify: App loads in light mode

Expected: Light mode applied immediately

- [ ] **Step 4: Test manual toggle from dark to light**

1. Set system to dark mode, clear localStorage
2. Visit page (should be dark)
3. Click theme toggle button
4. Verify: Theme switches to light mode
5. Verify: Icon changes from sun to moon
6. Verify: Smooth transition

Expected: Toggle works smoothly

- [ ] **Step 5: Test manual toggle from light to dark**

1. Click toggle again
2. Verify: Theme switches back to dark mode
3. Verify: Icon changes from moon to sun

Expected: Toggle works in both directions

- [ ] **Step 6: Test persistence**

1. Set theme to light mode
2. Refresh page
3. Verify: Theme remains light
4. Check localStorage: `finance-agent-theme` = "light"

Expected: Preference persists across refreshes

- [ ] **Step 7: Test system theme independence**

1. Manually set theme to light
2. Change OS to dark mode
3. Refresh page
4. Verify: App stays in light mode (ignores system)

Expected: Manual preference overrides system

- [ ] **Step 8: Test system theme following after clear**

1. Clear localStorage `finance-agent-theme`
2. Set OS to light mode
3. Refresh page
4. Verify: App loads in light mode
5. Change OS to dark mode
6. Refresh page
7. Verify: App loads in dark mode

Expected: Follows system when no manual preference

---

### Task 8: Manual Testing - Accessibility

**Files:**
- Test: Accessibility features

- [ ] **Step 1: Test keyboard navigation**

1. Tab to theme toggle button
2. Verify: Focus ring visible
3. Press Enter
4. Verify: Theme toggles

Expected: Fully keyboard accessible

- [ ] **Step 2: Test aria-label in dark mode**

1. Set theme to dark mode
2. Inspect theme toggle button
3. Verify: aria-label="切换到浅色模式"

Expected: Correct aria-label for current state

- [ ] **Step 3: Test aria-label in light mode**

1. Set theme to light mode
2. Inspect theme toggle button
3. Verify: aria-label="切换到暗黑模式"

Expected: Correct aria-label for current state

- [ ] **Step 4: Test with screen reader (if available)**

1. Enable screen reader
2. Navigate to theme toggle
3. Verify: Announces correct action

Expected: Screen reader announces button purpose

---

### Task 9: Manual Testing - Edge Cases

**Files:**
- Test: Edge case scenarios

- [ ] **Step 1: Test rapid switching**

1. Click toggle button rapidly 10 times
2. Verify: No errors in console
3. Verify: Theme state remains consistent

Expected: Handles rapid clicks gracefully

- [ ] **Step 2: Test with JavaScript disabled**

1. Disable JavaScript in browser
2. Visit page
3. Verify: Shows default light theme (CSS :root)

Expected: Graceful degradation to light theme

- [ ] **Step 3: Test localStorage quota (simulated)**

Note: next-themes automatically handles localStorage failures by falling back to in-memory storage. Verify no errors in console if localStorage is unavailable.

Expected: No console errors, theme works in-memory

- [ ] **Step 4: Document any issues found**

If any bugs or issues were discovered during testing, document them clearly with steps to reproduce.

Expected: All tests pass or issues documented for fixing

---

### Task 10: Fix Any Issues Found

**Files:**
- Fix: Any files with issues discovered during testing

- [ ] **Step 1: Review documented issues**

Review any issues found in Task 7-9.

- [ ] **Step 2: Fix each issue separately**

For each issue:
1. Fix the code
2. Test the fix
3. Commit with descriptive message: `fix: [specific issue description]`

Expected: Each fix is committed separately with clear message

- [ ] **Step 3: Re-run affected tests**

After fixes, re-run the relevant test scenarios to verify fixes work.

Expected: All tests now pass

---

### Task 11: Final Verification and Cleanup

### Task 11: Final Verification and Cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run final TypeScript check**

```bash
cd /home/wcqqq21/finance-agent/frontend
npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 2: Run linter**

```bash
npm run lint
```

Expected: No linting errors

- [ ] **Step 3: Check for console.log statements**

```bash
cd /home/wcqqq21/finance-agent/frontend
grep -r "console\.log" src/components/providers/ src/components/layout/ThemeToggle.tsx
```

Expected: No console.log statements found (or only intentional ones)

- [ ] **Step 4: Verify all imports are used**

Review each new file to ensure no unused imports.

Expected: All imports are necessary

- [ ] **Step 5: Verify all changes committed**

```bash
cd /home/wcqqq21/finance-agent
git status
```

Expected: Working tree clean

- [ ] **Step 6: Review commit history**

```bash
git log --oneline -10
```

Expected: Clear, descriptive commit messages for all changes

---

## Rollback Instructions

If critical issues are found and you need to rollback:

```bash
cd /home/wcqqq21/finance-agent
# Count commits made during this implementation
git log --oneline | head -10

# Rollback N commits (replace N with actual number)
git reset --hard HEAD~N

# Or rollback to specific commit
git reset --hard <commit-hash>
```

---

## Testing Checklist Summary

From spec document `docs/superpowers/specs/2026-03-19-dark-mode-theme-toggle-design.md`:

**First Visit:**
- [ ] System in dark mode → app loads in dark mode
- [ ] System in light mode → app loads in light mode
- [ ] No theme flicker on page load

**Manual Toggle:**
- [ ] Click toggle in dark mode → switches to light
- [ ] Click toggle in light mode → switches to dark
- [ ] Icon updates correctly (sun in dark, moon in light)
- [ ] Smooth transition between themes

**Persistence:**
- [ ] Manually switch theme → refresh page → theme persists
- [ ] Change system theme → app ignores it (after manual switch)
- [ ] Clear localStorage → app follows system theme again

**Accessibility:**
- [ ] Button has proper aria-label describing the action
- [ ] Keyboard accessible (Tab + Enter)
- [ ] Screen reader announces button purpose
- [ ] Focus visible indicator present

**Edge Cases:**
- [ ] Rapid theme switching doesn't cause issues
- [ ] localStorage quota exceeded handled gracefully (next-themes handles this)
- [ ] JavaScript disabled shows default light theme (CSS :root)

---

## Notes

- All CSS variables already defined in `src/app/globals.css` - no changes needed
- Tailwind CSS v4 custom variant `@custom-variant dark (&:is(.dark *));` works with next-themes
- next-themes automatically injects inline script to prevent FOUC
- ThemeProvider must be client component but doesn't affect SSR
- suppressHydrationWarning on `<html>` prevents Next.js warnings
