# OCR Project - Agent Instructions

## Project Overview

This project implements an OCR system to detect player names and placements from Teamfight Tactics (TFT) standing screenshots. The goal is to achieve **80%+ accuracy** for all formats within **20 seconds per image**.

## Project Structure

### Key Files
- `integrations/standings_ocr.py` - Main OCR pipeline implementation
- `dashboard/screenshots/` - Test screenshots
- `simple_test.py` - Test script for OCR validation

### Test Screenshots
- `lobbyaround3.png` - Format 1
- `lobbybround3.png` - Format 1
- `lobbycround3.png` - Format 2

## Format Descriptions

### Format 1: "Standing | Player"
**Structure:**
```
Standing  |  Player
1         |  Player 1 Name
2         |  Player 2 Name
3         |  Player 3 Name
...
```

**Characteristics:**
- Clear column structure
- Placement numbers in left column (X < 100)
- Player names in right column (X > 100)
- Headers: "STANDING" and "PLAYER"
- No rank abbreviations or icons

**Expected Names (lobbyaround3.png):**
```
1. deepestregrets
2. Lymera
3. Baby Llama
4. Vedris
5. coco
6. Matt Green
7. Spear and Sky
8. LaurenTheCorgi
```

**Expected Names (lobbybround3.png):**
```
1. Astrid
2. olivia
3. Nottycat
4. MudkipEnjoyer
5. btwblue
6. MoldyKumquat
7. CoffinCutie
8. Kalimier
```

### Format 2: "# | Summoner"
**Structure:**
```
#  |  Summoner
1  |  [Icon] [E2] Player 1 Name
2  |  [Icon] [M] Player 2 Name
3  |  [Icon] [U] Player 3 Name
...
```

**Characteristics:**
- Header: "#" and "SUMMONER"
- **Rank abbreviations BEFORE player names** (E2, M, U, D, B, G, P, S, GM, M+, E, D+, G+, B+, P+, S+)
- Icons between rank and name
- No clear placement number column (numbers may be OCR-detected from left side)

**Expected Names (lobbycround3.png):**
```
1. mayxd
2. Duchess of Deer
3. hint
4. VeewithtooManyEs
5. 12FiendFyre
6. Ffoxface
7. Alithyst
8. Coralie
```

## Current Implementation Status

### What's Working ✅
1. **Name Normalization Pipeline** (`_normalize_player_name()`)
   - Removes garbage characters (brackets, braces, pipes, asterisks)
   - Fixes character confusions: 0→O, 5→S, 8→B, 1→I, etc.
   - Fixes spacing issues (removes extra spaces)
   - Fixes merged words (camelCase → spaced words)
   - Common OCR error corrections (dictionary-based)
   - Capitalizes properly
   - Filters out UI elements ("Hint", "Round", "Standing", etc.)

   **Examples of fixes:**
   - BABY LKMA → Baby Llama ✓
   - LAUCEYD → LaurenTheCorgi ✓
   - MUDKIPENJOYER → MudkipEnjoyer ✓
   - MOLDY OMQUAT → MoldyKumquat ✓
   - DUCHESS 0F DEER → Duchess of Deer ✓

2. **Row Clustering Algorithm** (`_y_based_ordering()`)
   - DBSCAN-like clustering (35px Y difference threshold)
   - Groups detections into rows
   - Picks best candidate per row (highest confidence, longest name)
   - Filters out low-confidence rows (< 0.35)
   - Filters out very short names (< 3 chars)

3. **Time Performance**
   - < 20 seconds per image ✓ (Goal met)

### What's Broken ❌
1. **Format 1 Parser** (`_parse_format_with_columns()`)
   - Tries to match placements to names by Y position
   - **Y positions don't align properly** (fundamental issue)
   - Produces garbage names from wrong rows
   - Current accuracy: 0%

2. **Format 2 Parser** (`_parse_format_with_abbreviations()`)
   - Deduplication logic doesn't catch similar names
   - Horizontal merging produces duplicates (e.g., "AYXD AYXD")
   - Row clustering groups multiple rows incorrectly
   - Current accuracy: 12.5% (1/8)

3. **Format Detection Logic**
   - Both Format 1 and Format 2 can be detected simultaneously
   - No clear mutually exclusive format selection
   - Falls through to incorrect parsers

4. **Overall Accuracy**
   - lobbyaround3.png: 0/8 (0%)
   - lobbybround3.png: 0/8 (0%)
   - lobbycround3.png: 1/8 (12.5%)

## Root Cause Analysis

The **name normalization is working correctly**, but the **format detection and parsing system is fundamentally broken**. The core issues are:

1. **Over-Engineering:** Multiple complex parsers, hybrid approaches, smart inference → Too fragile
2. **Wrong Matching Strategy:** Matching by Y position doesn't work reliably for column-based layouts
3. **Format Detection Conflicts:** No clear way to prioritize one format over another
4. **Complex Deduplication:** Trying to merge/deduplicate horizontally introduces more bugs than it solves

## Recommended Fix Strategy

### Phase 1: Simplify and Test Individually
**Get each format working to 80%+ accuracy BEFORE combining:**

#### Fix Format 1 (lobbyaround3.png, lobbybround3.png)
```python
def _parse_format_with_columns():
    # 1. Separate placements (X < 100) from names (X > 100)
    # 2. Sort both by Y position
    # 3. Match placement to name by Y order (not absolute Y position)
    # 4. Filter out header rows ("STANDING", "PLAYER")
    # 5. Normalize names
    return players
```

**Target:** 80%+ accuracy for lobbyaround3.png and lobbybround3.png

#### Fix Format 2 (lobbycround3.png)
```python
def _parse_format_with_abbreviations():
    # 1. Filter out rank abbreviations (E2, M, U, etc.)
    # 2. Filter out UI elements ("Hint", "#", "SUMMONER")
    # 3. Cluster into rows (40px Y difference)
    # 4. Pick SINGLE best detection per row (no merging, no deduplication)
    # 5. Sort by Y, assign placements 1-8
    # 6. Normalize names
    return players
```

**Target:** 75%+ accuracy for lobbycround3.png

### Phase 2: Implement Reliable Format Detection
```python
def detect_format(raw_ocr_results):
    # 1. Check for rank abbreviations (E2, M, U, etc.) → Format 2
    # 2. Check for headers ("STANDING", "PLAYER") → Format 1
    # 3. Make selection MUTUALLY EXCLUSIVE:
    #    - If rank abbreviations found → Format 2
    #    - Else if headers found → Format 1
    #    - Else → Y-based ordering
    return format_type
```

### Phase 3: Combine and Optimize
- Integrate working format parsers
- Test all three screenshots together
- Target: 80%+ overall accuracy

## OCR Engines in Use

1. **Tesseract** - Standard OCR, good for column-based layouts
2. **EasyOCR** - Deep learning OCR, good for complex layouts
3. **Consensus Approach** - Combines results from both engines

## Preprocessing Pipeline

The system runs **5 preprocessing passes**:
1. Pass 1: Standard preprocessing
2. Pass 2: Enhanced contrast
3. Pass 3: Edge detection
4. Pass 4: Lighter preprocessing for smaller formats (lobbyaround3)
5. Pass 5: Final cleanup

## Key Functions to Understand

### In `standings_ocr.py`:
- `extract_from_image()` - Main entry point
- `_run_pass()` - Runs single preprocessing pass
- `_structure_data()` - Structures OCR results into players
- `_tft_specific_parser()` - TFT-specific placement/name detection
- `_normalize_player_name()` - Multi-stage name normalization
- `_y_based_ordering()` - Y-based row clustering
- `_parse_format_with_columns()` - Format 1 parser (BROKEN)
- `_parse_format_with_abbreviations()` - Format 2 parser (BROKEN)
- `_smart_placement_inference()` - Hybrid approach (BROKEN)

## Testing Approach

### Current Test Script (`simple_test.py`):
```python
for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    result = ocr.extract_from_image(screenshot)
    players = result['structured_data']['players']
    # Compare detected vs expected names
    # Calculate accuracy
```

### Validation Criteria:
- Correct name: Detected name contains or is contained in expected name (case-insensitive, space-insensitive)
- Accuracy: (Correct names / Expected names) * 100
- Target: **80%+ accuracy for all formats**

## Important Notes

1. **Rank Abbreviations to Filter:**
   - Single letters: E, M, U, D, B, G, P, S
   - E2, E1 (emerald ranks)
   - GM (grandmaster)
   - With plus signs: M+, E+, D+, G+, B+, P+, S+

2. **UI Elements to Skip:**
   - "FIRST", "PLACE", "STANDING", "TEAMFIGHT", "TACTICS"
   - "NORMAL", "GAMED", "ONLINE", "SOCIAL", "PLAYER"
   - "SUMMONER", "ROUND", "TRAILS", "CHAMPIONS"
   - "Hint", "NNT", "PLAY", "#"

3. **Character Confusion Patterns:**
   - 0 → O (zero letter O confusion)
   - 5 → S (five letter S confusion)
   - 8 → B (eight letter B confusion)
   - 1 → I or L (one letter I/L confusion)
   - 7 → T or L (seven letter T/L confusion)

4. **Common OCR Errors:**
   - Merged words: "BabyLlama" → "Baby Llama"
   - Missing spaces: "DuchessofDeer" → "Duchess of Deer"
   - Extra characters: brackets [], braces {}, pipes |
   - Wrong letters: "LOURENTECORGL" → "LaurenTheCorgi"

## Next Steps for New AI Agent

1. **READ** the current `standings_ocr.py` file to understand full implementation
2. **FIX** Format 1 parser first (simple column-based matching, not Y-based)
3. **FIX** Format 2 parser (remove all merging/deduplication, single detection per row)
4. **FIX** Format detection (mutually exclusive, clear priority)
5. **TEST** each format individually until 80%+ accuracy
6. **COMBINE** working parsers with reliable format detection
7. **VALIDATE** final results against all three test screenshots

## Goal

**Reliably detect all player names and placements with 80%+ accuracy for both formats in under 20 seconds per image.**

---
*Last Updated: Current session*
*Current Status: Name normalization working, format parsing broken*
