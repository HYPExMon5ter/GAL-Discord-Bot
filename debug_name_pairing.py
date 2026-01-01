"""Debug script to see what OCR is actually detecting vs what should be there."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

ocr = get_ocr_pipeline()

# Process each screenshot and show detailed OCR results
for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    path = f'dashboard/screenshots/{screenshot}'
    print(f'\n{"="*80}')
    print(f'{screenshot}')
    print(f'{"="*80}')

    result = ocr.extract_from_image(path)

    if result.get('success'):
        players = result['structured_data']['players']

        print(f'\nDetected {len(players)} players:')
        for i, player in enumerate(players, 1):
            print(f'{i}. Placement {player["placement"]:2d}: {player["name"]:30s} (points: {player["points"]})')

        # Get raw OCR results to see what was detected
        if 'raw_results' in result:
            print(f'\nRaw OCR detections (first 30):')
            for pass_name, pass_data in list(result['raw_results'].items())[:2]:
                print(f'\n{pass_name}:')
                if 'results' in pass_data:
                    for engine_name, engine_data in pass_data['results'].items():
                        if engine_name == 'easyocr' and 'raw_data' in engine_data:
                            # Get raw detections from EasyOCR
                            detections = []
                            for (bbox, text, conf) in engine_data['raw_data']:
                                x_center = (bbox[0][0] + bbox[2][0]) / 2
                                y_center = (bbox[0][1] + bbox[2][1]) / 2
                                detections.append({
                                    'text': text.strip(),
                                    'x': x_center,
                                    'y': y_center,
                                    'conf': conf
                                })

                            # Sort by Y and show
                            detections.sort(key=lambda x: x['y'])
                            for det in detections[:30]:
                                print(f"  Y={det['y']:6.0f} | X={det['x']:6.0f} | {det['conf']:.3f} | {det['text']}")
