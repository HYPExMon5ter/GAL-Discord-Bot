"""
Show players detected by Cloud Vision OCR with placements.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from integrations.cloud_vision_ocr import get_cloud_vision_ocr

ocr = get_cloud_vision_ocr()

screenshots = [
    ("Lobby A", "dashboard/screenshots/lobbyaround3.png"),
    ("Lobby B", "dashboard/screenshots/lobbybround3.png"),
    ("Lobby C", "dashboard/screenshots/lobbycround3.png")
]

print("=" * 60)
print("CLOUD VISION OCR - PLAYER DETECTION RESULTS")
print("=" * 60)
print()

for name, path in screenshots:
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
    
    print(f"\n{'=' * 60}")
    print(f"  {name.upper()}")
    print(f"{'=' * 60}\n")
    
    result = ocr.extract_from_image(path)
    
    if result["success"]:
        players = result["structured_data"]["players"]
        confidence = result["scores"]["overall"]
        
        print(f"Detected: {len(players)} players | Confidence: {confidence:.1%}\n")
        
        for p in players:
            print(f"  {p['placement']}. {p['name']} ({p['points']} pts)")
        
        print()
    else:
        print(f"OCR failed: {result.get('error')}\n")

print("=" * 60)
