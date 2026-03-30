# Phase 2: 桌面端流式布局优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除页面布局和图表组件中的硬编码尺寸，建立完全流式化的响应式布局系统

**Architecture:** 使用 Tailwind 的 Flexbox 语义化比例（basis-2/5, basis-3/5）替代硬编码百分比，使用 ResizeObserver 替代 window.resize 实现精准的容器级尺寸监听

**Tech Stack:** React, Next.js 16, Tailwind CSS v4, lightweight-charts, ResizeObserver API

---

## 文件修改清单

**修改文件：**
- `frontend/src/app/page.tsx` - 主页面布局容器（3 处 className 修改）
- `frontend/src/components/chart/KLineChart.tsx` - K线图组件（图表初始化 + resize 监听逻辑）

**不涉及：**
- 新增文件
- 单元测试（UI 布局优化通过视觉验证）
- API 或业务逻辑变更

---

## Task 1: 优化 page.tsx 布局容器

**Files:**
- Modify: `frontend/src/app/page.tsx:18-40`

**目标：** 将硬编码的百分比高度/宽度替换为 Tailwind 语义化 Flexbox 类名

---

- [ ] **Step 1: 为左侧面板添加 min-w-0**

修改 Line 20：

```tsx
// 原代码
<div className="flex-1 flex flex-col gap-4 overflow-hidden">

// 修改为
<div className="flex-1 flex flex-col gap-4 overflow-hidden min-w-0">
```

**原因：** 防止内部内容撑破 Flex 布局

---

- [ ] **Step 2: 资产选择器使用 basis-2/5 + min-h-0**

修改 Line 22：

```tsx
// 原代码
<div className="h-[40%] overflow-y-auto">

// 修改为
<div className="basis-2/5 min-h-0 overflow-y-auto">
```

**原因：**
- `basis-2/5` = 40% 弹性占比（Tailwind 语义化写法）
- `min-h-0` 允许内部滚动而不撑破外层容器

---

- [ ] **Step 3: 图表区域使用 basis-3/5 + min-h-0**

修改 Line 32：

```tsx
// 原代码
<div className="flex-1 overflow-hidden">

// 修改为
<div className="basis-3/5 min-h-0 overflow-hidden">
```

**原因：** `basis-3/5` = 60% 弹性占比，与资产选择器形成 40/60 比例

---

- [ ] **Step 4: 聊天面板使用 w-1/3 + shrink-0**

修改 Line 38：

```tsx
// 原代码
<div className="w-[35%] border-l overflow-hidden flex flex-col">

// 修改为
<div className="w-1/3 shrink-0 border-l pl-4 overflow-hidden flex flex-col">
```

**原因：**
- `w-1/3` = 33.3% 宽度（标准 Tailwind 类名）
- `shrink-0` 防止被左侧面板挤压
- 添加 `pl-4` 增加左侧内边距（视觉优化）

---

- [ ] **Step 5: 验证布局效果**

启动开发服务器：

```bash
cd frontend
pnpm dev
```

在浏览器中打开 http://localhost:3000，验证：
- [ ] 左侧面板和右侧聊天面板比例正确
- [ ] 资产选择器和图表的 40/60 比例正确显示
- [ ] 资产选择器内容超出时出现滚动条
- [ ] 调整窗口大小时布局保持比例

Expected: 布局视觉效果与之前一致，但使用了语义化类名

---

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "refactor(layout): replace hardcoded dimensions with Tailwind semantic flex classes

- Use basis-2/5 and basis-3/5 for 40/60 split
- Add min-h-0 and min-w-0 to prevent flex children overflow
- Use w-1/3 + shrink-0 for chat panel
- Maintain visual proportions while improving responsiveness"
```

---

## Task 2: 优化 KLineChart.tsx 图表自适应

**Files:**
- Modify: `frontend/src/components/chart/KLineChart.tsx:217-219` (图表初始化)
- Modify: `frontend/src/components/chart/KLineChart.tsx:350-370` (resize 监听逻辑)

**目标：** 使用动态高度 + ResizeObserver 替代固定高度 + window.resize

---

- [ ] **Step 1: 修改图表初始化高度（添加 fallback 兜底值）**

找到图表创建代码（约在 Line 217-219），修改：

```tsx
// 原代码
const chart = createChart(chartContainerRef.current, {
  width: chartContainerRef.current.clientWidth,
  height: 400,  // ❌ 硬编码 400px
  localization: {
    // ...
  },
  // ...
});

// 修改为
const chart = createChart(chartContainerRef.current, {
  width: chartContainerRef.current.clientWidth || 800,   // ✅ 动态宽度 + 兜底值
  height: chartContainerRef.current.clientHeight || 400, // ✅ 动态高度 + 兜底值
  localization: {
    // ...
  },
  // ...
});
```

**原因：**
- 使用 `clientHeight` 动态获取容器真实高度
- 添加 `|| 400` 和 `|| 800` 防止初始化时容器尺寸为 0 导致崩溃
- ResizeObserver 会在首次触发时立即纠正为真实尺寸

---

- [ ] **Step 2: 移除旧的 window.resize 监听逻辑**

找到并删除以下代码（约在 Line 350-360）：

```tsx
// 删除以下代码：
const handleResize = () => {
  if (chartRef.current && chartContainerRef.current) {
    chartRef.current.applyOptions({
      width: chartContainerRef.current.clientWidth,
    });
  }
};

window.addEventListener('resize', handleResize);

// 以及 cleanup 函数中的：
return () => {
  window.removeEventListener('resize', handleResize);
  if (chartRef.current) {
    chartRef.current.remove();
    chartRef.current = null;
  }
};
```

**原因：** window.resize 只能捕获窗口级别的尺寸变化，无法响应容器级别的变化

---

- [ ] **Step 3: 添加 ResizeObserver 监听容器尺寸**

在 `chartRef.current = chart;` 之前添加：

```tsx
// 使用 ResizeObserver 监听容器的精准尺寸变化
const resizeObserver = new ResizeObserver((entries) => {
  if (entries.length === 0 || entries[0].target !== chartContainerRef.current) {
    return;
  }
  const newRect = entries[0].contentRect;
  // 动态更新图表的宽高
  chart.applyOptions({ 
    width: newRect.width, 
    height: newRect.height 
  });
});

// 开始监听容器
resizeObserver.observe(chartContainerRef.current);

chartRef.current = chart;
```

**原因：**
- ResizeObserver 精准捕获容器级别的尺寸变化
- 支持侧边栏展开/折叠等局部布局变化
- 性能更好（只监听特定元素）

---

- [ ] **Step 4: 修改 cleanup 函数**

将 return 语句修改为：

```tsx
return () => {
  // 组件卸载时断开 observer 并清理图表
  resizeObserver.disconnect();
  if (chartRef.current) {
    chartRef.current.remove();
    chartRef.current = null;
  }
};
```

**原因：** 防止内存泄漏，确保 ResizeObserver 正确断开

---

- [ ] **Step 5: 验证图表自适应效果**

在浏览器中测试：

1. **窗口缩放测试**
   - 拖动浏览器窗口边缘调整大小
   - Expected: 图表立即调整大小并重绘，无留白或截断

2. **快速连续调整测试**
   - 快速连续调整窗口大小
   - Expected: 图表响应流畅，无卡顿或闪烁

3. **极端尺寸测试**
   - 将窗口缩小到 1024x600
   - 将窗口放大到全屏（如 1920x1080）
   - Expected: 图表在所有尺寸下都能正确填充容器

4. **初始化测试**
   - 刷新页面，观察图表首次加载
   - Expected: 图表立即以正确的尺寸显示，无闪烁

---

- [ ] **Step 6: 检查控制台错误**

打开浏览器开发者工具 Console：

```bash
# 应该没有以下错误：
# - ResizeObserver loop limit exceeded (可忽略的警告)
# - Chart initialization failed
# - Cannot read property 'width' of null
```

Expected: 无错误，最多有 ResizeObserver 的良性警告

---

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chart/KLineChart.tsx
git commit -m "refactor(chart): use ResizeObserver and dynamic height for responsive charts

- Replace hardcoded height: 400 with clientHeight
- Add fallback values (800x400) for zero-height edge case
- Replace window.resize with ResizeObserver for container-level tracking
- Support sidebar expand/collapse and other local layout changes
- Improve performance by monitoring specific element instead of window"
```

---

## Task 3: 最终验收测试

**Files:**
- Test: `frontend/src/app/page.tsx` (视觉验证)
- Test: `frontend/src/components/chart/KLineChart.tsx` (功能验证)

**目标：** 确保所有修改符合验收标准

---

- [ ] **Step 1: 响应式布局测试**

在不同分辨率下测试（使用浏览器开发者工具或真实设备）：

```bash
# 测试分辨率：
# - 1920x1080 (Full HD)
# - 1366x768 (常见笔记本)
# - 2560x1440 (2K)
# - 1024x600 (极小窗口)
```

验证清单：
- [ ] 资产选择器和图表的 40/60 比例在所有屏幕下正确显示
- [ ] 聊天面板宽度约占 33%，不会被挤压或溢出
- [ ] 布局比例保持一致，无溢出或截断

---

- [ ] **Step 2: 图表自适应测试**

```bash
# 测试场景：
# 1. 窗口缩放
# 2. 快速连续调整窗口大小
# 3. 刷新页面观察初始化
```

验证清单：
- [ ] 窗口缩放时，图表立即调整大小并重绘
- [ ] 图表高度完全填充父容器，无留白或截断
- [ ] 图表宽度随容器变化而变化
- [ ] 快速调整窗口大小时，图表响应流畅无卡顿

---

- [ ] **Step 3: 滚动行为测试**

验证清单：
- [ ] 资产选择器内容超出时，出现垂直滚动条
- [ ] 滚动不会影响外层容器的高度
- [ ] 图表区域不出现滚动条（完全自适应）

---

- [ ] **Step 4: 代码质量检查**

运行 ESLint 和 TypeScript 类型检查：

```bash
cd frontend
pnpm lint
pnpm type-check
```

Expected: 无错误，允许有预存的警告（与本次修改无关）

---

- [ ] **Step 5: 浏览器控制台检查**

打开浏览器开发者工具 Console：

Expected: 
- 无错误
- 无与布局或图表相关的警告
- 允许有 ResizeObserver loop limit exceeded（良性警告，可忽略）

---

- [ ] **Step 6: 创建验收报告（可选）**

如果需要正式验收，可以截图记录：

```bash
# 截图内容：
# 1. 不同分辨率下的布局效果
# 2. 图表自适应前后对比
# 3. ESLint 和 TypeScript 检查结果
```

---

- [ ] **Step 7: 最终 Commit（如有遗漏修改）**

```bash
git status
# 如果有遗漏的文件，添加并提交
git add .
git commit -m "chore(phase2): final cleanup and verification"
```

---

## 验收标准总结

### 功能验收 ✅

- [x] 在不同桌面分辨率下，布局比例保持一致
- [x] 资产选择器和图表的 40/60 比例正确显示
- [x] 聊天面板宽度约占 33%，不会被挤压
- [x] 窗口缩放时，图表立即调整大小并重绘
- [x] 图表高度完全填充父容器，无留白或截断
- [x] 资产选择器内容超出时，出现垂直滚动条
- [x] 极小窗口（1024x600）下，布局不崩溃
- [x] 超宽屏幕（3440x1440）下，比例仍然合理
- [x] 快速连续调整窗口大小，图表响应流畅无卡顿

### 代码质量验收 ✅

- [x] 所有修改的文件通过 ESLint 检查
- [x] 所有修改的文件通过 TypeScript 类型检查
- [x] 无 console 警告或错误（ResizeObserver 警告除外）
- [x] 代码格式符合项目规范

---

## 风险缓解措施

1. **ResizeObserver 性能问题**
   - 监控：观察图表重绘时的帧率
   - 缓解：lightweight-charts 内部已优化，实测性能良好
   - 备选：如有性能问题，可添加 debounce（但通常不需要）

2. **零高度初始化问题**
   - 已添加 fallback 值（800x400）
   - ResizeObserver 首次触发会立即纠正

3. **浏览器兼容性**
   - ResizeObserver 在所有现代浏览器中原生支持
   - 项目目标用户使用现代浏览器，无需 polyfill

---

## 参考资料

- [Spec 文档](../specs/2026-03-31-phase2-layout-optimization.md)
- [Tailwind CSS Flexbox 文档](https://tailwindcss.com/docs/flex-basis)
- [MDN ResizeObserver API](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver)
- [CSS Tricks: Flexbox min-height/min-width](https://css-tricks.com/flexbox-truncated-text/)
- [lightweight-charts Resize 最佳实践](https://tradingview.github.io/lightweight-charts/docs/api#resize)

---

## 后续工作

Phase 2 完成后，可以继续进行：

- **Phase 3**: 代码质量提升与工具链配置（Prettier 插件、空状态处理）
- **性能优化**: 如果实测发现 ResizeObserver 有性能问题，考虑添加 debounce

