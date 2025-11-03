## Overview

Move `dashboard/public/assets` to project root as `assets/`, making it accessible for both the Discord bot and dashboard. Update all code references to the new location and filenames.

## Current State

**Existing Structure:**
- `dashboard/public/assets/Logo2.png` - Current dashboard logo
- Referenced in 2 dashboard components via `/assets/Logo2.png`
- `core/test_components.py` line 42 uses Discord CDN URL (external)

**New Structure:**
```
assets/
├── GA_Logo_Black_Background.jpg              # Bot icon (user uploads)
├── GA_Logo_Transparent_Background_White_Text.png  # Dashboard icon (user uploads)
└── Logo2.png                                  # Moved from dashboard/public/assets/
```

## Implementation Steps

### Step 1: Create Git Commit (Before Changes)
**Action:** Create commit to preserve current working state
- Commit message: "chore: prepare for assets folder restructure"
- Creates checkpoint before major file moves

### Step 2: Move Assets Folder
**Action:** Move `dashboard/public/assets/` → `assets/` (project root)
- Moves entire folder with existing contents
- Deletes original `dashboard/public/assets/` folder

### Step 3: Update Dashboard Component References

**File 1: `dashboard/components/layout/DashboardLayout.tsx`**
- **Current:** `src="/assets/Logo2.png"`
- **New:** `src="../../assets/GA_Logo_Transparent_Background_White_Text.png"`
- Rationale: Must use relative path from dashboard to root assets folder

**File 2: `dashboard/components/auth/LoginForm.tsx`**
- **Current:** `src="/assets/Logo2.png"`
- **New:** `src="../../assets/GA_Logo_Transparent_Background_White_Text.png"`
- Rationale: Must use relative path from dashboard to root assets folder

### Step 4: Update Bot Component Reference

**File 3: `core/test_components.py` line 42**
- **Current:** Discord CDN URL (external)
- **New:** `attachment://GA_Logo_Black_Background.jpg`
- Rationale: Discord bots use `attachment://` protocol for locally attached files

### Step 5: Bot Command Integration Note

The command in `core/commands/utility.py` that uses `TestComponents` must be updated to:
1. Read the file: `assets/GA_Logo_Black_Background.jpg`
2. Attach it when sending the message as a Discord File object
3. The `attachment://` reference in test_components.py will then resolve correctly

**Example pattern:**
```python
file = discord.File("assets/GA_Logo_Black_Background.jpg", filename="GA_Logo_Black_Background.jpg")
await interaction.response.send_message(view=TestComponents(), file=file)
```

### Step 6: User Action Required
After code updates, user must upload:
1. `assets/GA_Logo_Black_Background.jpg` - Bot thumbnail image
2. `assets/GA_Logo_Transparent_Background_White_Text.png` - Dashboard logo

## Files Modified

1. ✅ **Move:** `dashboard/public/assets/` → `assets/`
2. ✅ **Update:** `dashboard/components/layout/DashboardLayout.tsx`
3. ✅ **Update:** `dashboard/components/auth/LoginForm.tsx`
4. ✅ **Update:** `core/test_components.py`
5. ⚠️ **Check:** `core/commands/utility.py` (may need file attachment code)

## Important Notes

- **Next.js Public Folder:** By default, Next.js only serves files from `public/` folder via `/` paths
- **Solution:** Use relative paths (`../../assets/`) to reference root-level assets from dashboard components
- **Alternative:** Could configure Next.js to serve additional static directories, but relative paths are simpler and more explicit

## Commit Strategy

1. **Before changes:** Commit current state ("prepare for assets folder restructure")
2. **After changes:** User can review all updates and commit as "refactor: move assets to root for shared bot/dashboard access"

This approach eliminates the need for symlinks while maintaining clean separation of concerns.