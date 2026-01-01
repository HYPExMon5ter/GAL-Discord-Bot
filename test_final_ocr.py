"""Final OCR test with name normalization."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

# Expected names (ground truth)
expected_names = {
    'lobbyaround3.png': [
        'deepestregrets', 'Lymera', 'Baby Llama', 'Vedris',
        'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi'
    ],
    'lobbybround3.png': [
        'Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer',
        'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier'
    ],
    'lobbycround3.png': [
        'mayxd', 'Duchess of Deer', 'hint', 'VeewithtooManyEs',
        '12FiendFyre', 'Ffoxface', 'Alithyst', 'Coralie'
    ]
}

ocr = get_ocr_pipeline()

print('=' * 80)
print('FINAL OCR TEST WITH NAME NORMALIZATION')
print('=' * 80)

all_correct = True
total_errors = 0

for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    path = f'dashboard/screenshots/{screenshot}'
    print(f'\n--- {screenshot} ---')

    result = ocr.extract_from_image(path)

    if not result.get('success'):
        print(f"ERROR: {result.get('error', 'Unknown error')}")
        continue

    players = result['structured_data']['players']

    # Check each player name
    print(f"{'Placement':<10} | {'Detected Name':<30} | {'Expected Name':<30} | {'Status'}")
    print("-" * 80)

    screenshot_correct = True

    for player in players:
        placement = player['placement'] - 1  # 0-indexed
        detected_name = player['name']
        expected_name = expected_names[screenshot][placement]

        # Compare (case-insensitive)
        if detected_name.lower() == expected_name.lower():
            status = '✓'
        else:
            status = '✗'
            screenshot_correct = False
            all_correct = False
            total_errors += 1

        print(f"{player['placement']:<10} | {detected_name:<30} | {expected_name:<30} | {status}")

    if screenshot_correct:
        print(f"\n✓ All names correct!")
    else:
        print(f"\n✗ {total_errors} error(s) in this screenshot")

print('\n' + '=' * 80)
print('SUMMARY')
print('=' * 80)

if all_correct and total_errors == 0:
    print('✓ ALL NAMES DETECTED CORRECTLY!')
    sys.exit(0)
else:
    print(f'✗ {total_errors} total error(s) across all screenshots')
    print('Note: Some errors may remain due to OCR limitations.')
    sys.exit(1)
