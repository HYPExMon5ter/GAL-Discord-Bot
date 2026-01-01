import re

# Read the file
with open('integrations/cloud_vision_ocr.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add space in merge (remove curly braces)
content = content.replace(
    'merged_text = f"{item1[\'text\'].strip()}{item2[\'text\'].strip()}"',
    'merged_text = f"{item1[\'text\'].strip()} {item2[\'text\'].strip()}"'
)
content = content.replace(
    'merged_text = f"{item2[\'text\'].strip()}{item1[\'text\'].strip()}"',
    'merged_text = f"{item2[\'text\'].strip()} {item1[\'text\'].strip()}"'
)

# Fix 2: Add timestamp filtering
timestamp_filter = '''            # FILTER: Skip timestamp patterns (HH:MM format)
            # e.g., "36:26", "34:05", "28:26", "26:07", "24:10", "24:24"
            if re.match(r'^\\d{1,2}:\\d{2}$', text):
                log.debug(f"Skipping timestamp: {text}")
                continue
            
            # FILTER: Skip UI elements with colon prefix (e.g., "P2:", "E4:")
            if re.match(r'^[A-Z]\\d+:', text):
                log.debug(f"Skipping UI element: {text}")
                continue
'''

# Find alpha_count line and insert filtering before it
content = content.replace(
    '            # Check if this looks like a player name',
    timestamp_filter + '            # Check if this looks like a player name'
)

# Write back
with open('integrations/cloud_vision_ocr.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed: 1. Merge spacing, 2. Timestamp filtering")
