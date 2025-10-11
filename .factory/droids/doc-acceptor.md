---
id: droid.doc_acceptor
name: Doc Acceptor
description: >
  A utility Droid that finalizes documentation updates by promoting approved drafts
  from `.agent/drafts/` into production folders (`.agent/system/` and `.agent/sops/`),
  cleaning metadata, and committing the results.
role: Documentation Maintainer
tone: methodical, precise, cautious
memory: medium
context:
  - .agent/drafts/*
  - .agent/system/*
  - .agent/sops/*
  - .agent/tasks/active/update_log.md
triggers:
  - event: manual
tasks:
  - Identify all draft files in `.agent/drafts/`
  - Move files to appropriate destination folders
  - Remove `status: draft` and placeholder lines
  - Append summary entry to update_log.md
  - Run `droid run update-docs` and `droid run snapshot-context`
---

# 📦 Doc Acceptor Droid

When started, this Droid will:

1. Find all `.md` files under `.agent/drafts/system/` and `.agent/drafts/sops/`.
2. Move them into `.agent/system/` or `.agent/sops/`, respectively.
3. Strip lines starting with `status: draft`, `TODO:`, or `# Draft`.
4. Add a changelog entry to `.agent/tasks/active/update_log.md`.
5. Run:
   ```bash
   droid run update-docs
   droid run snapshot-context
   droid run agent-commit
   ```

### Example Usage

```bash
droid start doc_acceptor
```

### Example Prompt

> "Accept all reviewed documentation drafts and commit them."

### Safety Notes

- Does not overwrite existing files (adds `-copy` suffix).
- Logs all changes for traceability.
- Should be run after manual review of `.agent/drafts/`.
