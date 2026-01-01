# Comprehensive OCR System Implementation Plan
**Goal: 80%+ accuracy, <20s per image, concurrent processing support**

## Current State Analysis

### What's Working ✅
- **Name normalization pipeline** - Excellent character confusion handling (0→O, 5→S, etc.)
- **Time performance** - Already under 20 seconds
- **Multi-pass preprocessing** - 4-5 preprocessing passes with adaptive thresholding
- **Dual OCR engines** - Tesseract + EasyOCR consensus approach

### Critical Issues ❌
1. **Format 1 Parser (Standing | Player)** - 0% accuracy due to Y-position misalignment
2. **Format 2 Parser (# | Summoner)** - 12.5% accuracy due to duplicate detection and poor deduplication
3. **Format Detection** - Non-mutually exclusive, both formats can trigger simultaneously
4. **No concurrent processing** - Serial processing only

## Implementation Strategy

### Phase 1: Fix Format Detection (Mutually Exclusive)
**Priority: CRITICAL | Impact: Foundation for all parsing**

**Changes:**
1. Create clear priority hierarchy:
   - **Format 2 indicators** (highest): Rank abbreviations (E2, M, U, D, B, G, P, S, GM, etc.)
   - **Format 1 indicators** (medium): Headers ("STANDING", "PLAYER")
   - **Fallback**: Y-based ordering if neither detected

2. Make format selection **mutually exclusive**:
   ```python
   if rank_abbreviations_detected:
       return Format2Parser()  # STOP HERE
   elif column_headers_detected:
       return Format1Parser()  # STOP HERE
   else:
       return YBasedParser()   # FALLBACK
   ```

3. Add format detection confidence scoring to prevent false positives

---

### Phase 2: Rebuild Format 1 Parser (Column-Based)
**Priority: CRITICAL | Target: 80%+ accuracy for lobbyaround3.png, lobbybround3.png**

**Root Cause:** Current parser tries to match placements to names by absolute Y position, but OCR Y-coordinates don't align properly.

**Solution - Simplified Y-Order Matching:**
1. **Separate detections by X position:**
   - Placement numbers: `X < 200` (left column)
   - Player names: `X > 150` (right column)

2. **Sort both lists by Y position** (top to bottom)

3. **Match by INDEX, not absolute Y:**
   ```python
   placements = sort_by_y([detect for detect in ocr if detect.x < 200 and detect.is_digit])
   names = sort_by_y([detect for detect in ocr if detect.x > 150 and detect.is_name])
   
   for i, placement in enumerate(placements):
       if i < len(names):
           match_placement_to_name(placement, names[i])
   ```

4. **Filter out headers:** Skip "STANDING", "PLAYER", "FIRST", "PLACE"

**Expected Result:** 7-8/8 players matched correctly (87.5%+ accuracy)

---

### Phase 3: Rebuild Format 2 Parser (Single Detection Per Row)
**Priority: CRITICAL | Target: 75%+ accuracy for lobbycround3.png**

**Root Cause:** Over-engineering with horizontal merging, deduplication causing duplicate names and missed detections.

**Solution - Simplified Row Clustering:**
1. **Filter out rank abbreviations** (E2, M, U, D, B, G, P, S, GM, M+, E+, etc.)
   - Remove from text ONLY if at start or as separate word
   - Don't remove if it's just a letter in the name (e.g., "E" in "DEEPESTREGRETS")

2. **Filter out UI elements** ("#", "SUMMONER", "HINT", "ROUND")

3. **Cluster into rows** (40px Y threshold):
   ```python
   for item in sorted_by_y(ocr_results):
       if any_row_within_40px(item):
           add_to_existing_row(item)
       else:
           create_new_row(item)
   ```

4. **Pick SINGLE best detection per row:**
   - Sort by: confidence DESC, length DESC
   - Pick top item (NO merging, NO deduplication)

5. **Assign placements 1-8** based on Y-order

6. **Normalize names** using existing pipeline

**Expected Result:** 6-7/8 players matched correctly (75%+ accuracy)

---

### Phase 4: Add Concurrent Processing Support
**Priority: HIGH | Target: Process 3 images in 25-30 seconds (vs 60 seconds serial)**

**Implementation:**
1. **Python ThreadPoolExecutor for I/O-bound operations:**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   def process_batch(image_paths):
       with ThreadPoolExecutor(max_workers=3) as executor:
           futures = [executor.submit(extract_from_image, path) for path in image_paths]
           return [f.result() for f in futures]
   ```

2. **Shared resource handling:**
   - EasyOCR reader singleton (thread-safe)
   - Tesseract via subprocess (inherently parallel)

3. **Batch API for Discord bot:**
   ```python
   # Process 3 lobby screenshots simultaneously
   results = ocr.process_batch([
       'lobbyaround3.png',
       'lobbybround3.png', 
       'lobbycround3.png'
   ])
   ```

**Expected Result:** 3 images processed in ~25 seconds (8-9 sec each with overhead)

---

### Phase 5: Optimize Preprocessing Pipeline
**Priority: MEDIUM | Target: Reduce per-image time to 12-15 seconds**

**Optimizations:**
1. **Early stopping:** If Pass 3 finds 8 players, skip Pass 4-5
   - Already partially implemented, needs refinement

2. **Adaptive pass selection:**
   ```python
   if image_format_is_format1:
       run_passes = [1, 2, 3]  # Skip pass 4 (designed for format 2)
   else:
       run_passes = [1, 2, 4, 5]  # Skip pass 3 (too aggressive for format 2)
   ```

3. **ROI detection (optional):**
   - Crop image to left 50% (user stated "names are on left side")
   - Reduces OCR processing area by 50%

4. **Scale normalization improvements:**
   - Current: Resize to 1295x865 if > 25% difference
   - Enhancement: Skip resize for small formats (< 900px height) - already implemented

**Expected Result:** 12-15 seconds per image (down from current 18-20 seconds)

---

### Phase 6: Validation & Testing Framework
**Priority: MEDIUM | Target: Automated accuracy tracking**

**Components:**
1. **Test harness with expected results:**
   ```python
   EXPECTED = {
       'lobbyaround3.png': ['deepestregrets', 'Lymera', 'Baby Llama', ...],
       'lobbybround3.png': ['Astrid', 'olivia', 'Nottycat', ...],
       'lobbycround3.png': ['mayxd', 'Duchess of Deer', 'hint', ...]
   }
   ```

2. **Fuzzy validation:**
   - Substring matching (case-insensitive, space-insensitive)
   - Character confusion handling (0↔O, 5↔S, etc.)

3. **Automated reporting:**
   ```
   lobbyaround3.png: 7/8 correct (87.5%)
   lobbybround3.png: 8/8 correct (100%)
   lobbycround3.png: 6/8 correct (75%)
   Overall: 21/24 = 87.5% accuracy ✅
   ```

4. **Performance metrics:**
   - Average time per image
   - Batch processing speedup factor

---

### Phase 7: Enhanced Error Handling & Logging
**Priority: LOW | Target: Better debugging and monitoring**

**Improvements:**
1. **Structured logging with context:**
   ```python
   log.info(f"Format detection: Format2=True, Format1=False → Using Format2Parser")
   log.info(f"Format2 parser: Found 6 rows, selected 6 names")
   ```

2. **Confidence scoring per detection:**
   - Track OCR confidence for each player
   - Flag low-confidence matches for review

3. **Debug mode with visual output:**
   - Save annotated images with bounding boxes
   - Highlight detected placements vs names

---

## Success Criteria

| Metric | Target | Current | After Implementation |
|--------|--------|---------|----------------------|
| **Accuracy (Format 1)** | 80%+ | 0% | 85%+ |
| **Accuracy (Format 2)** | 80%+ | 12.5% | 75%+ |
| **Overall Accuracy** | 80%+ | 4% | 82%+ |
| **Time per image** | <20s | 18-20s | 12-15s |
| **Batch (3 images)** | <60s | 54-60s | 25-30s |
| **Concurrent support** | Yes | No | Yes ✅ |

---

## Implementation Order

1. **Phase 1** (Format Detection) - 2 hours
2. **Phase 2** (Format 1 Parser) - 3 hours
3. **Phase 3** (Format 2 Parser) - 3 hours
4. **Phase 4** (Concurrent Processing) - 2 hours
5. **Phase 6** (Testing Framework) - 1 hour
6. **Phase 5** (Optimization) - 2 hours (optional)
7. **Phase 7** (Error Handling) - 1 hour (optional)

**Total Core Implementation: 10 hours**
**Total with Optional: 13 hours**

---

## Files to Modify

1. `integrations/standings_ocr.py` - Main OCR pipeline
   - `_tft_specific_parser()` - Format detection logic
   - `_parse_format_with_columns()` - Format 1 parser
   - `_parse_format_with_abbreviations()` - Format 2 parser
   - Add `process_batch()` method for concurrent processing

2. `simple_test.py` - Testing harness
   - Add concurrent batch testing
   - Enhanced validation and reporting

3. `config.yaml` - Configuration
   - Add concurrent processing settings
   - Add format detection thresholds

4. **New file:** `integrations/batch_processor.py`
   - ThreadPoolExecutor wrapper
   - Batch processing utilities

---

## Risk Mitigation

1. **Backup current system:** Git commit before changes
2. **Incremental testing:** Test each phase independently
3. **Fallback logic:** Keep Y-based ordering as last resort
4. **Format detection confidence:** Don't force format if unclear (use fallback)

---

## Post-Implementation Options

### Optional Enhancement: PaddleOCR Upgrade
- Replace Tesseract+EasyOCR with single PaddleOCR engine
- 30-50% faster, similar or better accuracy
- Effort: 4-6 hours
- **Benefit:** 8-10 seconds per image, 20-25 seconds for batch of 3

### Optional Enhancement: Cloud Vision API
- Replace entire OCR with Google Cloud Vision or AWS Textract
- 95-98% accuracy, 2-4 seconds per image
- Cost: ~$0.01-0.03 per image
- **Benefit:** Highest accuracy, minimal maintenance

---

## Next Steps

1. Approve this specification
2. I'll implement Phases 1-4 + 6 (core functionality)
3. Test with your 3 screenshots
4. Iterate based on results
5. Optionally implement Phase 5 + 7 (optimizations)