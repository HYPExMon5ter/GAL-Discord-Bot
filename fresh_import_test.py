"""Fresh import test."""
import subprocess
import sys

# Force Python to reload module
result = subprocess.run([sys.executable, '-c', '''
import sys
# Remove cached module
for mod in list(sys.modules.keys()):
    if "paddle_ocr_engine" in mod:
        del sys.modules[mod]

from integrations.paddle_ocr_engine import get_paddle_ocr
paddle = get_paddle_ocr()
result = paddle.extract_from_image("dashboard/screenshots/lobbybround3.png")
players = result["structured_data"]["players"]
print(f"Players detected: {len(players)}")
for p in players:
    print(f"  {p['placement']}: {p['name']}")
'''], capture_output=True, text=True, encoding='utf-8')

print(result.stdout)
if result.stderr:
    # Filter out warnings
    for line in result.stderr.split('\n'):
        if 'DEBUG' in line and ('Adding' in line or 'Skipping' in line):
            print(line)
