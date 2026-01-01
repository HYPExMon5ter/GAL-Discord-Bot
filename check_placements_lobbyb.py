"""Check placement detection for lobbyb."""
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='en')
result = ocr.ocr(cv2.imread('dashboard/screenshots/lobbybround3.png'))

# Get placement numbers
texts = result[0].json['res']['rec_texts']
digits = [t for t in texts if t.strip().isdigit() and 1 <= int(t) <= 8]

print(f"Placement numbers detected: {digits}")
print(f"Total texts: {len(texts)}")

# Show all texts with 3+ chars
print("\nAll texts (3+ chars):")
for t in texts:
    if len(t.strip()) >= 3:
        print(f"  - '{t}'")
