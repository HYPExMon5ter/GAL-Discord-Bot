"""
Debug script to see what Cloud Vision actually detects in screenshots.
"""

import os
import sys
from pathlib import Path
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.cloud import vision

# Initialize Vision client
client = vision.ImageAnnotatorClient()

# Test screenshots
screenshots = [
    "dashboard/screenshots/lobbyaround3.png",
    "dashboard/screenshots/lobbybround3.png",
    "dashboard/screenshots/lobbycround3.png"
]

print("=" * 80)
print("CLOUD VISION RAW TEXT DETECTION")
print("=" * 80)
print()

for path in screenshots:
    if not os.path.exists(path):
        continue
    
    print(f"File: {path}")
    print("-" * 80)
    
    # Read image
    with open(path, 'rb') as f:
        content = f.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    # Get annotations
    annotations = response.text_annotations
    
    # Show first 50 text items (skip index 0 which is full page text)
    print(f"Total detections: {len(annotations)}")
    print()
    
    for i, annotation in enumerate(annotations[1:51]):  # Skip first, show next 50
        text = annotation.description.strip()
        vertices = annotation.bounding_poly.vertices
        
        # Get bounding box
        x_coords = [v.x for v in vertices]
        y_coords = [v.y for v in vertices]
        
        x_min = min(x_coords)
        x_max = max(x_coords)
        y_min = min(y_coords)
        y_max = max(y_coords)
        
        print(f"[{i}] '{text}'")
        print(f"    Position: ({x_min:.0f}, {y_min:.0f}) to ({x_max:.0f}, {y_max:.0f})")
        print(f"    Center: ({(x_min+x_max)/2:.0f}, {(y_min+y_max)/2:.0f})")
        print()
    
    if len(annotations) > 51:
        print(f"... (and {len(annotations)-51} more)")
    
    print()
    print("=" * 80)
    print()
