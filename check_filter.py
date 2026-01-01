"""Check which names pass filtering."""
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='en')
result = ocr.ocr(cv2.imread('dashboard/screenshots/lobbyaround3.png'))
items = result[0].json['res']

skip_keywords = ['FIRST', 'PLACE', 'STAND', 'TEAMFIGHT', 'TACTICS',
                'NORMAL', 'GAME', 'ONLINE', 'SOCIAL', 'PLAYER',
                'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'TAND',
                'PLAY', 'AGAIN', 'CONTINUE', 'GAMEID',
                'GAMEL', 'GAMEID', 'TEAMF', 'TACT']

garbage_keywords = ['GAME', 'STAND', 'PLAYER', 'TEAM', 'TACT', 'VOw', 'BRC', 'COS', 'OLO', 'Gamel', 'ROR']

names = []
for i in range(len(items['rec_texts'])):
    text = items['rec_texts'][i].strip()
    y = items['rec_boxes'][i][1]
    text_upper = text.upper()

    # Skip UI keywords
    if any(keyword in text_upper for keyword in skip_keywords):
        print(f"SKIP UI: '{text}'")
        continue

    # Check if valid name
    text_alpha_only = ''.join(c for c in text if c.isalpha())

    # Skip garbage
    if any(kw in text_upper for kw in garbage_keywords):
        print(f"SKIP GARBAGE: '{text}'")
        continue

    # Accept 3+ letter names
    if len(text_alpha_only) >= 3 and len(text_alpha_only) / len(text) >= 0.7:
        # Skip duplicates
        if not any(n[0].upper() == text_upper for n in names):
            names.append(text)
            print(f"ADD: '{text}'")

print(f"\nTotal names: {len(names)}")
print(f"Names: {names}")
