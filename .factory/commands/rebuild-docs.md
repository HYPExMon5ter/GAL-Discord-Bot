---
description: "Run the Doc Rebuilder Droid to automatically generate missing documentation and architecture drafts."
---

# 🧩 Rebuild Documentation Command

This command triggers the **Doc Rebuilder Droid**, which scans the latest
audit report and regenerates any missing or incomplete `.agent` files.

Use this when you’ve run the auditor and want to fix missing documentation automatically.

## 🧠 Usage

```bash
droid run rebuild-docs
```

or start it interactively:

```bash
droid start doc_rebuilder
```

### What It Does

1. Parses the most recent `documentation_gap_analysis_*.md`.
2. Creates missing architecture and SOP drafts in `.agent/drafts/`.
3. Logs its actions in `.agent/tasks/active/update_log.md`.
4. Optionally triggers a snapshot rebuild via `droid run snapshot-context`.

---

**Tip:** Review drafts before promoting them into the main `.agent/` structure to prevent overwriting existing documentation.
