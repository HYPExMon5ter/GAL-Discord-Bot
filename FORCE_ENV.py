"""
Force Environment Variables for Bot
Run this BEFORE starting the bot!
"""

import os

# CRITICAL: Disable PaddleOCR model connectivity check
# Without this, PaddleOCR hangs for 30-60 seconds on every batch
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# Fix Unicode encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("✅ Environment variables set:")
print(f"  DISABLE_MODEL_SOURCE_CHECK: {os.environ.get('DISABLE_MODEL_SOURCE_CHECK')}")
print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")
print()
print("Now run: python bot.py")
