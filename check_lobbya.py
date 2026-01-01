"""Check lobbya detection."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()
result = paddle.extract_from_image('dashboard/screenshots/lobbyaround3.png')

players = result['structured_data']['players']
print(f'Detected {len(players)} players:')
for p in players:
    print(f"  {p['placement']}: {p['name']}")

expected = ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris', 'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi']
detected = [p['name'] for p in players]

print(f'\nExpected: {expected}')
print(f'Detected: {detected}')

# Find missing
missing = [exp for exp in expected if exp not in detected]
print(f'Missing: {missing}')
