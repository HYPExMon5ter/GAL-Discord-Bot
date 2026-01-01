#!/usr/bin/env python3
"""Apply comprehensive fixes to cloud_vision_ocr.py"""

with open('integrations/cloud_vision_ocr.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the POST-MERGE cleanup section
output = []
in_cleanup = False
for i, line in enumerate(lines):
    if '# POST-MERGE: Clean up text' in line:
        in_cleanup = True
        output.append(line)
        continue
    
    if in_cleanup:
        # Replace the old cleanup with new comprehensive cleanup
        if 'Remove timestamps from merged text' in line:
            output.append(line)
            # Add the new cleanup lines
            output.append("            # Remove all score artifacts and UI elements aggressively\n")
            output.append("            # 1. Remove timestamps: \"Name 36:26\" -> \"Name\"\n")
            output.append("            text = re.sub(r'\\\\s+\\\\d{1,2}:\\\\d{2}\\\\s*', '', text).strip()\n")
            output.append("            # 2. Remove score ratios: \"Name 0/3\", \"Name 6-5\" -> \"Name\"\n")
            output.append("            text = re.sub(r'\\\\s+\\\\d+[/-]\\\\d+\\\\s*$', '', text).strip()\n")
            output.append("            text = re.sub(r'\\\\s+\\\\d+[/-]\\\\d+\\\\s+', '', text).strip()\n")
            output.append("            # 3. Remove pts paren: \"Name (8 pts)\" -> \"Name\"\n")
            output.append("            text = re.sub(r'\\\\s+\\\\(\\\\d+\\\\s*pts?\\\\)\\\\s*$', '', text).strip()\n")
            output.append("            # 4. Remove UI prefixes/suffixes: \"U mayxd\", \"P2 Ffoxface\"\n")
            output.append("            text = re.sub(r'^\\\\s*[A-ZUEPO]\\\\d+\\\\s*', '', text).strip()\n")
            output.append("            text = re.sub(r'\\\\s+[A-ZUEPO]\\\\d+\\\\s*$', '', text).strip()\n")
            output.append("\n")
            output.append("            item['text'] = text\n")
            # Skip old cleanup lines
            if "item['text']" in line or 'Remove UI prefixes' in line or 'Remove UI suffixes' in line:
                continue
        else:
            output.append(line)
    else:
        output.append(line)

with open('integrations/cloud_vision_ocr.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print("Applied comprehensive score artifact and UI cleanup!")
