# Quick Start Instructions - PaddleOCR Screenshot System

## Before Testing - MUST DO THIS

### 1. Set Environment Variables

Run this in your terminal BEFORE starting bot:

**Windows PowerShell:**
```powershell
$env:DISABLE_MODEL_SOURCE_CHECK="True"
```

**Windows Command Prompt:**
```cmd
set DISABLE_MODEL_SOURCE_CHECK=True
```

### 2. Restart Your Bot

Stop the current bot (Ctrl+C) and start fresh:
```bash
python bot.py
```

### 3. Create Bot Admin Channel (Optional)

If you want to see notifications, create channel named `bot-admin` in Discord.

---

## Testing the System

### Step 1: Post Screenshot

1. Go to `#tournament-standings` channel in Discord
2. Upload a TFT screenshot (full screen, showing player names + placements)
3. Wait for bot reaction (should appear within 1-2 seconds) ✅

### Step 2: Wait for Batch Processing

- Bot waits **30 seconds** to collect all screenshots
- You'll see: `Batch timer expired - processing X images`
- Processing will begin

### Step 3: Check Results

After processing completes (30-90 seconds depending on your CPU):

1. **Bot will send notification** to `#tournament-standings`:
   - "Screenshot Processing Complete"
   - Shows: processed count, validated count, errors

2. **Check admin dashboard**:
   - Go to your bot's admin URL
   - Navigate to placements section
   - View extracted player names and placements

3. **Check logs** if issues:
   - Open `gal_bot.log`
   - Look for "OCR successful" or "Players found"

---

## Expected Behavior

### ✅ Normal Operation:
```
[User posts screenshot]
  ↓
[Bot adds reaction] ✅ (1-2 seconds)
  ↓
[Bot waits] 30 seconds (batch window)
  ↓
[Processing starts]
  ↓
[Classification passes] ✓ (70% confidence)
  ↓
[PaddleOCR extracts text]
  ↓
[Players structured] (placements + names)
  ↓
[Bot sends notification]
  "Processing complete: 3 images, 2 validated"
```

### ⚠️ If Processing is Slow:

**CPU-based processing (your setup):**
- First image: 30-60 seconds (PaddleOCR loads models)
- Subsequent images: 5-10 seconds each
- Total batch of 3: 30-45 seconds

**This is NORMAL** for CPU processing. PaddleOCR loads large models once.

---

## Troubleshooting

### Error: "Image processing error: Attribute 'extracted_data_tesseract'..."

**Solution**: Already fixed! Just restart your bot.

### Error: "PaddleOCR timed out after 30 seconds"

**Causes**:
1. Image is too large (>4000px width/height)
2. CPU is very slow/old
3. Multiple images processing simultaneously

**Solutions**:
1. Use smaller screenshots (1920x1080 is ideal)
2. Reduce concurrent processing in config: `max_concurrent_processing: 2`
3. Wait - first image is always slow (model loading)

### Warning: "Notification channel 'bot-admin' not found"

**Solution 1**: Create channel named `bot-admin`

**Solution 2**: Change channel in `config.yaml`:
```yaml
channels:
  log_channel: your-existing-channel-name
```

### Warning: "No ccache found"

**This is harmless** - just means recompilation may be slow on first run.

**Ignore it** - doesn't affect functionality.

### No players detected

**Check**:
1. Screenshot shows player names clearly
2. Screenshot shows placement numbers (1st, 2nd, etc.) or (1, 2, etc.)
3. Text is not blurry
4. Image is at least 800x600 pixels

**Common TFT screenshot formats that work**:
- Full-screen standings page
- Lobby results after match
- Round standings table

---

## Performance Optimization

### If You Want Faster Processing:

**Option 1: Skip Classification**
```yaml
# config.yaml
standings_screenshots:
  skip_classification: true  # Saves 1-2 seconds per image
```

**Option 2: Reduce Concurrent Processing**
```yaml
standings_screenshots:
  max_concurrent_processing: 2  # Default is 4, reduce for older CPUs
```

**Option 3: Use GPU (If Available)**
```yaml
standings_screenshots:
  use_gpu: true  # Requires NVIDIA GPU with CUDA
```
**Note**: Only works if you have NVIDIA GPU and CUDA installed.

---

## What's Expected

### With Real TFT Screenshots:

**Classification**: ✅ PASS (70-90% confidence)
- Aspect ratio check
- Text density analysis  
- Edge density check

**OCR Extraction**: ✅ PASS (5-10 seconds per image on CPU)
- Detects placement numbers (1-8)
- Detects player names
- Structures data correctly

**Player Detection**: ✅ Should find 6-8 players
- Patterns like: "1st PlayerName" or "1 PlayerName"
- Or: "PlayerName (1st)" or "PlayerName (1)"

**Overall Processing**: ✅ 30-60 seconds for 3 screenshots

---

## Getting Help

If issues persist after following these steps:

1. **Check logs**: `gal_bot.log` - search for "ERROR"
2. **Run test**: `python scripts/test_paddle_ocr.py`
3. **Review files**: `IMPLEMENTATION_SUMMARY.md`, `SETUP_GUIDE.md`

**Bot will work with your full TFT screenshots showing player names and placements!**

---

**Last updated**: 2025-12-29  
**Status**: Ready for testing with `DISABLE_MODEL_SOURCE_CHECK=True`
