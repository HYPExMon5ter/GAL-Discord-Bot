---
description: "Promote reviewed documentation drafts from .agent/drafts/ to official .agent/system/ or .agent/sops/ directories."
---

# ✅ Accept Documentation Command

This command finalizes the documentation lifecycle after a Doc Rebuilder run.
It moves approved `.agent/drafts/*` files into their correct production folders
and updates logs automatically.

## ⚙️ Usage

```bash
droid run accept-docs
```

### What It Does

1. Scans `.agent/drafts/` for new or modified Markdown files.
2. Moves each file into its target directory:
   - `.agent/drafts/system/*` → `.agent/system/`
   - `.agent/drafts/sops/*` → `.agent/sops/`
3. Strips placeholder frontmatter tags like `status: draft` or `TODO:` comments.
4. Appends a summary entry to `.agent/tasks/active/update_log.md`:
   ```
   - (timestamp): Accepted X new documentation files from drafts.
   ```
5. Runs:
   ```bash
   droid run update-docs
   droid run snapshot-context
   droid run agent-commit
   ```

## 🧠 Example Output

```
📁 Promoted .agent/drafts/system/helper-modules.md → .agent/system/helper-modules.md
📁 Promoted .agent/drafts/sops/security.md → .agent/sops/security.md
✅ 2 files accepted and committed successfully.
```

## ⚠️ Notes

- Only files with `.md` extensions are promoted.
- Existing files are never overwritten — duplicates are renamed with `-copy`.
- Always review drafts before running this command.
- All actions are logged in `.agent/tasks/active/update_log.md`.
