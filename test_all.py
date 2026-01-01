"""Test all 3 formats."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()

for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    print(f'\n--- Testing: {screenshot} ---')
    result = paddle.extract_from_image(f'dashboard/screenshots/{screenshot}')

    if result['success']:
        players = result['structured_data']['players']
        print(f'Players detected: {len(players)}')
        for p in players:
            print(f"  {p['placement']}: {p['name']}")
        print(f"Overall confidence: {result['scores']['overall']:.2%}")
    else:
        print(f"ERROR: {result.get('error')}")
