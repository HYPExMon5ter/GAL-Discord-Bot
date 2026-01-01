"""Check what names are being collected for lobbyb."""
from integrations.paddle_ocr_engine import get_paddle_ocr

# Force fresh import
import sys
if 'integrations.paddle_ocr_engine' in sys.modules:
    del sys.modules['integrations.paddle_ocr_engine']

paddle = get_paddle_ocr()

# Temporarily add print to _structure_tft_data
import integrations.paddle_ocr_engine as engine_module

# Save original
original_structure = engine_module.PaddleOCREngine._structure_tft_data

def debug_structure(self, text_results):
    result = original_structure(self, text_results)
    print(f"\nDEBUG: Names collected in _structure_tft_data:")
    for n, y in result['names']:
        print(f"  - '{n}'")
    return result

# Monkey patch
engine_module.PaddleOCREngine._structure_tft_data = debug_structure

# Run test
result = paddle.extract_from_image('dashboard/screenshots/lobbybround3.png')
print(f"\nFinal players: {len(result['structured_data']['players'])}")
