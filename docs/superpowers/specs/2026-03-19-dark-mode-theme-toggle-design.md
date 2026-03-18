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
app/
├── layout.tsx (modified)
│   └── Wraps children with ThemeProvider
├── components/
│   ├── layout/
│   │   ├── Navbar.tsx (modified)
│   │   │   └── Adds ThemeToggle button
│   │   └── ThemeToggle.tsx (new)
│   │       └── Theme switch button component
│   └── providers/
│       └── ThemeProvider.tsx (new)
│           └── Wraps next-themes provider
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

- **next-themes** (^0.3.0): Theme management library for Next.js
  - Handles SSR/CSR synchronization
  - Provides React hooks for theme state
  - Manages localStorage persistence
  - Prevents FOUC with inline script injection

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
- Displays icon based on current resolved theme:
  - Dark mode → Sun icon (clicking switches to light)
  - Light mode → Moon icon (clicking switches to dark)
- Icons from `lucide-react` (already installed)
- Styled with shadcn/ui Button component for consistency
- Includes hover effects and smooth transitions

**Button Behavior**:
- Click handler: `setTheme(theme === 'dark' ? 'light' : 'dark')`
- This explicit setting overrides system preference
- Aria-label: "切换主题" for accessibility

### Integration Points

**layout.tsx Changes**:
- Import and wrap children with ThemeProvider
- No changes to existing `<html>` structure
- ThemeProvider handles class injection

**Navbar.tsx Changes**:
- Add ThemeToggle component to right side of navbar
- Position using flexbox: `justify-between` with toggle on the right
- Maintains existing navigation items on the left

### CSS Compatibility

**Existing Styles** (globals.css):
- Already defines `:root` variables for light theme
- Already defines `.dark` class variables for dark theme
- Uses oklch color space for smooth transitions
- No modifications needed to existing CSS

**Theme Switching Mechanism**:
- next-themes adds/removes `.dark` class on `<html>`
- CSS variables automatically update via cascade
- All components using Tailwind classes (e.g., `bg-background`, `text-foreground`) automatically adapt

## Error Handling

1. **localStorage Unavailable**: next-themes gracefully falls back to in-memory storage
2. **System Theme Detection Fails**: Defaults to light theme
3. **Hydration Mismatch**: next-themes suppresses hydration warnings with proper SSR handling

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
   - [ ] Button has proper aria-label
   - [ ] Keyboard accessible (Tab + Enter)
   - [ ] Screen reader announces button purpose

5. **Cross-Browser**:
   - [ ] Works in Chrome, Firefox, Safari, Edge
   - [ ] Works on mobile browsers

## Implementation Steps

1. Install next-themes package
2. Create ThemeProvider wrapper component
3. Create ThemeToggle button component
4. Modify layout.tsx to include ThemeProvider
5. Modify Navbar.tsx to include ThemeToggle
6. Test all scenarios from checklist
7. Commit changes

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
