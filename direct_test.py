"""Direct test to check names list."""
from integrations.paddle_ocr_engine import PaddleOCREngine

engine = PaddleOCREngine()

# Monkey patch to print names
original_structure = engine._structure_tft_data

def debug_structure(self, text_results):
    print(f"\n[DEBUG] Input text_results: {len(text_results)} items")
    for i, item in enumerate(text_results[:15]):  # First 15 items
        print(f"  {i}: '{item['text']}' (conf: {item['confidence']*100:.1f}%)")

    result = original_structure(self, text_results)
    print(f"\n[DEBUG] Output: {len(result['players'])} players")
    return result

engine._structure_tft_data = debug_structure.__get__(engine, PaddleOCREngine)

result = engine.extract_from_image('dashboard/screenshots/lobbybround3.png')
print(f"\nFinal: {len(result['structured_data']['players'])} players")
