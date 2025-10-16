"""Test configuration for pytest."""

import warnings

# Ignore upstream DeprecationWarning triggered by discord.py using the stdlib
# audioop module, which is slated for removal in Python 3.13.
warnings.filterwarnings(
    "ignore",
    message=r".*audioop.*deprecated.*",
    category=DeprecationWarning,
    module=r"discord\.player",
)
