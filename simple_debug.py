"""Simple debug test."""
from integrations.paddle_ocr_engine import PaddleOCREngine

engine = PaddleOCREngine()
result = engine.extract_from_image('dashboard/screenshots/lobbyaround3.png')

players = result['structured_data']['players']
print(f"Players: {len(players)}")
for p in players:
    print(f"  {p['placement']}: {p['name']}")
