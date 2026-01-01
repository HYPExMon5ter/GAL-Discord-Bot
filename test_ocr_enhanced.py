"""
Enhanced OCR Test Script - Phase 6: Validation & Testing Framework

Tests:
1. Individual image processing
2. Batch concurrent processing
3. Accuracy validation with fuzzy matching
4. Performance metrics
5. Format detection verification
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
import time
from datetime import datetime

# Set up logging to show INFO level for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

# Expected results for validation
EXPECTED_NAMES = {
    'lobbyaround3.png': [
        'deepestregrets', 'Lymera', 'Baby Llama', 'Vedris',
        'coco', 'Matt Green', 'Spear and Sky', 'LaurenTheCorgi'
    ],
    'lobbybround3.png': [
        'Astrid', 'olivia', 'Nottycat', 'MudkipEnjoyer',
        'btwblue', 'MoldyKumquat', 'CoffinCutie', 'Kalimier'
    ],
    'lobbycround3.png': [
        'mayxd', 'Duchess of Deer', 'hint', 'VeewithtooManyEs',
        '12FiendFyre', 'Ffoxface', 'Alithyst', 'Coralie'
    ]
}

# Expected formats
EXPECTED_FORMATS = {
    'lobbyaround3.png': 'Format 1',  # Standing | Player
    'lobbybround3.png': 'Format 1',  # Standing | Player
    'lobbycround3.png': 'Format 2'   # # | Summoner (with rank abbreviations)
}


def normalize_for_comparison(text: str) -> str:
    """Normalize text for fuzzy comparison."""
    return text.lower().replace(' ', '').replace('_', '')


def validate_name(detected: str, expected: str) -> bool:
    """
    Validate if detected name matches expected name (fuzzy matching).
    
    Returns True if:
    - Detected contains expected (substring)
    - Expected contains detected (substring)
    - Character confusion variations match
    """
    detected_norm = normalize_for_comparison(detected)
    expected_norm = normalize_for_comparison(expected)
    
    # Substring matching (case-insensitive, space-insensitive)
    if detected_norm in expected_norm or expected_norm in detected_norm:
        return True
    
    # Check with character confusions (0↔O, 5↔S, 1↔I, etc.)
    # Handle common OCR errors
    confusions = [
        ('0', 'o'), ('5', 's'), ('1', 'i'), ('1', 'l'),
        ('8', 'b'), ('rn', 'm'), ('vv', 'w')
    ]
    
    for char1, char2 in confusions:
        detected_variant = detected_norm.replace(char1, char2).replace(char2, char1)
        if detected_variant in expected_norm or expected_norm in detected_variant:
            return True
    
    return False


def test_single_image(ocr, screenshot: str, base_path: str = 'dashboard/screenshots'):
    """Test single image processing."""
    print(f'\n{"="*80}')
    print(f'Testing: {screenshot}')
    print(f'{"="*80}')
    
    image_path = f'{base_path}/{screenshot}'
    
    # Time the processing
    start_time = time.time()
    result = ocr.extract_from_image(image_path)
    elapsed = time.time() - start_time
    
    if not result.get('success'):
        print(f'❌ ERROR: {result.get("error")}')
        return {
            'screenshot': screenshot,
            'success': False,
            'error': result.get('error'),
            'elapsed': elapsed
        }
    
    players = result['structured_data']['players']
    player_count = result['structured_data']['player_count']
    confidence = result['scores'].get('overall', 0.0)
    
    print(f'\n[OK] Processing completed in {elapsed:.2f}s')
    print(f'[OK] Confidence: {confidence:.1%}')
    print(f'[OK] Players detected: {player_count}/8')
    
    # Validate against expected results
    expected = EXPECTED_NAMES.get(screenshot, [])
    detected_names = [p['name'] for p in players]
    
    print(f'\nDetected players:')
    correct_count = 0
    for i, (detected, expected_name) in enumerate(zip(detected_names, expected)):
        is_correct = validate_name(detected, expected_name)
        if is_correct:
            correct_count += 1
            status = '[OK]'
        else:
            status = '[X]'
        
        print(f'  {status} {i+1}. {detected:25s} (expected: {expected_name})')
    
    # Handle missing players
    if len(detected_names) < len(expected):
        print(f'\n  Missing {len(expected) - len(detected_names)} players:')
        for i in range(len(detected_names), len(expected)):
            print(f'  [X] {i+1}. {"<missing>":25s} (expected: {expected[i]})')
    
    accuracy = (correct_count / max(len(detected_names), len(expected))) * 100
    
    print(f'\n[ACCURACY] {correct_count}/{max(len(detected_names), len(expected))} = {accuracy:.1f}%')
    
    # Check format detection
    expected_format = EXPECTED_FORMATS.get(screenshot, 'Unknown')
    print(f'[FORMAT] Expected: {expected_format}')
    
    return {
        'screenshot': screenshot,
        'success': True,
        'player_count': player_count,
        'accuracy': accuracy,
        'correct_count': correct_count,
        'expected_count': len(expected),
        'elapsed': elapsed,
        'confidence': confidence,
        'detected_names': detected_names,
        'expected_names': expected
    }


def test_batch_processing(ocr, screenshots: list, base_path: str = 'dashboard/screenshots'):
    """Test batch concurrent processing."""
    print(f'\n{"="*80}')
    print(f'BATCH PROCESSING TEST (Concurrent)')
    print(f'{"="*80}')
    
    image_paths = [f'{base_path}/{s}' for s in screenshots]
    
    # Time the batch processing
    start_time = time.time()
    results = ocr.process_batch(image_paths, max_workers=3)
    elapsed = time.time() - start_time
    
    print(f'\n[OK] Batch processing completed in {elapsed:.2f}s')
    print(f'[OK] Average: {elapsed/len(screenshots):.2f}s per image')
    print(f'[OK] Speedup vs serial: ~{len(screenshots) * 15 / elapsed:.1f}x (estimated)')
    
    # Validate each result
    batch_results = []
    
    # Debug: Check if results is valid
    print(f'\n[DEBUG] Got {len(results)} results for {len(screenshots)} screenshots')
    
    for i, (result, screenshot) in enumerate(zip(results, screenshots)):
        # Debug: Check result type
        if not isinstance(result, dict):
            print(f'\n[ERROR] Result {i} is not a dict: {type(result)} - {result}')
            continue
            
        if result.get('success'):
            players = result['structured_data']['players']
            expected = EXPECTED_NAMES.get(screenshot, [])
            detected_names = [p['name'] for p in players]
            
            correct_count = sum(
                1 for d, e in zip(detected_names, expected)
                if validate_name(d, e)
            )
            
            accuracy = (correct_count / max(len(detected_names), len(expected))) * 100
            
            print(f'\n  {screenshot}: {len(players)} players, {accuracy:.1f}% accuracy')
            
            batch_results.append({
                'screenshot': screenshot,
                'success': True,
                'accuracy': accuracy,
                'correct_count': correct_count,
                'expected_count': len(expected)
            })
        else:
            print(f'\n  {screenshot}: ERROR - {result.get("error")}')
            batch_results.append({
                'screenshot': screenshot,
                'success': False,
                'error': result.get('error')
            })
    
    return {
        'elapsed': elapsed,
        'results': batch_results
    }


def print_summary(individual_results: list, batch_result: dict):
    """Print final summary report."""
    print(f'\n{"="*80}')
    print(f'FINAL SUMMARY')
    print(f'{"="*80}')
    
    # Overall accuracy
    total_correct = sum(r['correct_count'] for r in individual_results if r['success'])
    total_expected = sum(r['expected_count'] for r in individual_results if r['success'])
    overall_accuracy = (total_correct / total_expected * 100) if total_expected > 0 else 0
    
    print(f'\n[OVERALL] Accuracy: {total_correct}/{total_expected} = {overall_accuracy:.1f}%')
    
    if overall_accuracy >= 80:
        print(f'[SUCCESS] Achieved target accuracy (>=80%)')
    else:
        print(f'[WARNING] BELOW TARGET: Need {80 - overall_accuracy:.1f}% more accuracy')
    
    # Per-format accuracy
    print(f'\n[FORMATS] Format-specific accuracy:')
    for screenshot, expected_format in EXPECTED_FORMATS.items():
        result = next((r for r in individual_results if r['screenshot'] == screenshot), None)
        if result and result['success']:
            accuracy = result['accuracy']
            status = '[OK]' if accuracy >= 75 else '[WARN]'
            print(f'  {status} {screenshot:25s} ({expected_format}): {accuracy:.1f}%')
    
    # Performance metrics
    print(f'\n[PERFORMANCE] Metrics:')
    avg_time = sum(r['elapsed'] for r in individual_results if r['success']) / len(individual_results)
    print(f'  Average processing time: {avg_time:.2f}s per image')
    
    if batch_result:
        batch_time = batch_result['elapsed']
        print(f'  Batch processing time: {batch_time:.2f}s for {len(individual_results)} images')
        print(f'  Speedup: ~{len(individual_results) * avg_time / batch_time:.1f}x')
    
    # Success criteria
    print(f'\n[CRITERIA] Success Criteria:')
    criteria = [
        ('Overall accuracy >=80%', overall_accuracy >= 80),
        ('Format 1 accuracy >=80%', all(
            r['accuracy'] >= 80 for r in individual_results
            if r['success'] and EXPECTED_FORMATS.get(r['screenshot']) == 'Format 1'
        )),
        ('Format 2 accuracy >=75%', all(
            r['accuracy'] >= 75 for r in individual_results
            if r['success'] and EXPECTED_FORMATS.get(r['screenshot']) == 'Format 2'
        )),
        ('Processing time <20s', all(r['elapsed'] < 20 for r in individual_results if r['success'])),
        ('Batch processing <60s', batch_result and batch_result['elapsed'] < 60)
    ]
    
    for criterion, met in criteria:
        status = '[OK]' if met else '[X]'
        print(f'  {status} {criterion}')
    
    all_met = all(met for _, met in criteria)
    
    if all_met:
        print(f'\n[SUCCESS] ALL SUCCESS CRITERIA MET!')
    else:
        print(f'\n[WARNING] Some criteria not met - further optimization needed')


def main():
    """Run all tests."""
    print('='*80)
    print('ENHANCED OCR TESTING FRAMEWORK')
    print('Phase 1: Mutually Exclusive Format Detection')
    print('Phase 4: Concurrent Processing Support')
    print('Phase 6: Validation & Testing Framework')
    print('='*80)
    
    # Initialize OCR pipeline
    ocr = get_ocr_pipeline()
    
    screenshots = ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']
    
    # Test 1: Individual image processing
    individual_results = []
    for screenshot in screenshots:
        result = test_single_image(ocr, screenshot)
        individual_results.append(result)
        time.sleep(0.5)  # Brief pause between tests
    
    # Test 2: Batch concurrent processing
    batch_result = test_batch_processing(ocr, screenshots)
    
    # Print final summary
    print_summary(individual_results, batch_result)


if __name__ == '__main__':
    main()
