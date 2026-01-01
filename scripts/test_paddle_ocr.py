"""
Quick test script for new PaddleOCR-based screenshot processing system.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Unicode encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_classifier():
    """Test simplified classifier."""
    print("="*60)
    print("Testing Simplified Classifier")
    print("="*60)
    
    from integrations.screenshot_classifier import get_classifier
    
    classifier = get_classifier()
    print(f"✓ Classifier initialized")
    print(f"  - Threshold: {classifier.threshold}")
    print(f"  - Skip classification: {classifier.skip_classification}")
    print(f"  - Trusted channels: {classifier.trusted_channels}")
    print()


def test_paddle_ocr():
    """Test PaddleOCR engine."""
    print("="*60)
    print("Testing PaddleOCR Engine")
    print("="*60)
    
    from integrations.paddle_ocr_engine import get_paddle_ocr
    
    try:
        ocr_engine = get_paddle_ocr()
        print(f"✓ PaddleOCR engine initialized")
        print(f"  - GPU enabled: {ocr_engine.use_gpu}")
        print(f"  - ROI detection: {ocr_engine.enable_roi}")
        print()
        
        # Test if PaddleOCR loads properly
        print("Loading PaddleOCR instance (this may take a moment)...")
        ocr_instance = ocr_engine._get_ocr_instance()
        print("✓ PaddleOCR loaded successfully!")
        print()
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize PaddleOCR: {e}")
        print()
        return False


def test_with_sample_image(image_path):
    """Test full pipeline with a sample image."""
    print("="*60)
    print("Testing Full Pipeline with Sample Image")
    print("="*60)
    
    if not os.path.exists(image_path):
        print(f"✗ Image not found: {image_path}")
        print("  Skipping image test")
        print()
        return
    
    print(f"Testing with: {image_path}")
    print()
    
    # Test classifier
    from integrations.screenshot_classifier import get_classifier
    classifier = get_classifier()
    
    print("Step 1: Classification")
    is_valid, confidence, metadata = classifier.classify(image_path)
    print(f"  Result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"  Confidence: {confidence:.3f}")
    print(f"  Scores: {metadata.get('scores', {})}")
    print()
    
    if not is_valid:
        print("✗ Image rejected by classifier")
        print()
        return
    
    # Test OCR
    from integrations.paddle_ocr_engine import get_paddle_ocr
    ocr_engine = get_paddle_ocr()
    
    print("Step 2: OCR Extraction")
    result = ocr_engine.extract_from_image(image_path)
    
    if result.get("success"):
        print("  ✓ OCR successful")
        structured = result.get("structured_data", {})
        scores = result.get("scores", {})
        
        print(f"  Players found: {structured.get('player_count', 0)}/8")
        print(f"  OCR confidence: {scores.get('overall', 0):.3f}")
        print()
        
        # Show detected players
        players = structured.get("players", [])
        if players:
            print("  Detected placements:")
            for player in sorted(players, key=lambda x: x.get("placement", 99)):
                print(f"    {player.get('placement', '?')}. {player.get('name', 'Unknown')}")
        else:
            print("  ✗ No players detected")
        print()
    else:
        print(f"  ✗ OCR failed: {result.get('error', 'Unknown error')}")
        print()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PaddleOCR Screenshot System Test")
    print("="*60)
    print()
    
    # Test 1: Classifier
    try:
        test_classifier()
    except Exception as e:
        print(f"✗ Classifier test failed: {e}")
        print()
    
    # Test 2: PaddleOCR Engine
    try:
        paddle_ok = test_paddle_ocr()
    except Exception as e:
        print(f"✗ PaddleOCR test failed: {e}")
        print()
        paddle_ok = False
    
    # Test 3: Sample image (if available)
    if paddle_ok:
        sample_images = [
            "assets/templates/tft_standings/lobbyaround3.png",
            "assets/templates/tft_standings/lobbybround3.png",
            "assets/templates/tft_standings/lobbycround3.png"
        ]
        
        for img_path in sample_images:
            if os.path.exists(img_path):
                try:
                    test_with_sample_image(img_path)
                    break  # Test with first available image
                except Exception as e:
                    print(f"✗ Image test failed: {e}")
                    print()
    
    print("="*60)
    print("Test Complete!")
    print("="*60)
    print()


if __name__ == "__main__":
    main()
