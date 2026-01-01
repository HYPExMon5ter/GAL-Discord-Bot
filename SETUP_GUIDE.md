# PaddleOCR Screenshot System - Setup Guide

## Environment Variables (Recommended)

Set these environment variables to improve performance and reduce warnings:

### Windows (PowerShell):
```powershell
$env:DISABLE_MODEL_SOURCE_CHECK="True"
$env:PYTHONIOENCODING="utf-8"
```

### Windows (Command Prompt):
```cmd
set DISABLE_MODEL_SOURCE_CHECK=True
set PYTHONIOENCODING=utf-8
```

### Linux/Mac:
```bash
export DISABLE_MODEL_SOURCE_CHECK=True
export PYTHONIOENCODING=utf-8
```

### Why These Are Needed:
1. **DISABLE_MODEL_SOURCE_CHECK** - Skips slow model connectivity checks (saves 5-10 seconds startup)
2. **PYTHONIOENCODING** - Fixes Unicode display issues in console

## Notification Channel Setup

You're seeing this warning:
```
Notification channel 'bot-admin' not found
```

### Solution: Create the channel

1. Go to your Discord server
2. Create a new channel named `bot-admin`
3. Make sure the bot has permission to see and post in it

### Or: Change the channel name

Edit `config.yaml`:
```yaml
standings_screenshots:
  staff_notification_channel: your-channel-name  # Change to existing channel
```

## Performance Tips

### If PaddleOCR is too slow:

1. **Disable ROI detection** (already done in latest config):
   ```yaml
   enable_roi_detection: false
   ```

2. **Skip classification for trusted channels**:
   ```yaml
   skip_classification: true
   ```

3. **Enable GPU if available** (requires NVIDIA GPU with CUDA):
   ```yaml
   use_gpu: true
   ```

4. **Reduce concurrent processing**:
   ```yaml
   max_concurrent_processing: 2  # Default is 4
   ```

### Expected Processing Times:

| Hardware | Speed per Image | 3 Images Batch |
|-----------|------------------|------------------|
| CPU (Modern) | 5-8 seconds | 15-24 seconds |
| CPU (Older) | 10-15 seconds | 30-45 seconds |
| GPU (CUDA) | 2-3 seconds | 6-9 seconds |

## Testing Checklist

- [ ] Set `DISABLE_MODEL_SOURCE_CHECK=True` environment variable
- [ ] Restart the Discord bot
- [ ] Post a TFT screenshot to `#tournament-standings`
- [ ] Watch for confirmation reaction (✅)
- [ ] Wait 30 seconds for batch processing
- [ ] Check notification channel for results
- [ ] Verify player names were extracted correctly
- [ ] Check admin dashboard for extracted placements

## Troubleshooting

### Images are still rejected:

**Symptom**: `Classification result: False (confidence: 0.XX)`

**Solution**: Lower threshold in config:
```yaml
classification_threshold: 0.40  # Try 0.40-0.50 range
```

**Or skip entirely**:
```yaml
skip_classification: true  # For trusted channels only
```

### Players not detected:

**Symptom**: `Players found: 0/8` or very few players

**Solutions**:
1. Check screenshot quality (min 800x600, clear text)
2. Verify the standings table is visible in image
3. Try with `enable_roi_detection: true` in config
4. Check logs for parsing errors

### Processing hangs/times out:

**Symptom**: OCR takes >30 seconds per image

**Solutions**:
1. **Set environment variable**: `DISABLE_MODEL_SOURCE_CHECK=True`
2. **Disable ROI**: `enable_roi_detection: false`
3. **Reduce concurrency**: `max_concurrent_processing: 2`
4. **Check image size**: Very large images (>4000px) take longer

### Database errors:

**Symptom**: `Attribute 'extracted_data_tesseract' does not accept objects of type <class 'list'>`

**Solution**: ✅ **Already fixed** in latest code
- Ensure you've restarted the bot after updates
- Pull latest changes from repository

## Understanding the System

### How It Works:

```
1. User posts screenshot to Discord
   ↓
2. Bot detects image in monitored channel
   ↓
3. Bot adds reaction emoji ✓ (confirmation)
   ↓
4. Bot waits 30 seconds (batch window)
   ↓
5. Bot processes all screenshots in batch:
   - Classifies image (valid TFT screenshot?)
   - Extracts text using PaddleOCR
   - Structures data (placements + player names)
   - Matches players to roster
   - Validates data
   - Auto-approves if confidence is high (85%+)
   ↓
6. Bot sends notification with results:
   - Images processed
   - Auto-validated count
   - Errors
   - Average confidence
```

### Data Flow:

```
Discord Screenshot
  → Image downloaded
  → Classification (70%+ confidence)
  → PaddleOCR extraction
  → Structured parsing (placements + names)
  → Player matching (roster lookup)
  → Validation (8 players, 1-8 placements, no duplicates)
  → Database storage (if validated)
```

## File Locations

### Configuration:
- `config.yaml` - Main bot settings

### Code:
- `integrations/screenshot_classifier.py` - Image classification
- `integrations/paddle_ocr_engine.py` - OCR extraction
- `integrations/batch_processor.py` - Pipeline orchestration
- `core/events/handlers/screenshot_monitor.py` - Discord event handler

### Database:
- `dashboard/dashboard.db` - SQLite database
  - `placement_submissions` table - Raw OCR results
  - `round_placements` table - Validated placements

### Logs:
- `gal_bot.log` - Main bot log file

## Support

If you continue to have issues:

1. Check the log file: `gal_bot.log`
2. Run the test script: `python scripts/test_paddle_ocr.py`
3. Review this guide
4. Check config.yaml settings

**Environment info for bug reports**:
- OS: Windows/Linux/Mac
- Python version: 3.12+
- PaddleOCR version: latest
- GPU: available/not available
- Environment variables: DISABLE_MODEL_SOURCE_CHECK=True

---

Last updated: 2025-12-29
