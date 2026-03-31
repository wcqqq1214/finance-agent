# Trend Color Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在设置页面添加涨跌色模式切换（绿涨红跌 / 红涨绿跌），通过 CSS 变量覆盖实现，业务组件零改动。

**Architecture:** 新增 `TrendColorProvider` 管理 `trendMode` 状态，持久化到 localStorage，切换时在 `<html>` 上 toggle `.cn-mode` class。`globals.css` 中 `.cn-mode` 和 `.dark.cn-mode` 覆盖涨跌色 CSS 变量，所有消费这些变量的组件自动响应。`layout.tsx` 注入防 FOUC blocking script，Settings 页面新增 Display Preferences Card。

**Tech Stack:** Next.js App Router, React Context, shadcn/ui Switch, CSS custom properties, localStorage

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/lib/trend-color-constants.ts` | Create | 共享常量：localStorage key、CSS class 名 |
| `frontend/src/components/providers/TrendColorProvider.tsx` | Create | Context + localStorage + isMounted |
| `frontend/src/hooks/use-trend-color.ts` | Create | 消费 Context 的 hook |
| `frontend/src/app/globals.css` | Modify | 新增 `.cn-mode` / `.dark.cn-mode` CSS 变量覆盖 |
| `frontend/src/app/layout.tsx` | Modify | 注册 TrendColorProvider + 注入 blocking script |
| `frontend/src/app/settings/page.tsx` | Modify | 新增 Display Preferences Card |

---

## Task 1: 常量文件

**Files:**
- Create: `frontend/src/lib/trend-color-constants.ts`

- [ ] **Step 1: 创建常量文件**

```ts
// frontend/src/lib/trend-color-constants.ts
export const TREND_COLOR_KEY = "trend-color-mode";
export const TREND_COLOR_CN_CLASS = "cn-mode";
export type TrendMode = "western" | "chinese";
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/trend-color-constants.ts
git commit -m "feat(trend-color): add shared constants"
```

---

## Task 2: CSS 变量覆盖

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: 在 globals.css 末尾追加 `.cn-mode` 和 `.dark.cn-mode` 规则**

在文件末尾（`@layer utilities` 块之后）追加：

```css
/* Trend color mode: Chinese convention (red=up, green=down) */
.cn-mode {
  --chart-up: 0 84.2% 60.2%;
  --chart-down: 142.1 76.2% 36.3%;
  --chart-up-js: hsl(0deg, 84.2%, 60.2%);
  --chart-down-js: hsl(142.1deg, 76.2%, 36.3%);
  --chart-up-js-alpha: hsla(0deg, 84.2%, 60.2%, 0.6);
  --chart-down-js-alpha: hsla(142.1deg, 76.2%, 36.3%, 0.6);
}

.dark.cn-mode {
  --chart-up: 0 72.2% 50.6%;
  --chart-down: 142.1 70.6% 45.3%;
  --chart-up-js: hsl(0deg, 72.2%, 50.6%);
  --chart-down-js: hsl(142.1deg, 70.6%, 45.3%);
  --chart-up-js-alpha: hsla(0deg, 72.2%, 50.6%, 0.6);
  --chart-down-js-alpha: hsla(142.1deg, 70.6%, 45.3%, 0.6);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "feat(trend-color): add cn-mode CSS variable overrides"
```

---

## Task 3: TrendColorProvider

**Files:**
- Create: `frontend/src/components/providers/TrendColorProvider.tsx`

- [ ] **Step 1: 创建 Provider**

```tsx
"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { TREND_COLOR_KEY, TREND_COLOR_CN_CLASS, type TrendMode } from "@/lib/trend-color-constants";

interface TrendColorContextValue {
  trendMode: TrendMode;
  setTrendMode: (mode: TrendMode) => void;
  isMounted: boolean;
}

const TrendColorContext = createContext<TrendColorContextValue>({
  trendMode: "western",
  setTrendMode: () => {},
  isMounted: false,
});

export function TrendColorProvider({ children }: { children: React.ReactNode }) {
  const [trendMode, setTrendModeState] = useState<TrendMode>("western");
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(TREND_COLOR_KEY) as TrendMode | null;
    if (stored === "chinese" || stored === "western") {
      setTrendModeState(stored);
    }
    setIsMounted(true);
  }, []);

  const setTrendMode = (mode: TrendMode) => {
    setTrendModeState(mode);
    localStorage.setItem(TREND_COLOR_KEY, mode);
    if (mode === "chinese") {
      document.documentElement.classList.add(TREND_COLOR_CN_CLASS);
    } else {
      document.documentElement.classList.remove(TREND_COLOR_CN_CLASS);
    }
  };

  return (
    <TrendColorContext.Provider value={{ trendMode, setTrendMode, isMounted }}>
      {children}
    </TrendColorContext.Provider>
  );
}

export function useTrendColor() {
  return useContext(TrendColorContext);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/providers/TrendColorProvider.tsx
git commit -m "feat(trend-color): add TrendColorProvider with localStorage persistence"
```

---

## Task 4: use-trend-color hook

**Files:**
- Create: `frontend/src/hooks/use-trend-color.ts`

- [ ] **Step 1: 创建 hook 文件（re-export，保持 hooks 目录统一入口）**

```ts
// frontend/src/hooks/use-trend-color.ts
export { useTrendColor } from "@/components/providers/TrendColorProvider";
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/use-trend-color.ts
git commit -m "feat(trend-color): add use-trend-color hook"
```

---

## Task 5: layout.tsx — 注册 Provider + blocking script

**Files:**
- Modify: `frontend/src/app/layout.tsx`

当前 `layout.tsx` 已有 `suppressHydrationWarning`，无需再加。

- [ ] **Step 1: 在 `<head>` 中添加 blocking script，在 `ThemeProvider` 内侧包裹 `TrendColorProvider`**

将 `layout.tsx` 修改为：

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { TrendColorProvider } from "@/components/providers/TrendColorProvider";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Q-Agents",
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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem('trend-color-mode')==='chinese')document.documentElement.classList.add('cn-mode')}catch(e){}`,
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          storageKey="finance-agent-theme"
          disableTransitionOnChange={false}
        >
          <TrendColorProvider>
            <Navbar />
            <main className="container mx-auto flex-1 px-4 py-8">{children}</main>
            <Toaster />
          </TrendColorProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: 运行 lint 检查**

```bash
cd frontend && pnpm lint
```

Expected: 无新增错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/layout.tsx
git commit -m "feat(trend-color): register TrendColorProvider and add anti-FOUC script"
```

---

## Task 6: Settings 页面 — Display Preferences Card

**Files:**
- Modify: `frontend/src/app/settings/page.tsx`

- [ ] **Step 1: 在 settings/page.tsx 中引入 hook 和 Switch，新增 Display Preferences Card**

在现有 import 区域末尾追加：

```tsx
import { Switch } from "@/components/ui/switch";
import { useTrendColor } from "@/hooks/use-trend-color";
```

在 `SettingsPage` 组件内，`const { toast } = useToast();` 下方追加：

```tsx
const { trendMode, setTrendMode, isMounted } = useTrendColor();
```

在 `</div>` 闭合（`space-y-6` 容器）内、Save 按钮 `<div>` 之前，追加新 Card：

```tsx
<Card>
  <CardHeader>
    <CardTitle>Display Preferences</CardTitle>
    <CardDescription>配置图表涨跌颜色习惯</CardDescription>
  </CardHeader>
  <CardContent>
    <div className="flex items-center justify-between">
      <div className="space-y-0.5">
        <Label>涨跌色模式</Label>
        <p className="text-sm text-muted-foreground">
          {!isMounted ? "加载中..." : trendMode === "chinese" ? "🇨🇳 红涨绿跌（Chinese）" : "🌍 绿涨红跌（Western）"}
        </p>
      </div>
      <Switch
        disabled={!isMounted}
        checked={isMounted ? trendMode === "chinese" : false}
        onCheckedChange={(checked) => setTrendMode(checked ? "chinese" : "western")}
        aria-label="切换涨跌色模式"
      />
    </div>
  </CardContent>
</Card>
```

- [ ] **Step 2: 运行 lint 和类型检查**

```bash
cd frontend && pnpm lint && pnpm type-check
```

Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/settings/page.tsx
git commit -m "feat(trend-color): add Display Preferences card in settings"
```

---

## Self-Review

**Spec coverage:**
- ✅ `.cn-mode` / `.dark.cn-mode` CSS 变量覆盖 → Task 2
- ✅ `TREND_COLOR_KEY` / `TREND_COLOR_CN_CLASS` 常量 → Task 1
- ✅ `TrendColorProvider` + `isMounted` + localStorage → Task 3
- ✅ `use-trend-color` hook → Task 4
- ✅ blocking script + `suppressHydrationWarning`（已存在）→ Task 5
- ✅ Settings Display Preferences Card + Switch 禁用态 → Task 6

**Placeholder scan:** 无 TBD/TODO，所有步骤含完整代码。

**Type consistency:**
- `TrendMode` 定义于 Task 1 (`trend-color-constants.ts`)，Task 3 中 import 使用，一致。
- `useTrendColor()` 定义于 Task 3，Task 4 re-export，Task 6 消费，一致。
- `isMounted` 在 Task 3 Provider 中定义并暴露，Task 6 中解构使用，一致。
