"""Test standalone PaddleOCR engine."""
import sys
if 'integrations.paddle_ocr_engine' in sys.modules:
    del sys.modules['integrations.paddle_ocr_engine']
import importlib
import integrations.paddle_ocr_engine
importlib.reload(integrations.paddle_ocr_engine)
from integrations.paddle_ocr_engine import get_paddle_ocr

# Expected player names for each screenshot
EXPECTED_NAMES = {
    'lobbyaround3.png': ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris', 'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi'],
    'lobbybround3.png': ['Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer', 'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier'],
    'lobbycround3.png': ['mayxd', 'Duchess of Deer', 'hint', 'VeewithtooManyEs', '12FiendFyre', 'Ffoxface', 'Alithyst', 'Coralie']
}

try:
    paddle = get_paddle_ocr()
except Exception as e:
    print(f"ERROR initializing PaddleOCR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    print(f'\n--- Testing: {screenshot} ---')
    try:
        result = paddle.extract_from_image(f'dashboard/screenshots/{screenshot}')
    except Exception as e:
        print(f"ERROR during OCR: {e}")
        import traceback
        traceback.print_exc()
        result = {"success": False, "error": str(e)}

    if result['success']:
        players = result['structured_data']['players']
        detected_names = [p['name'].lower() for p in players]
        expected_names = EXPECTED_NAMES[screenshot]

        # Debug: show detected names
        print(f"Detected names (after correction): {detected_names}")

        # Calculate accuracy
        correct = 0
        for expected in expected_names:
            e_norm = expected.lower().replace(' ', '')
            for detected in detected_names:
                d_norm = detected.lower().replace(' ', '')
                if e_norm in d_norm or d_norm in e_norm:
                    correct += 1
                    break

        accuracy = (correct / max(len(detected_names), len(expected_names))) * 100 if expected_names else 0

        print(f'Players detected: {len(players)}')
        for p in players:
            print(f"  {p['placement']}: {p['name']}")
        print(f"Overall confidence: {result['scores']['overall']:.2%}")

        # Show accuracy
        print(f"\nExpected: {expected_names}")
        print(f"Detected: {detected_names}")
        print(f"Correct: {correct}/{max(len(detected_names), len(expected_names))} ({accuracy:.1f}%)")
    else:
        print(f"ERROR: {result.get('error')}")
