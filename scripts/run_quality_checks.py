#!/usr/bin/env python3
"""
Execute the repository quality gates (lint, type-check, tests) in a single command.

This script is referenced by Phase 5 to ensure consistent tooling across the
Python services and dashboard frontend.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT / "dashboard"


def _run_command(step: str, command: Sequence[str], cwd: Path | None = None) -> Tuple[str, int]:
    """Run a command and return its return code."""
    print(f"[quality] Running {step} -> {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, check=False)
    return step, completed.returncode


def _python_cmd(*args: str) -> List[str]:
    """Build a python invocation with the current interpreter."""
    return [sys.executable, *args]


def _changed_python_files() -> List[str]:
    """Return a list of modified Python files relative to git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []

    paths: List[str] = []
    for line in result.stdout.splitlines():
        if not line or len(line) < 4:
            continue
        path_fragment = line[3:]
        if " -> " in path_fragment:
            path_fragment = path_fragment.split(" -> ", 1)[1]
        if path_fragment.endswith(".py"):
            paths.append(path_fragment)
    return paths


def main() -> int:
    python_targets = _changed_python_files()
    steps: List[Tuple[str, Sequence[str], Path | None]] = []
    failures: List[Tuple[str, int]] = []

    if python_targets:
        steps.append(("ruff", _python_cmd("-m", "ruff", "check", *python_targets), ROOT))
        steps.append(("black", _python_cmd("-m", "black", "--check", *python_targets), ROOT))
    else:
        print("[quality] Skipping Ruff/Black; no modified Python files detected.")

    steps.append(("pytest", _python_cmd("-m", "pytest"), ROOT))

    npm_bin = shutil.which("npm")
    if npm_bin:
        steps.extend(
            [
                ("dashboard lint", [npm_bin, "run", "lint"], DASHBOARD_DIR),
                ("dashboard type-check", [npm_bin, "run", "type-check"], DASHBOARD_DIR),
            ]
        )
    else:
        print("[quality] Skipping dashboard checks; npm executable not found.")

    for name, command, directory in steps:
        step, code = _run_command(name, command, directory)
        if code != 0:
            failures.append((step, code))

    if failures:
        print("\n[quality] Failures detected:")
        for step, code in failures:
            print(f"  - {step} (exit code {code})")
        return 1

    print("\n[quality] All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
