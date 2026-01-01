"""Test lobbybround3.png specifically."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()

print('Testing: lobbybround3.png')
result = paddle.extract_from_image('dashboard/screenshots/lobbybround3.png')

if result['success']:
    players = result['structured_data']['players']
    print(f'Players detected: {len(players)}')
    for p in players:
        print(f"  {p['placement']}: {p['name']}")
    print(f"Expected: ['Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer', 'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier']")
    print(f"Overall confidence: {result['scores']['overall']:.2%}")
else:
    print(f"ERROR: {result.get('error')}")
