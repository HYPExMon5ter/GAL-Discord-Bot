"""Debug PaddleOCR result format."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import cv2
from paddleocr import PaddleOCR

# Initialize PaddleOCR
ocr = PaddleOCR(lang='en')

# Test on one screenshot
screenshot = 'dashboard/screenshots/lobbyaround3.png'
print(f"Testing: {Path(screenshot).name}")

img = cv2.imread(screenshot)
results = ocr.ocr(img)

print(f"\nType of results: {type(results)}")

# Handle both list and dict formats (different PaddleOCR versions)
if isinstance(results, list) and results:
    # Newer PaddleOCR version returns list of OCRResult objects
    first_result = results[0]
    
    if isinstance(first_result, dict):
        # OCRResult is a dict
        print(f"First result (dict) keys: {first_result.keys()}")
        
        if 'rec_boxes' in first_result:
            rec_boxes = first_result['rec_boxes']
            rec_texts = first_result.get('rec_texts', [])
            rec_scores = first_result.get('rec_scores', [])
            
            print(f"\nType of rec_boxes: {type(rec_boxes)}")
            print(f"Length of rec_boxes: {len(rec_boxes)}")
            
            # rec_boxes format: [[x1, y1, x2, y2], ...]
            # rec_texts: list of text strings
            # rec_scores: list of confidence scores
            
            for i in range(min(10, len(rec_boxes))):
                bbox = rec_boxes[i]
                text = rec_texts[i] if i < len(rec_texts) else "N/A"
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                
                print(f"\nItem {i}:")
                print(f"  BBox: {bbox}")
                print(f"  Text: '{text}'")
                print(f"  Score: {score}")
    else:
        print(f"First result type: {type(first_result)}")
        print(f"First result: {first_result}")
else:
    # Older format or empty results
    print(f"Length of results: {len(results) if results else 0}")
