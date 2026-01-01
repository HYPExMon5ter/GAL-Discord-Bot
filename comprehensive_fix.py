import re

# Read the current file
with open('integrations/cloud_vision_ocr.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Increase merge thresholds for better name detection
content = content.replace(
    'if y_gap > 15:',
    'if y_gap > 25:'
)
content = content.replace(
    'if x_gap > 150 or item2["center_x"] < item1["center_x"]:',
    'if x_gap > 250 or item2["center_x"] < item1["center_x"]:'
)

# Fix 2: Add better UI element filtering to skip artifacts
# Add filtering for "U mayxd", "E2 12FiendFyre", "P2 Ffoxface", "MAGICAL 0/3"
old_name_check = '''if alpha_count >= 3 and 4 <= len(text) <= 20:
                # Avoid duplicates (case insensitive)
                if not any(n[0].upper() == text_upper for n in names):
                    names.append((text, y_pos, x_pos))'''

new_name_check = '''# FILTER: Skip score artifacts like "0/3", "1/5"
            if re.match(r'^\\d+/\\d+$', text):
                log.debug(f"Skipping score artifact: {text}")
                continue
            
            # FILTER: Skip single letter UI prefixes (U, E, P, etc.)
            if len(text) == 1 and text.isalpha() and text.isupper():
                log.debug(f"Skipping single char UI: {text}")
                continue
            
            if alpha_count >= 3 and 4 <= len(text) <= 20:
                # Avoid duplicates (case insensitive)
                if not any(n[0].upper() == text_upper for n in names):
                    names.append((text, y_pos, x_pos))'''

content = content.replace(old_name_check, new_name_check)

# Fix 3: Improve post-merge cleanup to remove score artifacts
old_cleanup = '''# POST-MERGE: Clean up text
        for item in merged:
            text = item["text"]
            
            # Remove timestamps from merged text (e.g., "Name 36:26" -> "Name")
            text = re.sub(r'\\s\\d{1,2}:\\d{2}(?=\\s|$)', '', text).strip()
            # Remove UI prefixes/suffixes with colon or space+digit (e.g., "U mayxd", "E2 12FiendFyre")
            # Patterns: "U mayxd", "E2 12FiendFyre", "P2 Ffoxface"
            text = re.sub(r'^[A-ZUE]\\s*\\d+\\s*', '', text).strip()
            text = re.sub(r'\\s+[A-ZUEP]\\d+\\s*$', '', text).strip()
            
            item["text"] = text'''

new_cleanup = '''# POST-MERGE: Clean up text
        for item in merged:
            text = item["text"]
            
            # Remove timestamps from merged text (e.g., "Name 36:26" -> "Name")
            text = re.sub(r'\\s\\d{1,2}:\\d{2}(?=\\s|$)', '', text).strip()
            # Remove score artifacts (e.g., "0/3", "1/5")
            text = re.sub(r'\\s+\\d+/\\d+\\s*', '', text).strip()
            text = re.sub(r'\\s+\\(\\d+\\s*pts\\)\\s*', '', text).strip()
            # Remove UI prefixes/suffixes (e.g., "U mayxd" -> "mayxd", "E2 12FiendFyre" -> "12FiendFyre")
            text = re.sub(r'^[A-ZUEPO]\\s*\\d+\\s*', '', text).strip()
            text = re.sub(r'\\s+[A-ZUEPO]\\s*\\d+\\s*$', '', text).strip()
            
            item["text"] = text'''

content = content.replace(old_cleanup, new_cleanup)

# Write back
with open('integrations/cloud_vision_ocr.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed:")
print("  1. Increased merge thresholds (Y: 15->25px, X: 150->250px)")
print("  2. Added score artifact filtering (skip '0/3', '1/5')")
print("  3. Added single-char UI element filtering")
print("  4. Improved post-merge cleanup (remove all UI prefixes/suffixes, scores)")
