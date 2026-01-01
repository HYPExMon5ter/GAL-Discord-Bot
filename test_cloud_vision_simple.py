"""
Simple Cloud Vision test - just show detected players without comparing to expected names.
"""

import os
import sys
from pathlib import Path
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from integrations.cloud_vision_ocr import get_cloud_vision_ocr

ocr = get_cloud_vision_ocr()

screenshots = [
    ("Lobby A", "dashboard/screenshots/lobbyaround3.png"),
    ("Lobby B", "dashboard/screenshots/lobbybround3.png"),
    ("Lobby C", "dashboard/screenshots/lobbycround3.png")
]

print("=" * 80)
print("CLOUD VISION OCR - SHOW DETECTED PLAYERS")
print("=" * 80)
print()

for name, path in screenshots:
    if not os.path.exists(path):
        continue
    
    print(f"Screenshot: {name}")
    print(f"File: {path}")
    print("-" * 80)
    
    result = ocr.extract_from_image(path)
    
    if result["success"]:
        players = result["structured_data"]["players"]
        confidence = result["scores"]["overall"]
        
        print(f"✅ Detected: {len(players)} players")
        print(f"🎯 Confidence: {confidence:.1%}")
        print()
        
        for i, p in enumerate(players, 1):
            status = "✅" if i <= 8 else "❌"
            print(f"  {status} {i}. {p['name']} ({p['points']} pts)")
    else:
        print(f"❌ OCR failed: {result.get('error')}")
    
    print()
    print("=" * 80)
    print()
