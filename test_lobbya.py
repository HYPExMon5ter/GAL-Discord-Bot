"""Test lobbyaround3.png specifically."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()

print('Testing: lobbyaround3.png')
result = paddle.extract_from_image('dashboard/screenshots/lobbyaround3.png')

if result['success']:
    players = result['structured_data']['players']
    print(f'Players detected: {len(players)}')
    for p in players:
        print(f"  {p['placement']}: {p['name']}")
    print(f"Expected: ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris', 'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi']")
    print(f"Overall confidence: {result['scores']['overall']:.2%}")
else:
    print(f"ERROR: {result.get('error')}")
