Fix ArchiveTab Badge Error and Remove Badge Count

**Problem:** Badge component is used but not imported, causing ReferenceError. Badge showing archive count needs to be removed.

**Solution:**
1. Remove the entire Badge section (lines 273-285) that displays archived graphics count
2. Keep simplified header with just title and description

**Changes:**
- Delete the div containing Badge component that shows "X Archived 📚"
- Simplifies header layout and eliminates ReferenceError

This fixes both the error and removes the badge as requested.