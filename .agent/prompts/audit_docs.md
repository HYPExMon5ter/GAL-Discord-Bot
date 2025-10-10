# Audit Documentation Command
Scan `.agent/system` against the repository:
- Flag modules with no corresponding doc
- Flag stale links or missing cross-links
- Suggest SOPs if the same workflow occurs ≥2 times in scripts/ or cogs/
Output a human-readable report; do not modify files.
