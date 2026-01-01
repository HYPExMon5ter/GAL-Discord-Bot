"""Test name correction logic."""
from integrations.paddle_ocr_engine import PaddleOCREngine

engine = PaddleOCREngine()

# Test lobbyb specifically
result = engine.extract_from_image('dashboard/screenshots/lobbybround3.png')

print("Names detected:")
for p in result['structured_data']['players']:
    print(f"  {p['placement']}: '{p['name']}'")
