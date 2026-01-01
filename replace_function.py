"""Replace _structure_tft_data function with improved version."""

with open('new_structure_function.txt', 'r') as f:
    new_function = f.read()

# Read original file
with open('integrations/paddle_ocr_engine.py', 'r') as f:
    lines = f.readlines()

# Find line 361 (start of function to replace)
# The function starts with 'def _structure_tft_data'
for i, line in enumerate(lines):
    if i == 360 and 'def _structure_tft_data' in lines[i+1]:
        print(f"Found function start at line {i+2}")
        # Replace lines 361-483 with new function
        # First, count lines to 483
        # Old function: 361-483 = 123 lines
        # New function will be different length
        result = lines[:361] + [new_function] + lines[484:]
        with open('integrations/paddle_ocr_engine.py', 'w') as f:
            f.writelines(result)
        print("Successfully replaced _structure_tft_data function")
        break
