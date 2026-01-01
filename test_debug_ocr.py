"""Quick test - test with relaxed filtering to see all detected text."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')

from integrations.standings_ocr import get_ocr_pipeline

# TEMPORARY: Modify parser to disable filters for testing
import integrations.standings_ocr as ocr_module

# Save original function
original_parse = ocr_module.TFTOCRParser._tft_specific_parser

def debug_parser(self, image: np.ndarray, raw_results: Dict) -> list:
    """Debug parser that logs ALL detected text without filtering."""
    players = []
    height, width = image.shape[:2]
    
    # Collect ALL text without keyword filters
    all_text = []
    
    for pass_name, pass_data in raw_results.items():
        if pass_data and "results" in pass_data:
            for engine_name, engine_data in pass_data["results"].items():
                if engine_data and "raw_data" in engine_data:
                    for item in engine_data["raw_data"]:
                        # Handle both EasyOCR and Tesseract formats
                        if isinstance(item, tuple) and len(item) == 3:
                            # EasyOCR: (bbox, text, conf)
                            bbox, text, conf = item
                            x_center = (bbox[0][0] + bbox[2][0]) / 2
                            y_center = (bbox[0][1] + bbox[2][1]) / 2
                        elif isinstance(item, str):
                            continue
                        else:
                            continue
                        
                        # Collect ALL text, no filtering
                        if text.strip():
                            all_text.append({
                                'text': text.strip().upper(),
                                'x_center': x_center,
                                'y_center': y_center,
                                'confidence': conf if isinstance(conf, (int, float)) else 0
                            })
    
    # Sort by Y coordinate
    all_text_sorted = sorted(all_text, key=lambda x: x['y_center'])
    
    # Group by Y (rows) - use 100px threshold
    rows = []
    current_row = [all_text_sorted[0]] if all_text_sorted else []
    
    for i, item in enumerate(all_text_sorted[1:], start=1):
        if abs(item['y_center'] - current_row[0]['y_center']) < 100:
            current_row.append(item)
        else:
            rows.append(current_row)
            current_row = [item]
    
    if current_row:
        rows.append(current_row)
    
    print(f"\n=== DEBUG: All detected text grouped into {len(rows)} rows ===")
    for i, row in enumerate(rows):
        print(f"\nRow {i+1}:")
        for item in row:
            print(f"  '{item['text']}' at (x={item['x_center']:.0f}, y={item['y_center']:.0f}, conf={item['confidence']:.1f})")
    
    return players

# Replace parser for testing
ocr_module.TFTOCRParser._tft_specific_parser = debug_parser

ocr = get_ocr_pipeline()

screenshots = [
    'dashboard/screenshots/lobbyaround3.png',
    'dashboard/screenshots/lobbybround3.png',
    'dashboard/screenshots/lobbycround3.png'
]

print('='*80)
print('TESTING WITH DEBUG PARSER (shows all detected text)')
print('='*80)

for screenshot in screenshots:
    print(f'\n\n{"="*80}')
    print(f'Processing: {Path(screenshot).name}...')
    print(f'{"="*80}')
    
    result = ocr.extract_from_image(screenshot)
    
    if result.get('success'):
        players = result['structured_data']['players']
        print(f'\nParser found {len(players)} players')
        if players:
            print('\nFirst 5 detected players:')
            for p in players[:5]:
                print(f'  Placement {p["placement"]}: {p["name"]}')
    else:
        print(f'ERROR: {result.get("error")}')

print('\n' + '='*80)
print('TEST COMPLETE')
print('='*80)
