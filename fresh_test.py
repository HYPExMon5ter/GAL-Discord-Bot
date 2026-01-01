"""Fresh test without caching."""
import sys
sys.path.insert(0, '.')

from integrations.paddle_ocr_engine import PaddleOCREngine

engine = PaddleOCREngine()
result = engine.extract_from_image('dashboard/screenshots/lobbybround3.png')

players = result['structured_data']['players']
print(f'Detected {len(players)} players:')
for p in players:
    print(f"  {p['placement']}: {p['name']}")
