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

### Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install next-themes package**

```bash
cd frontend
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
git add package.json package-lock.json
git commit -m "chore: add next-themes for theme management"
```

---

### Task 2: Create ThemeProvider Component

**Files:**
- Create: `frontend/src/components/providers/ThemeProvider.tsx`

- [ ] **Step 1: Create providers directory**

```bash
mkdir -p frontend/src/components/providers
```

- [ ] **Step 2: Create ThemeProvider component**

Create `frontend/src/components/providers/ThemeProvider.tsx`:

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
cd frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 4: Commit ThemeProvider**

```bash
git add src/components/providers/ThemeProvider.tsx
git commit -m "feat: add ThemeProvider wrapper component"
```

---

### Task 3: Create ThemeToggle Component

**Files:**
- Create: `frontend/src/components/layout/ThemeToggle.tsx`

- [ ] **Step 1: Create ThemeToggle component**

Create `frontend/src/components/layout/ThemeToggle.tsx`:

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
cd frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 3: Commit ThemeToggle**

```bash
git add src/components/layout/ThemeToggle.tsx
git commit -m "feat: add ThemeToggle button component"
```

---

### Task 4: Update Layout with ThemeProvider

**Files:**
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Add ThemeProvider to layout**

Modify `frontend/src/app/layout.tsx`:

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
cd frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 3: Commit layout changes**

```bash
git add src/app/layout.tsx
git commit -m "feat: integrate ThemeProvider in root layout"
```

---

### Task 5: Update Navbar with ThemeToggle

**Files:**
- Modify: `frontend/src/components/layout/Navbar.tsx`

- [ ] **Step 1: Add ThemeToggle to Navbar**

Modify `frontend/src/components/layout/Navbar.tsx`:

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
cd frontend
npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 3: Commit Navbar changes**

```bash
git add src/components/layout/Navbar.tsx
git commit -m "feat: add ThemeToggle button to Navbar"
```

---

### Task 6: Manual Testing

**Files:**
- Test: All components in browser

- [ ] **Step 1: Start development server**

```bash
cd frontend
npm run dev
```

Expected: Server starts on http://localhost:3000

- [ ] **Step 2: Test first visit behavior**

1. Open browser DevTools → Application → Local Storage
2. Clear `finance-agent-theme` key if exists
3. Set system to dark mode (OS settings)
4. Visit http://localhost:3000
5. Verify: App loads in dark mode, no flash

Expected: Dark mode applied immediately

- [ ] **Step 3: Test manual toggle**

1. Click theme toggle button in navbar
2. Verify: Theme switches to light mode
3. Verify: Icon changes from sun to moon
4. Verify: Smooth transition
5. Click again
6. Verify: Theme switches back to dark mode

Expected: Toggle works smoothly in both directions

- [ ] **Step 4: Test persistence**

1. Set theme to light mode
2. Refresh page
3. Verify: Theme remains light
4. Check localStorage: `finance-agent-theme` = "light"

Expected: Preference persists across refreshes

- [ ] **Step 5: Test system theme independence**

1. Manually set theme to light
2. Change OS to dark mode
3. Refresh page
4. Verify: App stays in light mode (ignores system)

Expected: Manual preference overrides system

- [ ] **Step 6: Test system theme following**

1. Clear localStorage `finance-agent-theme`
2. Set OS to light mode
3. Refresh page
4. Verify: App loads in light mode
5. Change OS to dark mode
6. Refresh page
7. Verify: App loads in dark mode

Expected: Follows system when no manual preference

- [ ] **Step 7: Test accessibility**

1. Tab to theme toggle button
2. Verify: Focus ring visible
3. Press Enter
4. Verify: Theme toggles
5. Use screen reader
6. Verify: Announces "切换到浅色模式" or "切换到暗黑模式"

Expected: Fully keyboard accessible with proper labels

- [ ] **Step 8: Test rapid switching**

1. Click toggle button rapidly 10 times
2. Verify: No errors in console
3. Verify: Theme state remains consistent

Expected: Handles rapid clicks gracefully

- [ ] **Step 9: Document test results**

Create a test report noting any issues found during manual testing.

Expected: All tests pass or issues documented for fixing

---

### Task 7: Final Commit and Cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run final TypeScript check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 2: Run linter**

```bash
cd frontend
npm run lint
```

Expected: No linting errors (or fix any that appear)

- [ ] **Step 3: Verify all changes committed**

```bash
git status
```

Expected: Working tree clean

- [ ] **Step 4: Create summary commit if needed**

If there were any fixes during testing:

```bash
git add .
git commit -m "fix: address theme toggle testing issues"
```

- [ ] **Step 5: Update plan status**

Mark this plan as completed in the plan document.

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
