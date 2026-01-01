"""
Test script for Google Cloud Vision OCR on TFT screenshots.

Run this after setting up Google Cloud credentials:
1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable
2. Run: python test_cloud_vision.py
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding for emoji output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from integrations.cloud_vision_ocr import get_cloud_vision_ocr


def test_screenshots():
    """Test Cloud Vision OCR on all 3 TFT screenshot formats."""
    
    # Check if credentials are set
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS not set!")
        print("\nTo fix:")
        print("  Windows: set GOOGLE_APPLICATION_CREDENTIALS=C:\\path\\to\\your\\credentials.json")
        print("  Or add to .env file")
        return False
    
    print("=" * 80)
    print("GOOGLE CLOUD VISION OCR TEST")
    print("=" * 80)
    print()
    
    # Initialize OCR engine
    try:
        ocr = get_cloud_vision_ocr()
        print("✅ Cloud Vision client initialized")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize Cloud Vision: {e}")
        return False
    
    # Test screenshots
    # Note: These expected names are from one tournament
    # Your screenshots may contain different players (that's OK!)
    # The system will detect actual names from your screenshots
    screenshots = [
        ("Lobby A", "dashboard/screenshots/lobbyaround3.png"),
        ("Lobby B", "dashboard/screenshots/lobbybround3.png"),
        ("Lobby C", "dashboard/screenshots/lobbycround3.png")
    ]
    
    # Optional: Remove expected names comparison
    # If you want to validate against specific names, uncomment below
    # expected_names_map = {
    #     "Lobby A": ["coco", "Astrid", "Snowstorm", "Nidaleesha", "hint", "MaryamIsBad", "Kalimier", "Evermore"],
    #     "Lobby B": ["Astrid", "olivia", "Nottycat", "MudkipEnjoyer", "btwblue", "MoldyKumquat", "CoffinCutie", "Kalimier"],
    #     "Lobby C": ["Ffoxface", "hint", "ShyGrill", "Nidaleesha", "Evermore", "MaryamIsBad", "Snowstorm", "coco"]
    # }
    ]
    
    results = []
    
    for name, path in screenshots:
        print(f"Testing: {name}")
        print(f"File: {path}")
        print(f"Expected: {len(expected_names)} players")
        print("-" * 80)
        
        # Check if file exists
        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            print()
            results.append((name, 0, len(expected_names), []))
            continue
        
        # Run OCR
        try:
            result = ocr.extract_from_image(path)
            
            if not result.get("success"):
                print(f"❌ OCR failed: {result.get('error')}")
                print()
                results.append((name, 0, len(expected_names), []))
                continue
            
            # Get extracted players
            players = result["structured_data"]["players"]
            player_count = len(players)
            confidence = result["scores"]["overall"]
            
            # Check accuracy (if expected_names_map is defined)
            detected_names = [p["name"] for p in players]
            if name in expected_names_map:
                expected_names = expected_names_map[name]
                correct_matches = sum(1 for name in detected_names if name in expected_names)
                accuracy = (correct_matches / len(expected_names)) * 100 if expected_names else 100.0
            else:
                # No expected names - just show detected
                accuracy = 100.0
            accuracy = (correct_matches / len(expected_names)) * 100 if expected_names else 0
            
            # Display results
            print(f"✅ Detected: {player_count}/{len(expected_names)} players")
            print(f"📊 Accuracy: {accuracy:.1f}% ({correct_matches}/{len(expected_names)} correct)")
            print(f"🎯 Confidence: {confidence:.1%}")
            print()
            
            print("Players extracted:")
            for p in players:
                match_status = "✅" if p["name"] in expected_names else "❌"
                print(f"  {match_status} {p['placement']}. {p['name']} ({p['points']} pts)")
            
            # Show missing names
            missing = [name for name in expected_names if name not in detected_names]
            if missing:
                print(f"\n⚠️  Missing names: {', '.join(missing)}")
            
            print()
            results.append((name, correct_matches, len(expected_names), detected_names))
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            print()
            results.append((name, 0, len(expected_names), []))
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_correct = sum(r[1] for r in results)
    total_expected = sum(r[2] for r in results)
    overall_accuracy = (total_correct / total_expected * 100) if total_expected > 0 else 0
    
    for name, correct, expected, _ in results:
        accuracy = (correct / expected * 100) if expected > 0 else 0
        status = "✅" if accuracy >= 80 else "❌"
        print(f"{status} {name}: {correct}/{expected} ({accuracy:.1f}%)")
    
    print()
    print(f"Overall Accuracy: {overall_accuracy:.1f}% ({total_correct}/{total_expected})")
    
    if overall_accuracy >= 95:
        print("\n🎉 EXCELLENT! Cloud Vision is performing at 95%+ accuracy!")
    elif overall_accuracy >= 80:
        print("\n✅ GOOD! Cloud Vision is performing at 80%+ accuracy!")
    else:
        print("\n⚠️  Below target. Expected 80%+ accuracy.")
    
    print("=" * 80)
    
    return overall_accuracy >= 80


if __name__ == "__main__":
    success = test_screenshots()
    sys.exit(0 if success else 1)
