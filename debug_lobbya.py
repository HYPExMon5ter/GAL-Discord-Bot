"""Debug lobbyaround3.py regression."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()

print('Testing: lobbyaround3.png')
result = paddle.extract_from_image('dashboard/screenshots/lobbyaround3.png')

if result['success']:
    players = result['structured_data']['players']
    print(f'Players detected: {len(players)}')
    for p in players:
        print(f"  {p['placement']}: {p['name']}")

    expected = ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris', 'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi']
    detected = [p['name'] for p in players]

    print(f"\nExpected: {expected}")
    print(f"Detected: {detected}")

    # Check which are wrong
    for i, exp in enumerate(expected):
        exp_lower = exp.lower()
        if i < len(detected) and detected[i].lower() != exp_lower:
            print(f"MISMATCH at placement {i+1}: expected '{exp}', got '{detected[i]}'")
else:
    print(f"ERROR: {result.get('error')}")
