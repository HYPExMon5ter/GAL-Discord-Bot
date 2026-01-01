"""Debug script to trace OCR processing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

ocr = get_ocr_pipeline()

# Test just one screenshot to debug
screenshot = 'dashboard/screenshots/lobbyaround3.png'
print(f'\n=== Debugging: {screenshot} ===\n')

result = ocr.extract_from_image(screenshot)

if result.get('success'):
    players = result['structured_data']['players']
    print(f'\nPlayers detected: {len(players)}')
    for player in players:
        print(f"  Placement {player['placement']}: {player['name']}")
else:
    print(f"ERROR: {result.get('error')}")
