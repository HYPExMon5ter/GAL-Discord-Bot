"""Simple OCR test - one screenshot at a time."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

ocr = get_ocr_pipeline()

# Test all screenshots
results_summary = {}
for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    print(f'\n--- Testing: {screenshot} ---')
    result = ocr.extract_from_image(f'dashboard/screenshots/{screenshot}')

    if result.get('success'):
        players = result['structured_data']['players']
        print(f'Players detected: {len(players)}')
        for player in players:
            print(f"  Placement {player['placement']}: {player['name']}")
        results_summary[screenshot] = {
            'count': len(players),
            'players': [p['name'] for p in players]
        }
    else:
        print(f"ERROR: {result.get('error')}")
        results_summary[screenshot] = {'error': result.get('error')}

# Print summary
print("\n" + "="*80)
print("SUMMARY OF RESULTS")
print("="*80)
expected_names = {
    'lobbyaround3.png': ['deepestregrets', 'Lymera', 'Baby Llama', 'Vedris',
                     'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi'],
    'lobbybround3.png': ['Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer',
                     'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier'],
    'lobbycround3.png': ['mayxd', 'Duchess of Deer', 'hint', 'VeewithtooManyEs',
                     '12FiendFyre', 'Ffoxface', 'Alithyst', 'Coralie']
}

for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    print(f"\n{screenshot}:")
    if screenshot in results_summary:
        if 'error' in results_summary[screenshot]:
            print(f"  ERROR: {results_summary[screenshot]['error']}")
        else:
            detected = results_summary[screenshot]['players']
            expected = expected_names.get(screenshot, [])
            correct = 0
            for d, e in zip(detected, expected):
                # Normalize for comparison (case insensitive, space insensitive)
                # Use fuzzy matching: name is correct if detected contains expected or vice versa
                d_norm = d.lower().replace(' ', '')
                e_norm = e.lower().replace(' ', '')

                # Check if detected contains expected (substring match)
                # OR if expected contains detected
                if d_norm in e_norm or e_norm in d_norm:
                    correct += 1
            
            accuracy = (correct / max(len(detected), len(expected))) * 100 if expected else 0
            print(f"  Expected: {expected}")
            print(f"  Detected: {detected}")
            print(f"  Correct: {correct}/{max(len(detected), len(expected))} ({accuracy:.1f}%)")
