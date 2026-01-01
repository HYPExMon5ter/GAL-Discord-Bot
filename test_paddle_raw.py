"""Test raw PaddleOCR output."""
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='en')

image_path = 'dashboard/screenshots/lobbybround3.png'  # Changed to test format 2
img = cv2.imread(image_path)
print(f"Image loaded: {img.shape}")

result = ocr.ocr(image_path)
print(f"\nResult type: {type(result)}")
print(f"Result length: {len(result) if result else 0}")

if result and len(result) > 0:
    ocr_result = result[0]
    print(f"\nOCRResult type: {type(ocr_result)}")
    print(f"OCRResult dir: {[x for x in dir(ocr_result) if not x.startswith('_')]}")
    
    # Try to access OCRResult attributes
    if hasattr(ocr_result, 'rec_text'):
        print(f"\nrec_text: {ocr_result.rec_text}")
    if hasattr(ocr_result, 'rec_texts'):
        print(f"\nrec_texts: {ocr_result.rec_texts}")
    if hasattr(ocr_result, 'json'):
        print(f"\njson: {ocr_result.json}")
    if hasattr(ocr_result, '__dict__'):
        print(f"\n__dict__: {ocr_result.__dict__}")
