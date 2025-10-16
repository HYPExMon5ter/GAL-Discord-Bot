"""
Centralised feature flag helpers for coordinating staged rollouts.

Phase 6 introduces environment-driven toggles so we can rapidly disable
the new sheet integration stack if production issues surface.
"""

from __future__ import annotations

import os
from typing import Dict


def _env_bool(name: str, default: bool = True) -> bool:
    """Read an environment variable and coerce it to a boolean."""
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def sheets_refactor_enabled() -> bool:
    """
    Return True when the sheet integration refactor should be active.

    Controlled via `GAL_FEATURE_SHEETS_REFACTOR` (defaults to enabled).
    """
    return _env_bool("GAL_FEATURE_SHEETS_REFACTOR", default=True)


def deployment_stage() -> str:
    """
    Report the declared deployment stage for logging or observability.

    Environment variable: `GAL_DEPLOYMENT_STAGE`
    Expected values: integrations -> backend -> bot -> dashboard
    """
    return os.getenv("GAL_DEPLOYMENT_STAGE", "dashboard").strip().lower()


def rollout_flags_snapshot() -> Dict[str, bool]:
    """Expose the active feature toggles for diagnostics."""
    return {
        "sheets_refactor": sheets_refactor_enabled(),
    }


__all__ = [
    "deployment_stage",
    "rollout_flags_snapshot",
    "sheets_refactor_enabled",
]
