"""Check what names are being collected."""
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='en')
img = cv2.imread('dashboard/screenshots/lobbyaround3.png')
result = ocr.ocr(img)[0]

# Get raw data
raw_data = result.json['res']
texts = raw_data['rec_texts']
boxes = raw_data['rec_boxes']
scores = raw_data['rec_scores']

# Check specific names
target_names = ['Vedris', 'Matt Green', 'Spear and Sky']
found = False

for i, text in enumerate(texts):
    if any(t.lower() in text.lower() for t in target_names):
        print(f"Found '{text}' at index {i}, confidence {scores[i]*100:.1f}%")
        found = True
        if text.lower() in ['vedris']:
            print(f"  -> This is 'Vedris'!")

if not found:
    print("Vedris and Matt Green not found!")
    print("\nAll texts:")
    for i, text in enumerate(texts):
        if len(text) >= 3:
            print(f"  {i}: '{text}' (conf: {scores[i]*100:.1f}%)")
