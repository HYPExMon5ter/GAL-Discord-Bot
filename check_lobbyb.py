"""Check lobbyb detection."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()
result = paddle.extract_from_image('dashboard/screenshots/lobbybround3.png')

players = result['structured_data']['players']
print(f'Detected {len(players)} players:')
for p in players:
    print(f"  {p['placement']}: {p['name']}")

expected = ['Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer', 'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier']
detected = [p['name'] for p in players]

print(f'\nExpected: {expected}')
print(f'Detected: {detected}')
