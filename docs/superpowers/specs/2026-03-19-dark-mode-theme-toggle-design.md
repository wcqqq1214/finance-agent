# Dark Mode Theme Toggle Design

**Date:** 2026-03-19
**Status:** Approved
**Author:** Claude (Kiro)

## Overview

Implement a theme toggle system for the Finance Agent frontend that defaults to following the system theme preference, with a manual toggle button in the navigation bar. Once users manually switch themes, their preference is saved and no longer follows system changes.

## Requirements

### Functional Requirements

1. **System Theme Detection**: On first visit, automatically detect and apply the user's system theme preference (light or dark)
2. **Manual Override**: Provide a toggle button in the navbar that allows users to switch between light and dark modes
3. **Preference Persistence**: Save user's manual theme choice to localStorage and respect it on subsequent visits
4. **Smart Following**: Only follow system theme when no user preference is stored; once user manually switches, stop following system
5. **Visual Feedback**: Display appropriate icon (sun/moon) indicating the next state the button will switch to

### Non-Functional Requirements

1. **No Flash**: Prevent theme flicker on page load (FOUC - Flash of Unstyled Content)
2. **SSR Compatible**: Work correctly with Next.js server-side rendering
3. **Accessibility**: Include proper ARIA labels for screen readers
4. **Performance**: Minimal runtime overhead, theme applied before first paint

## Architecture

### Component Structure

```
src/
├── app/
│   └── layout.tsx (modified)
│       └── Wraps children with ThemeProvider
│       └── Add suppressHydrationWarning to <html>
├── components/
│   ├── layout/
│   │   ├── Navbar.tsx (modified)
│   │   │   └── Adds ThemeToggle button to right side
│   │   └── ThemeToggle.tsx (new)
│   │       └── Theme switch button component
│   └── providers/
│       └── ThemeProvider.tsx (new)
│           └── Client component wrapping next-themes provider
```

### Data Flow

1. **Initial Load**:
   - ThemeProvider checks localStorage for saved preference
   - If no preference found: detect system theme via `prefers-color-scheme`
   - Apply theme class to `<html>` element before render
   - CSS variables automatically switch based on `.dark` class

2. **User Interaction**:
   - User clicks ThemeToggle button
   - `setTheme()` updates theme state
   - Theme class on `<html>` updates
   - Preference saved to localStorage with key `finance-agent-theme`
   - System theme following is disabled

3. **Subsequent Visits**:
   - ThemeProvider reads localStorage
   - Applies saved preference
   - System theme is ignored

## Technical Implementation

### Dependencies

- **next-themes** (latest): Theme management library for Next.js
  - Handles SSR/CSR synchronization
  - Provides React hooks for theme state
  - Manages localStorage persistence
  - Prevents FOUC with inline script injection
  - Compatible with Next.js 16 and Tailwind CSS v4

### Configuration

**ThemeProvider Settings**:
```typescript
{
  attribute: "class",              // Use class-based theme switching
  defaultTheme: "system",          // Default to system preference
  enableSystem: true,              // Enable system theme detection
  storageKey: "finance-agent-theme", // localStorage key
  disableTransitionOnChange: false // Allow smooth transitions
}
```

### Component Design

**ThemeToggle Component**:
- Uses `useTheme()` hook from next-themes
  - Returns: `{ theme, setTheme, resolvedTheme, systemTheme }`
  - Use `resolvedTheme` to get actual theme when `theme === 'system'`
- Displays icon based on current resolved theme:
  - Dark mode → Sun icon (clicking switches to light)
  - Light mode → Moon icon (clicking switches to dark)
- Icons from `lucide-react` (already installed)
- Styled as icon button for consistency
- Includes hover effects and smooth transitions
- Must be a client component (`'use client'` directive)

**Button Behavior**:
- Click handler: `setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')`
- This explicit setting overrides system preference
- Aria-label: "切换到浅色模式" or "切换到暗黑模式" (describes the action, not just "toggle theme")

### Integration Points

**layout.tsx Changes**:
- Import and wrap children with ThemeProvider
- Add `suppressHydrationWarning` to `<html>` tag to prevent Next.js hydration warnings
- Example: `<html lang="en" suppressHydrationWarning>`
- ThemeProvider handles class injection via inline script

**Navbar.tsx Changes**:
- Add ThemeToggle component to right side of navbar
- The navbar already uses `justify-between`, add toggle to the right section
- Maintains existing navigation items on the left

**ThemeProvider Implementation**:
- Must use `'use client'` directive (uses React context and hooks)
- Wraps the next-themes `ThemeProvider` component
- This doesn't affect SSR - theme is still applied server-side via inline script

### CSS Compatibility

**Existing Styles** (src/app/globals.css):
- Already defines `:root` variables for light theme
- Already defines `.dark` class variables for dark theme
- Uses oklch color space for smooth transitions
- Uses Tailwind CSS v4 syntax: `@custom-variant dark (&:is(.dark *));`
- No modifications needed to existing CSS

**Tailwind CSS v4 Compatibility**:
- Tailwind v4 uses CSS-based configuration (no config file)
- The custom variant `@custom-variant dark (&:is(.dark *));` works with next-themes
- next-themes adds/removes `.dark` class on `<html>` element
- The custom variant selector matches any element inside `.dark` parent

**Theme Switching Mechanism**:
- next-themes adds/removes `.dark` class on `<html>`
- CSS variables automatically update via cascade
- All components using Tailwind classes (e.g., `bg-background`, `text-foreground`) automatically adapt

## Error Handling

1. **localStorage Unavailable**: next-themes gracefully falls back to in-memory storage
2. **localStorage Quota Exceeded**: Falls back to in-memory storage
3. **System Theme Detection Fails**: Defaults to light theme
4. **Hydration Mismatch**: next-themes suppresses hydration warnings with proper SSR handling
5. **JavaScript Disabled**: App defaults to light theme (CSS `:root` variables)

## Testing Strategy

### Manual Testing Checklist

1. **First Visit**:
   - [ ] System in dark mode → app loads in dark mode
   - [ ] System in light mode → app loads in light mode
   - [ ] No theme flicker on page load

2. **Manual Toggle**:
   - [ ] Click toggle in dark mode → switches to light
   - [ ] Click toggle in light mode → switches to dark
   - [ ] Icon updates correctly (sun in dark, moon in light)
   - [ ] Smooth transition between themes

3. **Persistence**:
   - [ ] Manually switch theme → refresh page → theme persists
   - [ ] Change system theme → app ignores it (after manual switch)
   - [ ] Clear localStorage → app follows system theme again

4. **Accessibility**:
   - [ ] Button has proper aria-label describing the action
   - [ ] Keyboard accessible (Tab + Enter)
   - [ ] Screen reader announces button purpose
   - [ ] Focus visible indicator present

5. **Cross-Browser**:
   - [ ] Works in Chrome, Firefox, Safari, Edge
   - [ ] Works on mobile browsers

6. **Edge Cases**:
   - [ ] Rapid theme switching doesn't cause issues
   - [ ] localStorage quota exceeded handled gracefully
   - [ ] JavaScript disabled shows default light theme

## Implementation Steps

1. Install next-themes package
2. Create `src/components/providers/` directory
3. Create ThemeProvider wrapper component
4. Create ThemeToggle button component in `src/components/layout/`
5. Modify layout.tsx to include ThemeProvider and suppressHydrationWarning
6. Modify Navbar.tsx to include ThemeToggle on the right side
7. Test all scenarios from checklist
8. Commit changes

## Future Enhancements (Out of Scope)

- Three-option mode selector (Light / Dark / System)
- Custom theme colors beyond light/dark
- Per-page theme overrides
- Animated theme transitions with view transitions API
- Theme preview before switching

## References

- next-themes documentation: https://github.com/pacocoursey/next-themes
- Next.js 16 documentation
- Tailwind CSS dark mode: https://tailwindcss.com/docs/dark-mode
- shadcn/ui theming: https://ui.shadcn.com/docs/dark-mode
