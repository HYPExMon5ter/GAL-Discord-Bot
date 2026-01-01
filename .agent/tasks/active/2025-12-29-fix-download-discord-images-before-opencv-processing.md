## Fix: Download Discord Images Before OpenCV Processing

### Problem
OpenCV's `cv2.imread()` cannot read HTTP/HTTPS URLs directly. When Discord screenshots are passed as URLs to `screenshot_classifier.py` and `standings_ocr.py`, they fail with:
```
cv::findDecoder imread_('https://cdn.discordapp.com/...'): can't open/read file
```

### Root Cause
In `batch_processor.py`, `_process_single_image()` method passes Discord URLs directly:
```python
classifier.classify(image_data["url"])  # ❌ cv2 can't read URLs
ocr_pipeline.extract_from_image(image_data["url"])  # ❌ cv2 can't read URLs
```

### Solution
1. **Add image download utility** in `batch_processor.py`
   - Download Discord attachment URLs to temporary files
   - Use `requests` with timeout
   - Save to temp directory with unique filenames

2. **Modify `_process_single_image()` method**
   - Download image first before processing
   - Pass local file path to classifier and OCR
   - Clean up temp files after processing

3. **Error handling**
   - Handle download failures gracefully
   - Log errors with Discord message ID for tracking
   - Return proper error response to batch processor

### Files to Modify
- `integrations/batch_processor.py` - Add download logic to `_process_single_image()`

### Expected Outcome
- ✅ Discord images downloaded successfully
- ✅ OpenCV reads local files without errors
- ✅ Template matching and OCR work correctly
- ✅ Screenshots processed and appear on dashboard
- ✅ Temp files cleaned up after processing

### Time Estimate
~10 minutes (code changes + testing)