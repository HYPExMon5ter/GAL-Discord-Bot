"""Debug raw OCR to see what's being detected."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

ocr = get_ocr_pipeline()

# Get OCR pipeline internals
ocr.extract_from_image('dashboard/screenshots/lobbyaround3.png')

# Check what raw OCR detected
if hasattr(ocr, '_last_raw_results') and ocr._last_raw_results:
    print('\n' + '='*80)
    print('RAW OCR RESULTS (left side only, X < 600)')
    print('='*80)

    all_items = []
    for pass_name, pass_data in ocr._last_raw_results.items():
        if 'results' in pass_data:
            for engine_name, engine_data in pass_data['results'].items():
                if engine_name == 'easyocr' and 'raw_data' in engine_data:
                    for (bbox, text, conf) in engine_data['raw_data']:
                        x_center = (bbox[0][0] + bbox[2][0]) / 2
                        y_center = (bbox[0][1] + bbox[2][1]) / 2

                        # Only left side
                        if x_center > 600:
                            continue

                        # Clean text
                        text = text.strip().upper()

                        all_items.append({
                            'text': text,
                            'x': x_center,
                            'y': y_center,
                            'conf': conf
                        })

    # Sort by Y and display
    all_items.sort(key=lambda x: x['y'])

    print(f"{'Y':<6} | {'X':<6} | {'Conf':<6} | {'Text'}")
    print("-" * 80)

    for item in all_items:
        print(f"{item['y']:6.0f} | {item['x']:6.0f} | {item['conf']:6.3f} | {item['text']}")
