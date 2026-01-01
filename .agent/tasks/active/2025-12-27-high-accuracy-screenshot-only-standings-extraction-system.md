# High-Accuracy Screenshot-Only Standings Extraction System

## Overview
Implement a production-grade automated system to monitor Discord channels for standings screenshots, extract placement data with **99%+ accuracy** using multi-stage OCR with validation, and store results in the database for live dashboard graphics. System supports **batch processing** for concurrent screenshot uploads with manual editing capabilities.

**Key Change**: No Riot API dependency - screenshot extraction is the primary and only automated data source, with manual correction interface for edge cases and tie-breakers.

---

## Accuracy Strategy: Multi-Stage Validation Pipeline

### Target: 99%+ Accuracy (Screenshot-Only)
To achieve 99%+ accuracy without Riot API cross-validation:

1. **Template Matching** - Pre-classify screenshot type with high confidence
2. **Advanced Preprocessing** - Multiple preprocessing passes optimized for TFT screenshots
3. **Ensemble OCR** - Run multiple OCR engines and cross-validate results
4. **Player Roster Validation** - Strict matching against registered tournament players
5. **Structural Validation** - Verify game rules (8 players, unique placements 1-8)
6. **Cross-Lobby Consistency** - Validate placements across multiple lobby screenshots
7. **Confidence Scoring** - Multi-dimensional confidence calculation
8. **Manual Editing Interface** - Staff can review and correct any extraction before finalizing

---

## System Architecture

### 1. **Discord Screenshot Monitor** (New Component)
**Location**: `core/events/handlers/screenshot_monitor.py`

**Features**:
- Monitor configured channel(s) for image attachments
- **Batch detection**: Queue multiple images posted within 30-second window
- Download to temporary storage with unique IDs
- Parallel processing queue (asyncio)
- Rate limiting and error handling
- Notify staff channel when screenshots detected

**Discord Event Handler**:
```python
@bot.event
async def on_message(message):
    # Check if message is in monitored standings channel
    # Check for image attachments (.png, .jpg, .jpeg)
    # Add to batch processing queue
    # If batch window expires, trigger batch processing
```

### 2. **Screenshot Classifier** (New Component)
**Location**: `integrations/screenshot_classifier.py`

**Purpose**: Determine if image is TFT standings screenshot with high confidence

**Classification Techniques**:
- **Template matching** using OpenCV (match against known TFT UI elements)
- **Keyword detection** via OCR preview scan:
  - "PLACEMENT" or "PLACE"
  - "1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH"
  - "GAME TIME" or time indicators
  - Player names region detection
- **Color profile matching** (TFT UI has distinct color palette)
- **Aspect ratio validation** (TFT screenshots have consistent dimensions)
- **Layout structure detection** (standings grid pattern)

**Confidence threshold**: >95% to proceed to full OCR

### 3. **Advanced OCR Pipeline** (New Component)
**Location**: `integrations/standings_ocr.py`

**Multi-Engine Ensemble Approach**:

#### OCR Engines:
1. **Tesseract OCR** (Primary) - Open-source, customizable, well-tested
2. **EasyOCR** (Secondary) - Deep learning-based, better for stylized fonts
3. **Cross-validation**: Compare outputs, use consensus or highest confidence

#### Preprocessing Pipeline (3-Pass System):

**Pass 1: High-Contrast Extraction**
```python
- Convert to grayscale
- Adaptive thresholding (Otsu's method)
- Contrast enhancement (CLAHE - Contrast Limited Adaptive Histogram Equalization)
- Noise reduction (Gaussian blur)
- Run OCR, store results
```

**Pass 2: Sharp Edge Extraction**
```python
- Bilateral filtering (preserve edges while reducing noise)
- Morphological operations (dilation/erosion)
- Sharpening filter
- Text region detection (EAST text detector or MSER)
- Run OCR, store results
```

**Pass 3: Inversion Pass (for dark mode/different UI themes)**
```python
- Color inversion
- Repeat Pass 1 preprocessing
- Run OCR, store results
- Compare with non-inverted results
```

**Consensus Algorithm**:
```python
# Compare all 3 passes + 2 OCR engines = up to 6 results per text region
# Use voting system: if 4+ agree on text, use that
# If disagreement, flag for manual review
# Calculate per-character confidence scores
```

#### Text Extraction Strategy:
- **Region of Interest (ROI) Detection**: 
  - Automatically detect player name columns
  - Detect placement number columns
  - Grid-based extraction (TFT standings are structured in predictable layout)
- **Layout analysis**: Identify rows (each player) and columns (name, placement)
- **Character-level confidence**: Track confidence per character, not just per word
- **Spatial validation**: Verify placement numbers are aligned with player names

### 4. **Player Matching Engine** (New Component)
**Location**: `integrations/player_matcher.py`

**Purpose**: Match extracted names to registered tournament players with high confidence

**Matching Strategy**:

**Tier 1 - Exact Matching** (Highest confidence: 100%):
- Case-insensitive comparison
- Whitespace normalization
- Special character handling

**Tier 2 - Alias Matching** (High confidence: 95%):
- Check against player_aliases table
- Known IGN variations
- Discord name → IGN mapping from registration

**Tier 3 - Fuzzy Matching** (Medium-High confidence: 85-95%):
- Levenshtein distance calculation (rapidfuzz)
- Threshold: 95% similarity for auto-accept
- Common OCR errors handled:
  - "1" ↔ "l" ↔ "I"
  - "0" ↔ "O"
  - "5" ↔ "S"
  - "8" ↔ "B"
  - Spaces vs underscores

**Tier 4 - Manual Review** (Low confidence: <85%):
- Flag for staff review
- Show closest matches from roster
- Allow manual selection

**Unmatched Player Handling**:
- If player not in roster, flag for review
- Could be typo, could be substitute/emergency add
- Staff can add to roster on-the-fly during validation

### 5. **Structural Validator** (New Component)
**Location**: `integrations/placement_validator.py`

**Validation Rules** (Must ALL pass for auto-validation):

**Single Lobby Validation**:
- ✅ Exactly 8 players per lobby
- ✅ Placements 1-8 all present, no duplicates
- ✅ No duplicate player names in same lobby
- ✅ All players matched to tournament roster (or flagged for review)

**Multi-Lobby Cross-Validation** (for round with multiple screenshots):
- ✅ No player appears in multiple lobbies for same round
- ✅ Expected number of lobbies (e.g., 32 players = 4 lobbies)
- ✅ Lobby identifiers are valid (Lobby 1, 2, 3, 4)

**Round Sequence Validation**:
- ✅ Round number is sequential (no skipping rounds)
- ✅ No duplicate submissions for same round/lobby

**Tie-Breaker Detection**:
- If multiple players have same points after round, flag for manual tie-breaker entry
- Provide interface to specify tie-breaker placement

### 6. **Confidence Scoring System** (New Component)
**Location**: `integrations/confidence_scorer.py`

**Multi-Dimensional Confidence Calculation**:

```python
# Calculate overall confidence score (0.0 - 1.0)
confidence_score = weighted_average([
    classification_confidence * 0.15,    # Screenshot is TFT standings
    ocr_consensus_confidence * 0.25,     # OCR engines agree on text
    ocr_character_confidence * 0.15,     # Per-character confidence avg
    player_match_confidence * 0.30,      # All players matched to roster
    structural_validity_score * 0.15,    # Passes all validation rules
])

# Confidence Thresholds:
# >= 0.98 (98%) → Auto-validate (very high confidence)
# 0.90-0.98 → Staff review recommended (good, but verify)
# < 0.90 → Requires manual review (low confidence)
```

**Per-Player Confidence**:
- Track confidence for each extracted player individually
- Flag specific players that need review (e.g., 7/8 high confidence, 1 low)

### 7. **Manual Editing Interface** (New Component)
**Location**: `dashboard/app/admin/placements/edit/[id]/page.tsx`

**Features**:

**Side-by-Side View**:
- Left: Original screenshot (zoomable)
- Right: Extracted data table

**Editing Capabilities**:
- ✏️ **Edit player names**: Dropdown with roster + fuzzy search
- ✏️ **Edit placements**: Dropdown 1-8, prevent duplicates
- ➕ **Add missing player**: If OCR missed someone
- ❌ **Remove incorrect player**: If OCR hallucinated a player
- 🔄 **Reorder players**: Drag-and-drop to fix placement order
- 🏆 **Tie-breaker entry**: Specify exact order for tied players

**Validation Indicators**:
- 🟢 High confidence (green highlight)
- 🟡 Medium confidence (yellow highlight)
- 🔴 Low confidence / flagged (red highlight)
- Show specific concerns per player

**Quick Actions**:
- ✅ **Approve As-Is**: If extraction looks perfect
- ✅ **Approve After Edit**: Save changes and validate
- ❌ **Reject Screenshot**: Invalid/unclear screenshot
- 🔄 **Reprocess**: Retry OCR with different settings

**Bulk Editing** (for full round):
- Review all lobbies for a round at once
- One-click approve if all look good
- Quickly fix consistent issues (e.g., same player name OCR error across lobbies)

### 8. **Placement Storage Service** (New Component)
**Location**: `api/services/placement_service.py`

**Responsibilities**:
- Store raw OCR results with confidence scores
- Store validated placements
- Handle duplicate detection (same round/lobby)
- Support updates/corrections via manual editing
- Maintain complete audit trail
- Trigger scoreboard refresh after validation
- Calculate points based on placement

**Points Calculation**:
```python
PLACEMENT_POINTS = {
    1: 8,
    2: 7,
    3: 6,
    4: 5,
    5: 4,
    6: 3,
    7: 2,
    8: 1
}
```

### 9. **Batch Processing Queue** (New Component)
**Location**: `integrations/batch_processor.py`

**Features**:
- Async queue for concurrent processing
- Collect screenshots posted within 30-second window
- Process in parallel using `asyncio.gather()`
- Configurable max concurrent workers (default: 4)
- Progress tracking and status updates to staff channel
- Error isolation (one failure doesn't break batch)
- Retry logic for transient failures

**Batch Intelligence**:
- Detect if batch represents complete round (e.g., 4 screenshots for 4 lobbies)
- Group by round automatically if possible (detect round name in screenshot or message)
- Cross-validate entire round before finalizing

---

## Database Schema

### New Tables:

```sql
-- Raw submission data from screenshot processing
CREATE TABLE placement_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    tournament_id TEXT NOT NULL,
    round_name TEXT NOT NULL,
    lobby_number INTEGER NOT NULL,
    
    -- Source tracking
    discord_message_id TEXT NOT NULL UNIQUE,
    discord_channel_id TEXT NOT NULL,
    discord_author_id TEXT,              -- Who posted the screenshot
    image_url TEXT NOT NULL,
    image_hash TEXT,                      -- For duplicate detection
    
    -- Processing metadata
    classification_score FLOAT,          -- Template match confidence (0-1)
    ocr_consensus_confidence FLOAT,      -- OCR engines agreement (0-1)
    ocr_character_confidence FLOAT,      -- Avg per-character confidence (0-1)
    player_match_confidence FLOAT,       -- Player matching confidence (0-1)
    structural_validity_score FLOAT,     -- Validation checks (0-1)
    overall_confidence FLOAT NOT NULL,   -- Final weighted score (0-1)
    
    -- OCR results (all engines for debugging)
    extracted_data_tesseract JSON,
    extracted_data_easyocr JSON,
    extracted_data_consensus JSON NOT NULL,  -- Final agreed-upon data
    
    -- Processing status
    status TEXT NOT NULL DEFAULT 'pending',  
    -- Status values: pending, validated, rejected, error, duplicate
    
    validation_method TEXT,                   -- auto, manual, hybrid
    validated_by_discord_id TEXT,
    validation_notes TEXT,
    edited BOOLEAN DEFAULT FALSE,            -- Was manually edited
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Batch tracking
    batch_id INTEGER REFERENCES processing_batches(id),
    
    -- Timestamps
    processed_at TIMESTAMP,
    validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_tournament_round (tournament_id, round_name),
    INDEX idx_guild_tournament (guild_id, tournament_id),
    INDEX idx_status (status),
    INDEX idx_confidence (overall_confidence),
    INDEX idx_message (discord_message_id),
    INDEX idx_batch (batch_id)
);

-- Validated per-player placement records
CREATE TABLE round_placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES placement_submissions(id) ON DELETE CASCADE,
    
    -- Player identification
    player_id TEXT NOT NULL,           -- Internal player ID
    player_name TEXT NOT NULL,          -- Display name
    discord_id TEXT,                    -- Discord user ID
    riot_id TEXT,                       -- Riot IGN
    
    -- Tournament context
    tournament_id TEXT NOT NULL,
    round_name TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    lobby_number INTEGER NOT NULL,
    
    -- Placement data
    placement INTEGER NOT NULL CHECK (placement >= 1 AND placement <= 8),
    points INTEGER NOT NULL,
    
    -- Tie-breaker support
    is_tie BOOLEAN DEFAULT FALSE,
    tie_breaker_rank INTEGER,          -- If tied, what's the specific order
    
    -- Confidence tracking (per player)
    extraction_confidence FLOAT,       -- Confidence in OCR extraction
    player_match_confidence FLOAT,     -- Confidence in player matching
    match_method TEXT,                  -- exact, alias, fuzzy, manual
    
    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    manually_corrected BOOLEAN DEFAULT FALSE,
    validated_by_discord_id TEXT,
    correction_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(tournament_id, round_name, lobby_number, player_id),
    UNIQUE(tournament_id, round_name, lobby_number, placement),  -- No duplicate placements
    
    INDEX idx_player_tournament (player_id, tournament_id),
    INDEX idx_tournament_round (tournament_id, round_name),
    INDEX idx_submission (submission_id),
    INDEX idx_validated (validated)
);

-- Player alias mapping for improved OCR matching
CREATE TABLE player_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    alias_name TEXT NOT NULL,
    alias_type TEXT NOT NULL,  
    -- Types: 'ign', 'discord_name', 'nickname', 'common_ocr_error', 'manual'
    
    priority INTEGER DEFAULT 1,        -- Higher priority checked first
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,                   -- Who added this alias
    
    UNIQUE(player_id, alias_name),
    INDEX idx_player (player_id),
    INDEX idx_alias (alias_name),
    INDEX idx_priority (priority)
);

-- Processing batch tracking
CREATE TABLE processing_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    tournament_id TEXT NOT NULL,
    round_name TEXT,                   -- May not be known at batch start
    
    batch_size INTEGER NOT NULL,
    completed_count INTEGER DEFAULT 0,
    validated_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    status TEXT NOT NULL DEFAULT 'processing',  
    -- Status: processing, completed, partial_error, failed
    
    average_confidence FLOAT,
    
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    INDEX idx_tournament_round (tournament_id, round_name),
    INDEX idx_status (status),
    INDEX idx_guild (guild_id)
);

-- OCR learning data (for future improvements)
CREATE TABLE ocr_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER REFERENCES placement_submissions(id),
    
    original_text TEXT NOT NULL,       -- What OCR extracted
    corrected_text TEXT NOT NULL,      -- What it should have been
    correction_type TEXT NOT NULL,     -- player_name, placement, etc.
    
    corrected_by_discord_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_submission (submission_id),
    INDEX idx_original (original_text),
    INDEX idx_corrected (corrected_text)
);
```

---

## Batch Processing Flow

```
1. Screenshots posted in Discord (potentially multiple within seconds)
   ↓
2. Monitor detects images, starts 30-second batch window
   ↓
3. Collect all images posted in window, create processing_batches record
   ↓
4. Send notification to staff: "Processing 4 screenshots for Round X..."
   ↓
5. Process images in parallel (max 4 concurrent):
   
   For each image (async):
   ├─ 5a. Download image to temp storage
   ├─ 5b. Run template classifier
   │   ├─ If score < 95%: Skip, log as non-standings image
   │   └─ If score >= 95%: Continue
   ├─ 5c. Run 3-pass preprocessing + ensemble OCR:
   │   ├─ Pass 1: High-contrast → Tesseract + EasyOCR
   │   ├─ Pass 2: Sharp edges → Tesseract + EasyOCR
   │   ├─ Pass 3: Inverted → Tesseract + EasyOCR
   │   └─ Generate consensus from all results
   ├─ 5d. Extract structured data:
   │   ├─ Detect lobby number (from screenshot or message)
   │   ├─ Extract player names (8 expected)
   │   ├─ Extract placements (1-8)
   │   └─ Pair names with placements
   ├─ 5e. Match players to roster:
   │   ├─ Try exact match
   │   ├─ Try alias match
   │   ├─ Try fuzzy match (95% threshold)
   │   └─ Flag unmatched for review
   ├─ 5f. Run structural validation
   ├─ 5g. Calculate multi-dimensional confidence
   └─ 5h. Store placement_submissions record
   
   ↓
6. Wait for all images in batch to complete
   ↓
7. Cross-lobby validation (if multiple lobbies detected):
   ├─ Check no player in multiple lobbies
   ├─ Verify expected lobby count
   └─ Flag any issues
   ↓
8. Calculate batch average confidence
   ↓
9. For high-confidence submissions (>=98% AND no validation issues):
   ├─ Auto-create round_placements records
   ├─ Mark submission as validated
   ├─ Set validation_method='auto'
   └─ Skip manual review
   ↓
10. For medium/low confidence submissions (<98% OR validation issues):
    ├─ Send notification to staff channel:
    │   "Round X results ready for review (3/4 high confidence, 1 needs review)"
    ├─ Include link to validation dashboard
    └─ Highlight specific concerns per submission
    ↓
11. Staff reviews flagged submissions:
    ├─ Open manual editing interface
    ├─ View screenshot side-by-side with extracted data
    ├─ Correct any errors
    ├─ Approve or reject
    └─ System creates round_placements records
    ↓
12. Once all lobbies for round are validated:
    ├─ Trigger StandingsAggregator.refresh_scoreboard()
    ├─ Set source='screenshot'
    └─ Calculate cumulative points
    ↓
13. Update scoreboard_snapshots table
    ↓
14. Broadcast WebSocket update to dashboard clients
    ↓
15. Dashboard displays updated live standings
    ↓
16. Send confirmation to staff channel: "✅ Round X standings updated"
```

---

## Configuration

**config.yaml additions**:
```yaml
standings_screenshots:
  enabled: true
  
  # Channel monitoring
  monitor_channels:
    - "tournament-standings"
    - "lobby-results"
  
  # Staff notifications
  staff_notification_channel: "bot-admin"
  notify_on_detection: true
  notify_on_completion: true
  notify_on_validation_needed: true
  
  # Batch processing
  batch_window_seconds: 30          # Collect screenshots within 30s window
  max_concurrent_processing: 4      # Process up to 4 images simultaneously
  
  # Accuracy settings
  template_match_threshold: 0.95    # 95% template match required
  auto_validate_threshold: 0.98     # 98% overall confidence for auto-validation
  ocr_consensus_threshold: 0.90     # OCR engines must agree 90%+
  player_match_threshold: 0.95      # 95% fuzzy match threshold
  
  # OCR engines (enable multiple for ensemble)
  ocr_engines:
    tesseract:
      enabled: true
      config: '--psm 6 --oem 3'      # Page segmentation mode 6, OCR Engine Mode 3
    easyocr:
      enabled: true
      languages: ['en']
      gpu: false                      # Set true if GPU available
  
  # Preprocessing
  preprocessing_passes: 3           # Multiple preprocessing attempts
  roi_detection: true               # Auto-detect text regions
  layout_analysis: true             # Analyze grid structure
  
  # Validation
  expected_lobbies: 4               # Number of lobbies per round
  players_per_lobby: 8
  strict_validation: true           # Require all validation checks
  allow_substitutes: false          # Allow players not in original roster
  
  # Manual editing
  manual_review_ui_enabled: true
  validation_dashboard_url: "/admin/placements"
  
  # Performance
  image_cache_ttl_seconds: 3600     # Keep images cached for 1 hour
  cleanup_processed_images: true    # Delete images after processing
```

**.env additions**:
```bash
# Tesseract OCR binary path (system-specific)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Screenshot processing
STANDINGS_MONITOR_ENABLED=true
STANDINGS_AUTO_VALIDATE=true
STANDINGS_CONFIDENCE_THRESHOLD=0.98

# Storage
SCREENSHOT_TEMP_DIR=./temp/screenshots
SCREENSHOT_CACHE_DIR=./cache/screenshots
```

---

## API Endpoints

### New Endpoints:

**Processing**:
- `POST /api/v1/placements/process-screenshot` - Manually trigger screenshot processing
  - Body: `{ "image_url": string, "round_name"?: string, "lobby_number"?: int }`
- `POST /api/v1/placements/batch-process` - Process multiple screenshots
  - Body: `{ "image_urls": string[], "round_name"?: string }`
- `POST /api/v1/placements/reprocess/{submission_id}` - Retry failed submission

**Viewing**:
- `GET /api/v1/placements/submissions` - List all submissions
  - Query params: `status`, `tournament_id`, `round_name`, `confidence_min`
- `GET /api/v1/placements/submissions/{id}` - Get detailed submission
- `GET /api/v1/placements/rounds/{tournament_id}/{round_name}` - Get placements for round
- `GET /api/v1/placements/batches` - List processing batches
- `GET /api/v1/placements/batches/{id}` - Get batch details

**Validation/Editing**:
- `GET /api/v1/placements/pending` - Get submissions needing review
- `POST /api/v1/placements/validate/{submission_id}` - Validate submission
  - Body: `{ "approved": bool, "edited_placements"?: array, "notes"?: string }`
- `PUT /api/v1/placements/edit/{submission_id}` - Update extracted data
  - Body: `{ "placements": [{ "player_id": string, "placement": int }] }`
- `POST /api/v1/placements/reject/{submission_id}` - Reject submission
  - Body: `{ "reason": string }`

**Scoreboard Integration**:
- `POST /api/v1/placements/refresh-scoreboard` - Recalculate scoreboard from validated placements
  - Body: `{ "tournament_id": string, "round_name"?: string }`
- `GET /api/v1/placements/confidence-report` - Accuracy metrics

**Player Aliases**:
- `GET /api/v1/placements/aliases/{player_id}` - Get aliases for player
- `POST /api/v1/placements/aliases` - Add new alias
  - Body: `{ "player_id": string, "alias_name": string, "alias_type": string }`
- `DELETE /api/v1/placements/aliases/{alias_id}` - Remove alias

---

## Manual Editing Interface

**Dashboard Route**: `/admin/placements/review`

### Main Review Dashboard:

**Pending Queue View**:
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Placement Submissions - Review Queue                     │
├─────────────────────────────────────────────────────────────┤
│ Round 1 - Batch #42 (4 submissions) - Avg Confidence: 96%  │
│                                                              │
│ ✅ Lobby 1 - Confidence: 99% - Auto-validated              │
│ ✅ Lobby 2 - Confidence: 98% - Auto-validated              │
│ 🟡 Lobby 3 - Confidence: 92% - [Review] [Edit]            │
│ 🔴 Lobby 4 - Confidence: 87% - [Review] [Edit]            │
│                                                              │
│ [Review All] [Approve Batch] [Export Data]                 │
└─────────────────────────────────────────────────────────────┘
```

### Individual Submission Edit View:

**Layout**:
```
┌────────────────────────────┬──────────────────────────────┐
│  Screenshot (Zoomable)     │  Extracted Data              │
│                            │                              │
│  [Full screenshot image]   │  Round: Round 1              │
│                            │  Lobby: 3                    │
│  [Zoom In] [Zoom Out]      │  Confidence: 92%             │
│  [Reset]                   │                              │
│                            │  Players & Placements:       │
│                            │  ┌──────────────────────┐   │
│                            │  │ Rank │ Player  │ Conf│   │
│                            │  ├──────┼─────────┼─────┤   │
│                            │  │ 1st  │ Player1 │ 99% │✅ │
│                            │  │ 2nd  │ Plyaer2 │ 85% │🟡 │ ← Edit
│                            │  │ 3rd  │ Player3 │ 98% │✅ │
│                            │  │ 4th  │ Player4 │ 97% │✅ │
│                            │  │ 5th  │ Player5 │ 96% │✅ │
│                            │  │ 6th  │ Player6 │ 99% │✅ │
│                            │  │ 7th  │ Player7 │ 94% │✅ │
│                            │  │ 8th  │ Player8 │ 98% │✅ │
│                            │  └──────────────────────┘   │
│                            │                              │
│                            │  Issues Found:               │
│                            │  • "Plyaer2" - possible typo │
│                            │    Did you mean "Player2"?   │
│                            │                              │
│                            │  [Quick Fix]                 │
│                            │                              │
│                            │  [✅ Approve] [✏️ Edit]      │
│                            │  [❌ Reject] [🔄 Reprocess]  │
└────────────────────────────┴──────────────────────────────┘
```

**Edit Mode**:
- Click any player name → Dropdown with roster + fuzzy search
- Click any placement → Dropdown 1-8
- Drag-and-drop rows to reorder
- "Quick Fix" button auto-applies suggested corrections
- Real-time validation (shows errors if invalid state)

### Batch Review Mode:

**View all lobbies side-by-side**:
```
┌────────────────────────────────────────────────────────────┐
│ Round 1 - All Lobbies                                      │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ Lobby 1 ✅   │ Lobby 2 ✅   │ Lobby 3 🟡   │ Lobby 4 🔴   │
│ [Thumbnail]  │ [Thumbnail]  │ [Thumbnail]  │ [Thumbnail]  │
│ Conf: 99%    │ Conf: 98%    │ Conf: 92%    │ Conf: 87%    │
│              │              │              │              │
│ 1. Player1   │ 1. Player9   │ 1. Player17  │ 1. Player25  │
│ 2. Player2   │ 2. Player10  │ 2. Player18  │ 2. ???       │
│ ...          │ ...          │ ...          │ ...          │
│              │              │              │              │
│ [Expand]     │ [Expand]     │ [Edit]       │ [Edit]       │
└──────────────┴──────────────┴──────────────┴──────────────┘
│                                                              │
│ [Approve All High Confidence] [Review Flagged Only]         │
└──────────────────────────────────────────────────────────────┘
```

---

## Dependencies

**requirements.txt additions**:
```txt
# OCR engines
pytesseract>=0.3.10
easyocr>=1.7.1

# Image processing
opencv-python>=4.9.0
opencv-contrib-python>=4.9.0  # Advanced features (EAST detector, etc.)
Pillow>=10.2.0
scikit-image>=0.22.0
imutils>=0.5.4

# Numeric/scientific
numpy>=1.26.0
scipy>=1.12.0

# Already in requirements (using existing):
# rapidfuzz>=3.14  - for fuzzy matching
# aiohttp>=3.12    - for async image downloads
```

**System Requirements**:
- **Tesseract OCR**: Must be installed separately
  - **Windows**: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
    - Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - **Linux**: `sudo apt-get install tesseract-ocr`
  - **macOS**: `brew install tesseract`
  
- **EasyOCR**: Auto-downloads models on first run (~500MB)
  - English model: `en.pth` and `craft_mlt_25k.pth`
  - Models cached in `~/.EasyOCR/model/`

---

## Installation & Setup

### Step 1: Install Tesseract OCR
```bash
# Windows: Download and run installer
# https://github.com/UB-Mannheim/tesseract/wiki

# Verify installation
tesseract --version
```

### Step 2: Install Python Dependencies
```bash
# From project root
python -m pip install pytesseract easyocr opencv-python opencv-contrib-python scikit-image imutils
```

### Step 3: Configure Environment
```bash
# Add to .env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
STANDINGS_MONITOR_ENABLED=true
```

### Step 4: Run Database Migration
```bash
# Create migration for new tables
alembic revision -m "add_placement_tables"
# Edit migration file with SQL from schema section above
alembic upgrade head
```

### Step 5: Update Config
```yaml
# Add to config.yaml (see Configuration section above)
standings_screenshots:
  enabled: true
  monitor_channels:
    - "tournament-standings"
  # ... rest of config
```

### Step 6: Build Player Alias Database
```python
# Import existing player data from tournament registration
# Run one-time script to populate player_aliases table
python scripts/import_player_aliases.py
```

---

## Accuracy Enhancement Techniques

### 1. **Template Library Management**
**Location**: `assets/templates/tft_standings/`

- Store reference screenshots of TFT standings UI
- Variants to include:
  - Different resolutions (1080p, 1440p, 4K)
  - Light mode vs dark mode
  - Different TFT sets (UI changes each set/season)
  - Different game modes (Normal, Hyper Roll, Double Up)
- Update library at start of each TFT season
- Allow staff to upload "known good" templates

### 2. **Player Alias Database Building**

**Automatic Population**:
```python
# On tournament registration, automatically add aliases:
- Discord username → player_aliases (type='discord_name')
- Riot IGN → player_aliases (type='ign')
- Any known nicknames → player_aliases (type='nickname')
```

**Learning from Corrections**:
```python
# When staff manually corrects OCR error:
# If "Plyaer2" was corrected to "Player2":
INSERT INTO player_aliases (player_id, alias_name, alias_type)
VALUES ('player2_id', 'Plyaer2', 'common_ocr_error')

# Future OCR instances of "Plyaer2" will auto-match to "Player2"
```

**Manual Management**:
- Staff can add/remove aliases via admin panel
- Bulk import from CSV
- Priority system (check high-priority aliases first)

### 3. **Confidence Calibration Over Time**

**Tracking**:
```sql
-- Track prediction accuracy
CREATE TABLE confidence_calibration (
    id INTEGER PRIMARY KEY,
    predicted_confidence FLOAT,
    actual_correct BOOLEAN,
    submission_id INTEGER REFERENCES placement_submissions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analyze: Are 98% confidence submissions actually 98% accurate?
SELECT 
    ROUND(predicted_confidence * 10) / 10 AS confidence_bucket,
    AVG(CASE WHEN actual_correct THEN 1.0 ELSE 0.0 END) AS actual_accuracy,
    COUNT(*) AS sample_size
FROM confidence_calibration
GROUP BY confidence_bucket;
```

**Adjustment**:
- If 98% confidence submissions are only 95% accurate → raise threshold to 99%
- If 95% confidence submissions are 98% accurate → lower threshold to 96%
- Continuously adjust weight factors in confidence calculation

### 4. **Error Pattern Learning**

**Common OCR Errors**:
```python
# Track common character confusions
CHARACTER_CONFUSION_MATRIX = {
    '1': ['l', 'I', '|'],
    'l': ['1', 'I', '|'],
    'I': ['1', 'l', '|'],
    '0': ['O', 'o'],
    'O': ['0', 'o'],
    '5': ['S', 's'],
    'S': ['5', 's'],
    '8': ['B'],
    'B': ['8'],
    'rn': ['m'],  # Common: "rn" read as "m"
    'm': ['rn'],
}

# When fuzzy matching, prioritize matches that differ only by confused characters
```

**Store Corrections**:
```python
# Every manual correction is stored in ocr_corrections table
# Periodically analyze to find patterns:
# - Which player names are consistently misread?
# - Which characters cause problems?
# - Does preprocessing method affect certain text?

# Use this data to:
# - Add pre-correction rules
# - Improve fuzzy matching
# - Suggest OCR configuration changes
```

### 5. **Multi-Round Context Validation**

**Player Consistency Checks**:
```python
# Validate new round against previous rounds:
- Same set of players across all rounds (unless substitutions)
- Players stay in same lobby throughout tournament
- Unusual patterns flagged (e.g., player suddenly appears in Round 3)

# If Round 3 extraction shows player not in Rounds 1-2:
→ Flag for review (possible OCR error or late addition)

# If lobby assignments change:
→ Flag for review (lobbies typically fixed for tournament)
```

**Expected Progression**:
```python
# Track cumulative points, flag anomalies:
- Player gained 8 points (1st place) but their name wasn't in lobby → likely error
- Player's total points don't match sum of round points → calculation error

# Use previous rounds to validate current round extractions
```

---

## Performance Optimization

### Processing Speed (per screenshot):
- **Classification**: 1-2 seconds
- **Preprocessing (3 passes)**: 3-4 seconds
- **OCR (Tesseract + EasyOCR, 3 passes each)**: 8-12 seconds
- **Player matching**: <1 second
- **Validation**: <1 second
- **Storage**: <1 second

**Total per screenshot**: 13-20 seconds (thorough, accurate processing)

### Batch Processing (4 screenshots):
- **Parallel processing**: 15-25 seconds total (not 60-80 seconds!)
- **Sequential fallback**: 52-80 seconds (if parallel fails)

### Optimizations:
- **Parallel async processing** of multiple images
- **OCR model caching** (keep models loaded in memory)
- **Image preprocessing caching** (if same image reprocessed)
- **Player roster caching** (load once per tournament)
- **Template pre-loading** (load all templates at bot startup)

---

## Success Metrics & Monitoring

### Target Metrics:
- **Extraction Accuracy**: ≥99% correct player/placement extraction
- **Auto-validation Rate**: ≥85% submissions auto-validated (high confidence)
- **False Positive Rate**: <1% (incorrect auto-validations)
- **Processing Time**: <20s per screenshot, <30s for 4-image batch
- **Manual Review Time**: <2 minutes per flagged submission

### Monitoring Dashboard:
**Location**: `/admin/placements/metrics`

**Display**:
- Real-time confidence score distribution (histogram)
- Auto-validation rate (daily, weekly trends)
- Average processing time
- Queue depth (pending reviews)
- Accuracy by OCR engine
- Most common corrections (to improve system)
- Per-player extraction success rate
- Confidence calibration accuracy

### Alerts:
- ⚠️ If average confidence drops below 90% → Alert admin
- ⚠️ If processing queue > 10 submissions → Alert staff
- ⚠️ If batch processing fails repeatedly → Alert developer
- ⚠️ If auto-validation rate drops below 70% → Investigate thresholds
- ⚠️ If false positive rate exceeds 2% → Raise thresholds

---

## Testing Strategy

### Unit Tests:
```python
# tests/test_screenshot_classifier.py
- Test template matching with known good screenshots
- Test false positive rejection (non-standings images)
- Test different resolutions and aspect ratios

# tests/test_ocr_pipeline.py
- Test each preprocessing pass
- Test OCR consensus algorithm
- Test with synthetic "perfect" screenshots
- Test with degraded quality screenshots

# tests/test_player_matcher.py
- Test exact matching
- Test alias matching
- Test fuzzy matching with various edit distances
- Test common OCR error handling

# tests/test_placement_validator.py
- Test structural validation rules
- Test cross-lobby validation
- Test duplicate detection
```

### Integration Tests:
```python
# tests/integration/test_end_to_end.py
- Full pipeline test with sample screenshots
- Batch processing test
- Manual editing workflow test
- Scoreboard refresh test
```

### Manual Testing:
- **Pre-launch**: Test with 50+ real tournament screenshots
- **Pilot program**: Use in parallel with manual entry for 1 tournament
- **Compare**: Screenshot extraction vs manual entry, measure accuracy
- **Iterate**: Fix issues, retrain, adjust thresholds

---

## Rollout Plan

### Phase 1: Core Infrastructure (Week 1)
- ✅ Database schema & migrations
- ✅ Basic screenshot monitor (detect & download)
- ✅ Placement storage service
- ✅ API endpoints (basic)

### Phase 2: Classification & Preprocessing (Week 2)
- ✅ Template matcher implementation
- ✅ 3-pass preprocessing pipeline
- ✅ ROI detection
- ✅ Build template library (collect reference screenshots)

### Phase 3: OCR Pipeline (Week 2-3)
- ✅ Tesseract integration
- ✅ EasyOCR integration
- ✅ Consensus algorithm
- ✅ Structured data extraction (names, placements)

### Phase 4: Validation & Matching (Week 3)
- ✅ Player matching engine (exact, alias, fuzzy)
- ✅ Structural validator
- ✅ Multi-dimensional confidence scoring
- ✅ Cross-lobby validation

### Phase 5: Batch Processing (Week 3-4)
- ✅ Async batch queue
- ✅ Parallel processing
- ✅ Batch tracking & status
- ✅ Error isolation & retry logic

### Phase 6: Manual Editing UI (Week 4-5)
- ✅ Dashboard review queue
- ✅ Side-by-side editor
- ✅ Player dropdown with fuzzy search
- ✅ Quick fix suggestions
- ✅ Batch review mode

### Phase 7: Player Alias System (Week 5)
- ✅ Alias database schema
- ✅ Import from tournament registration
- ✅ Learning from manual corrections
- ✅ Manual alias management UI

### Phase 8: Scoreboard Integration (Week 5-6)
- ✅ Update StandingsAggregator for screenshot source
- ✅ Scoreboard refresh API
- ✅ WebSocket notifications
- ✅ Dashboard live updates

### Phase 9: Testing & Calibration (Week 6-7)
- ✅ Unit tests for all components
- ✅ Integration tests
- ✅ Test with real tournament screenshots
- ✅ Calibrate confidence thresholds
- ✅ Performance optimization
- ✅ Build player alias database from historical data

### Phase 10: Pilot Deployment (Week 7)
- ✅ Deploy to test server
- ✅ Run in parallel with manual entry for one tournament
- ✅ Measure accuracy, processing time, user feedback
- ✅ Identify and fix issues
- ✅ Refine thresholds and UI

### Phase 11: Production Launch (Week 8)
- ✅ Deploy to production
- ✅ Enable for live tournament
- ✅ Monitor closely
- ✅ Staff on standby for manual corrections
- ✅ Collect metrics
- ✅ Iterate based on real-world usage

---

## Operational Procedures

### Before Tournament:
1. **Test channel monitoring**: Post test screenshot, verify detection
2. **Pre-load player roster**: Ensure all registered players in database
3. **Build alias database**: Import IGNs from registration
4. **Brief staff**: Train on manual review interface
5. **Set up monitoring**: Enable alerts, check dashboard access

### During Tournament:
1. **Monitor notifications**: Watch for screenshot detection alerts
2. **Review flagged submissions**: Prioritize low-confidence extractions
3. **Quick validation**: Use batch review for high-confidence rounds
4. **Real-time corrections**: Fix errors immediately via edit interface
5. **Scoreboard checks**: Verify standings update correctly after each round

### After Tournament:
1. **Accuracy audit**: Compare screenshot data vs final standings
2. **Review corrections**: Analyze what was manually changed
3. **Update aliases**: Add any new OCR error patterns discovered
4. **Generate report**: Accuracy metrics, processing times, issues
5. **Feedback loop**: Identify improvements for next tournament

---

## Fallback & Safety Mechanisms

### Multiple Safety Layers:

**1. Auto-validation Only for High Confidence**:
- Only ≥98% confidence auto-validates
- Anything uncertain requires human review
- Better to over-flag than auto-approve errors

**2. Structural Validation**:
- Even high-confidence submissions must pass all validation rules
- Invalid structures always flagged (even if OCR confident)

**3. Manual Override Always Available**:
- Staff can reject any auto-validated submission
- Easy rollback if error discovered later

**4. Audit Trail**:
- Complete history of all submissions, validations, edits
- Can trace any standing back to original screenshot
- Support dispute resolution

**5. Dual-Source Option**:
- Can still manually enter data if screenshot fails
- Screenshot extraction is primary, manual entry is fallback
- Both stored, compared for validation

**6. Easy Disable**:
- Single config flag to disable automated processing
- Fall back to manual entry only if system has issues

### Error Recovery:

**OCR Failure**:
- Retry with different preprocessing
- Try alternate OCR engine
- Manual entry as last resort

**Invalid Screenshot**:
- Notify user to repost with better quality
- Provide guidance on screenshot requirements

**Missing Player**:
- Alert staff immediately
- Check if substitute or typo
- Add to roster if legitimate

**System Overload**:
- Queue processing, process when capacity available
- Alert staff if queue backs up
- Prioritize current round over historical data

---

## Future Enhancements (Post-Launch)

### Phase 2 (Future):
1. **Custom ML Model**: Train convolutional neural network specifically on TFT screenshots
2. **Active Learning**: System learns from corrections, improves over time
3. **Mobile Screenshot Support**: Handle phone screenshots (cropped, varied aspect ratios)
4. **Video Processing**: Extract from Twitch VODs or live stream
5. **Multi-game Support**: Extend to other esports games
6. **Automated Round Detection**: Auto-detect round number from screenshot
7. **Lobby Auto-detection**: Identify lobby number from screenshot UI
8. **Real-time Streaming Mode**: Process screenshots as tournament happens
9. **Confidence Prediction**: Predict confidence before processing (save resources)
10. **Integration with Tournament Platform APIs**: Pull roster data automatically

---

## Documentation Requirements

**Staff Training Docs**:
- How to post screenshots for automated processing
- How to use manual review interface
- Common issues and how to fix them
- When to use manual entry vs screenshot

**Technical Docs**:
- Architecture overview
- API reference
- Database schema
- Deployment guide
- Troubleshooting guide

**User Docs**:
- Screenshot requirements (resolution, format, clarity)
- What to do if screenshot rejected
- How to verify standings are correct

---

## Summary

This spec provides a **production-ready, screenshot-only standings extraction system** that achieves 99%+ accuracy through:

1. **Multi-stage validation**: Template matching, ensemble OCR, structural validation
2. **Intelligent player matching**: Exact, alias, and fuzzy matching with learning
3. **Batch processing**: Efficient parallel processing of multiple screenshots
4. **Comprehensive manual editing**: Easy-to-use interface for corrections
5. **Confidence scoring**: Multi-dimensional scoring ensures only high-quality auto-validations
6. **Audit trail**: Complete tracking of all submissions and changes
7. **Safety mechanisms**: Multiple fallback layers prevent incorrect data

**No Riot API dependency** - system is fully self-contained and reliable. Manual editing interface ensures 100% accuracy when needed, while automation handles the majority of cases.