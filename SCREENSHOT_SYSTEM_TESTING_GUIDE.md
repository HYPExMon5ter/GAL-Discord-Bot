# Screenshot Extraction System - Testing Guide

Complete guide for testing screenshot-based standings extraction system.

## Prerequisites

- Python 3.12+
- Tesseract OCR installed
- Discord Bot running

## Quick Start

### 1. Run Test Suite
```bash
python scripts/test_screenshot_system.py
```

### 2. Start API
```bash
python -m api.main
```

### 3. Check API Docs
http://localhost:8000/docs

## Testing Method 1: API Upload

### Upload Screenshot
```bash
curl -X POST http://localhost:8000/api/v1/placements/process-screenshot   -H "Content-Type: application/json"   -d '{
    "image_url": "https://example.com/tft.png",
    "round_name": "ROUND_1",
    "lobby_number": 1
  }'
```

### Check Result
```bash
curl http://localhost:8000/api/v1/placements/submissions/1
```

## Testing Method 2: Discord Channel

1. Create channel named "tournament-standings"
2. Post TFT screenshot
3. Watch for notifications

## Manual Editing

### Find Pending
```bash
curl "http://localhost:8000/api/v1/placements/submissions?status=pending"
```

### Approve
```bash
curl -X POST http://localhost:8000/api/v1/placements/validate/5   -d '{"approved": true}'
```

### Edit
```bash
curl -X POST http://localhost:8000/api/v1/placements/validate/5   -d '{"approved": true, "edited_placements": [...]}'
```

## Debugging

### Test Classification
```python
from integrations.screenshot_classifier import get_classifier
c = get_classifier()
valid, conf, meta = c.classify("url")
print(f"Valid: {valid}, Conf: {conf}")
```

### Test OCR
```python
from integrations.standings_ocr import get_ocr_pipeline
p = get_ocr_pipeline()
result = p.extract_from_image("url")
print(result["structured_data"])
```

### Test Player Matching
```python
from integrations.player_matcher import get_player_matcher
m = get_player_matcher()
r = m.match_player("TestPlayer")
print(r)
```

## Troubleshooting

### Not a TFT Screenshot
- Add templates to assets/templates/tft_standings/
- Lower threshold: template_match_threshold: 0.85

### Player Not Found
- Add player to roster
- Add aliases
- Lower threshold: player_match_threshold: 0.90

### OCR Failed
- Check Tesseract: tesseract --version
- Check EasyOCR: python -c "import easyocr"

---

**Version:** 1.0.0
**Status:** Production Ready
