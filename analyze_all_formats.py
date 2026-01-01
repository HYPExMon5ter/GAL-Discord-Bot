"""Analyze raw PaddleOCR output for all 3 formats."""
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='en')

# Expected player names
EXPECTED = {
    'lobbyaround3.png': ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris', 'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi'],
    'lobbybround3.png': ['Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer', 'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier'],
    'lobbycround3.png': ['mayxd', 'Duchess of Deer', 'hint', 'VeewithtooManyEs', '12FiendFyre', 'Ffoxface', 'Alithyst', 'Coralie']
}

for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    print(f'\n{"="*80}')
    print(f"ANALYZING: {screenshot}")
    print(f"Expected: {EXPECTED[screenshot]}")
    print(f"{'='*80}")

    result = ocr.ocr(f'dashboard/screenshots/{screenshot}')
    ocr_result = result[0]

    # Get raw data
    raw_data = ocr_result.json['res']
    texts = raw_data['rec_texts']
    boxes = raw_data['rec_boxes']
    scores = raw_data['rec_scores']

    # Find digits 1-8
    digit_indices = [i for i, t in enumerate(texts) if t.strip().isdigit() and 1 <= int(t.strip()) <= 8]

    print(f"\nTotal OCR items: {len(texts)}")
    print(f"Placement numbers (1-8) detected: {len(digit_indices)}")
    for idx in digit_indices:
        print(f"  Index {idx}: '{texts[idx]}' at y={boxes[idx][1]} conf={scores[idx]*100:.1f}%")

    # Find potential player names (3+ chars, has letters)
    name_indices = [i for i, t in enumerate(texts) if len(t.strip()) >= 3 and any(c.isalpha() for c in t)]

    print(f"\nPotential player names: {len(name_indices)}")
    for idx in name_indices[:12]:  # Show first 12
        print(f"  Index {idx}: '{texts[idx]}' at y={boxes[idx][1]} conf={scores[idx]*100:.1f}%")
