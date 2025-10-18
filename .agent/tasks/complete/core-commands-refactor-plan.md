
**Status (2025-10-15):** Registration domain commands migrated to core/commands/registration.py with shared logging utilities; remaining commands stay in legacy.py for later slices.
- Configuration command suite migrated to core/commands/configuration.py with shared logging and modular helpers.
- Onboarding command moved to core/commands/onboarding.py with shared helper usage.
- Utility commands (test/placement/help) migrated to core/commands/utility.py; legacy definitions removed.
- Simplified core/commands/legacy.py to host only the GAL group scaffold and shared error handler.
