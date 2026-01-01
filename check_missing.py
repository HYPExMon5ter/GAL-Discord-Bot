"""Check which players are missing for lobbya and lobbyc."""
from integrations.paddle_ocr_engine import get_paddle_ocr

paddle = get_paddle_ocr()

for screenshot, expected in [
    ('lobbyaround3.png', ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris', 'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi']),
    ('lobbycround3.png', ['mayxd', 'Duchess of Deer', 'hint', 'VeeWithTooManyEs', '12FiendFyre', 'Ffoxface', 'Alithyst', 'Coralie'])
]:
    print(f'\n--- {screenshot} ---')
    result = paddle.extract_from_image(f'dashboard/screenshots/{screenshot}')
    detected = [p['name'].lower() for p in result['structured_data']['players']]
    expected_lower = [e.lower() for e in expected]

    print(f'Expected: {expected}')
    print(f'Detected: {detected}')

    # Find missing
    missing = [e for e in expected if e.lower() not in detected]
    extra = [d for d in detected if d not in expected_lower]

    print(f'Missing: {missing}')
    print(f'Extra: {extra}')
