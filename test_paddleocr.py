"""Test PaddleOCR installation and accuracy on TFT screenshots."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# Test PaddleOCR import
try:
    from paddleocr import PaddleOCR
    print("[OK] PaddleOCR imported successfully")
except ImportError as e:
    print(f"[ERROR] PaddleOCR not installed: {e}")
    print("\nPlease install PaddleOCR:")
    print("  pip install paddleocr paddlepaddle")
    sys.exit(1)

# Initialize PaddleOCR (CPU mode for Railway compatibility)
print("\nInitializing PaddleOCR (CPU mode)...")
ocr = PaddleOCR(lang='en')
print("[OK] PaddleOCR initialized successfully")

# Test on screenshots
import cv2
import numpy as np

screenshots = [
    'dashboard/screenshots/lobbyaround3.png',
    'dashboard/screenshots/lobbybround3.png',
    'dashboard/screenshots/lobbycround3.png'
]

print("\n" + "="*80)
print("TESTING PADDLEOCR ON TFT SCREENSHOTS")
print("="*80)

for screenshot in screenshots:
    if not Path(screenshot).exists():
        print(f"\n[ERROR] File not found: {screenshot}")
        continue
    
    print(f"\n\nProcessing: {Path(screenshot).name}...")
    print(f"{'-'*80}")
    
    # Read image
    img = cv2.imread(screenshot)
    if img is None:
        print(f"[ERROR] Failed to read image")
        continue
    
    # Run PaddleOCR (uses color image, not grayscale)
    print("Running OCR...")
    results = ocr.ocr(img)
    
    # Process results
    print(f"\n[OK] Detected {len(results)} text regions")
    
    # Group text by Y position (rows)
    rows = []
    sorted_results = sorted(results, key=lambda x: x[0][0][1])  # Sort by Y
    
    if sorted_results:
        current_row = [sorted_results[0]]
        
        for i, item in enumerate(sorted_results[1:], start=1):
            # Check if on same row (Y diff < 50px)
            current_y = current_row[0][0][1]
            next_y = item[0][0][1]
            
            if abs(next_y - current_y) < 50:
                current_row.append(item)
            else:
                rows.append(current_row)
                current_row = [item]
        
        if current_row:
            rows.append(current_row)
    
    # Print detected text by rows
    print("\nDetected text by rows:")
    for i, row in enumerate(rows, start=1):
        # Sort row by X position (left to right)
        sorted_row = sorted(row, key=lambda x: x[0][0][0])
        print(f"\nRow {i}:")
        for item in sorted_row:
            bbox = item[0]
            text, conf = item[1]
            x_center = (bbox[0][0] + bbox[2][0]) / 2
            y_center = (bbox[0][1] + bbox[2][1]) / 2
            
            # Check if it's a placement number (single digit 1-8)
            is_placement = text.strip().isdigit() and 1 <= int(text.strip()) <= 8 and len(text.strip()) == 1
            marker = "[PLACEMENT]" if is_placement else "[TEXT]"
            
            print(f"  {marker} '{text}' (conf: {conf*100:.1f}%) at (x={x_center:.0f}, y={y_center:.0f})")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
print("\nNext steps:")
print("1. Review detected text above")
print("2. If placements and names are correctly detected, PaddleOCR is working")
print("3. Run full test with test_ocr_enhanced.py")
print("4. Target: 80%+ accuracy per image")
