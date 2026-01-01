"""Fix duplicate _structure_tft_data functions and add improved version."""

with open('integrations/paddle_ocr_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all function definitions
structure_funcs = []
for i, line in enumerate(lines):
    if 'def _structure_tft_data(self, text_results: List[Dict]) -> Dict:' in line:
        structure_funcs.append(i)
        print(f"Found _structure_tft_data at line {i+1}")

print(f"Found {len(structure_funcs)} _structure_tft_data functions at lines: {structure_funcs}")

# We want to keep the latest one (highest line number) and remove the earlier ones
if len(structure_funcs) >= 2:
    keep_func = structure_funcs[-1]  # Keep the last one
    remove_funcs = structure_funcs[:-1]  # Remove first N-1

    print(f"Keeping function at line {keep_func+1}")
    print(f"Removing functions at lines {[f+1 for f in remove_funcs]}")

    # Find where each removed function ends
    func_ends = []
    for func_line in remove_funcs:
        # Find the next function or end of class
        for i in range(func_line, len(lines)):
            if i > func_line and lines[i].strip().startswith('def '):
                func_ends.append(i)
                break

    # Build new file content
    # Keep everything up to first removed function
    new_lines = lines[:remove_funcs[0]]

    # Add the kept function (last one)
    # Find where it ends
    keep_func_end = None
    for i in range(keep_func + 1, len(lines)):
        if i > keep_func and (lines[i].strip().startswith('def ') or lines[i].strip().startswith('def _') or lines[i].strip().startswith('class ')):
            keep_func_end = i
            break

    if keep_func_end:
        new_lines.extend(lines[keep_func:keep_func_end])
    else:
        new_lines.extend(lines[keep_func:])

    # Write back
    with open('integrations/paddle_ocr_engine.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Fixed duplicate functions. Now has only 1 _structure_tft_data function.")
