"""Test OCR directly on screenshots in dashboard/screenshots."""
import cv2
import numpy as np
import os
import sys
import logging
from typing import Dict, List

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from integrations.standings_ocr import OCRRipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# Placement points mapping
PLACEMENT_POINTS = {
    1: 8, 2: 7, 3: 6, 4: 5,
    5: 4, 6: 3, 7: 2, 8: 1
}

def test_single_screenshot(image_path: str, ocr_pipeline: OCRRipeline):
    """Test OCR on single screenshot with detailed logging."""
    log.info("=" * 70)
    log.info(f"TESTING: {os.path.basename(image_path)}")
    log.info("=" * 70)

    # Read image
    img = cv2.imread(image_path)
    if img is None:
        log.error(f"Failed to read image: {image_path}")
        return

    height, width = img.shape[:2]
    log.info(f"Image size: {width}x{height}")

    # Run OCR
    try:
        result = ocr_pipeline.extract_from_image(image_path)

        # Check results
        structured = result.get("structured_data", {})
        players = structured.get("players", [])

        log.info(f"\nPlayers extracted: {len(players)}")
        log.info("-" * 70)
        for player in players:
            log.info(f"  Place {player['placement']:2d}: {player['name']:<20} ({player['points']} pts)")

        log.info("-" * 70)

        if len(players) >= 6:
            log.info("✅ SUCCESS: Extracted 6+ players!")
        elif len(players) >= 4:
            log.info("⚠️  PARTIAL: Extracted 4-5 players (should be 8)")
        else:
            log.error("❌ FAILED: Extracted less than 4 players!")

    except Exception as e:
        log.error(f"Error processing {image_path}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test all screenshots in dashboard/screenshots."""
    screenshots_dir = os.path.join('dashboard', 'screenshots')

    if not os.path.exists(screenshots_dir):
        log.error(f"Screenshots directory not found: {screenshots_dir}")
        return

    # Find all screenshot files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp']
    screenshot_files = [
        f for f in os.listdir(screenshots_dir)
        if os.path.splitext(f)[1].lower() in image_extensions
    ]

    if not screenshot_files:
        log.error(f"No screenshot files found in {screenshots_dir}")
        return

    log.info(f"Found {len(screenshot_files)} screenshot(s) to test")

    # Initialize OCR pipeline
    try:
        ocr_pipeline = OCRRipeline()
        log.info("OCR Pipeline initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize OCR pipeline: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test each screenshot
    for filename in sorted(screenshot_files)[:5]:  # Test first 5
        image_path = os.path.join(screenshots_dir, filename)
        test_single_screenshot(image_path, ocr_pipeline)

    log.info("=" * 70)
    log.info("TESTING COMPLETE")
    log.info("=" * 70)

if __name__ == "__main__":
    main()
