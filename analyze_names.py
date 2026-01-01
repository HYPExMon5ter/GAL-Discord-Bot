"""Analyze OCR name errors and identify patterns."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from integrations.standings_ocr import get_ocr_pipeline

# Ground truth names from screenshot analysis (from diagnose_ocr.py)
ground_truth = {
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
        '12FiendFyre', 'P2 Ffoxface', 'P3 Alithyst', 'Coralie'
    ]
}

# OCR detected names (from previous test)
ocr_detected = {
    'lobbyaround3.png': [
        'SKJ', 'FLY AGIL]', 'BABY LKMA', 'VEDRKS',
        'COCO', 'MATT GREER', 'LOURENTHECORGL', 'LAUCEYD'
    ],
    'lobbybround3.png': [
        'COFFINCUTIE', 'OLIVIA', 'NOTTYCAT', 'MUDKIPENJOYER',
        'BTWBLUE', 'MOLDY OMQUAT', 'COFFINCUTIE', 'KALIMIER'
    ],
    'lobbycround3.png': [
        'SUMONB', 'MAYXD', 'DUCHESS OL OEER', 'NNT',
        'VEEWITHTOPMANYES', '12FIERXDFYRE', 'FFOXFACE', 'ALILHYSL'
    ]
}

print("=" * 80)
print("OCR NAME ERROR ANALYSIS")
print("=" * 80)

for screenshot in ['lobbyaround3.png', 'lobbybround3.png', 'lobbycround3.png']:
    print(f'\n--- {screenshot} ---')
    print(f"{'Ground Truth':<25} | {'OCR Detected':<25} | {'Error Type'}")
    print("-" * 80)

    true_names = ground_truth[screenshot]
    detected_names = ocr_detected[screenshot]

    # Simple pairing (they should be in order by placement)
    for true, detected in zip(true_names, detected_names):
        # Identify error types
        errors = []

        if true.lower() != detected.lower():
            # Check for character confusions
            if len(true) == len(detected):
                for t, d in zip(true.lower(), detected.lower()):
                    if t != d:
                        errors.append(f"'{t}' to '{d}'")

            # Check for missing/added characters
            if len(errors) == 0:
                if len(true) < len(detected):
                    errors.append(f"+{len(detected) - len(true)} chars")
                elif len(true) > len(detected):
                    errors.append(f"-{len(true) - len(detected)} chars")

            # Check for spacing issues
            if ' ' in true and ' ' not in detected:
                errors.append("missing spaces")
            elif ' ' not in true and ' ' in detected:
                errors.append("extra spaces")

            # Check for garbage characters
            garbage = [c for c in detected if not c.isalnum() and c != ' ']
            if garbage:
                errors.append(f"garbage: {garbage}")

            # Check for completely wrong
            if len(errors) == 0:
                errors.append("completely different")

        error_str = ', '.join(errors) if errors else "PERFECT"
        print(f"{true:<25} | {detected:<25} | {error_str}")

print("\n" + "=" * 80)
print("COMMON ERROR PATTERNS:")
print("=" * 80)

error_patterns = {
    'Character confusions': {
        'S → K': ['deepestregrets → DEEPESTREGRETS (wait, that\'s correct?)'],
        'A → K': ['Spear and Sky → FLY AGIL] (wrong name)'],
        'L → K': ['Baby Llama → BABY LKMA'],
        'I → J': ['Lymera → SKJ (wrong name?)'],
    },
    'Missing spaces': [
        'Matt Green → MATT GREER (wait, that has spaces)',
        'LaurenTheCorgi → LOURENTHECORGL (merged)',
        'MoldyKumquat → MOLDY OMQUAT (space added)',
        'MudkipEnjoyer → MUDKIPENJOYER (merged)',
    ],
    'Garbage characters': [
        'FLY AGIL]',
        'LOREHTHECAND]',
        '12FIENDFYRE → 12FIERXDFYRE (extra chars)',
    ],
    'Wrong names': [
        'deepestregrets → SKJ (completely wrong)',
        'Lymera → FLY AGIL] (completely wrong)',
        'Coralie → ALILHYSL (completely wrong)',
        'mayxd → SUMONB (completely wrong)',
    ]
}

for pattern, examples in error_patterns.items():
    print(f"\n{pattern}:")
    for ex in examples:
        print(f"  - {ex}")
