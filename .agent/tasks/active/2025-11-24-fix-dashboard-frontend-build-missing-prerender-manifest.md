# Fix Dashboard Frontend Build - Missing prerender-manifest.json

## Issue Summary
The Next.js frontend fails to start in production mode with error:
```
Error: ENOENT: no such file or directory, open '...\.next\prerender-manifest.json'
```

## Root Causes
1. Build errors during static page generation prevent `prerender-manifest.json` from being created
2. The `Toaster` component uses `useTheme()` from `next-themes` but there's no `ThemeProvider` in the app
3. Static generation fails for all pages that use context hooks during build time

## Technical Details
- Error: "Cannot read properties of null (reading 'useContext')"
- Affected files: `components/ui/sonner.tsx`, all pages
- The `useTheme()` hook is called without a `ThemeProvider` wrapper
- During build-time pre-rendering, React context is null

## Solution
Add `ThemeProvider` from `next-themes` to the root layout to properly wrap the application and provide theme context to all components.

## Implementation Steps
1. Update `dashboard/app/layout.tsx` to include `ThemeProvider`
2. Clean the `.next` directory to ensure fresh build
3. Rebuild with `npm run build`
4. Verify `prerender-manifest.json` exists and frontend loads correctly

## Expected Outcome
- Next.js build completes successfully without errors
- Production build includes all necessary files including `prerender-manifest.json`
- Frontend loads correctly at http://localhost:3000
