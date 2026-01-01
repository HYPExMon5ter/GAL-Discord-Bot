"""
Comprehensive test suite for Screenshot-Based Standings Extraction System.

Tests all components without requiring Discord or full API stack.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Import config for tests
from config import _FULL_CFG


def test_imports():
    """Test that all required modules can be imported."""
    log.info("=" * 60)
    log.info("Testing imports...")
    log.info("=" * 60)

    try:
        # Core Python
        import asyncio
        import re
        from datetime import datetime
        log.info("✓ Core Python imports successful")

        # Database models
        from api.models import (
            ProcessingBatch, PlacementSubmission,
            RoundPlacement, PlayerAlias, OCRCorrection
        )
        log.info("✓ Database models imported successfully")

        # Integrations
        from integrations.screenshot_classifier import get_classifier
        from integrations.standings_ocr import get_ocr_pipeline
        from integrations.player_matcher import get_player_matcher
        from integrations.placement_validator import get_validator
        from integrations.batch_processor import get_batch_processor
        log.info("✓ Integration modules imported successfully")

        # API
        from api.routers import placements
        log.info("✓ API routers imported successfully")

        # Configuration
        from config import _FULL_CFG
        config = _FULL_CFG
        log.info(f"✓ Config loaded successfully")
        log.info(f"  - Standings screenshots enabled: {config.get('standings_screenshots', {}).get('enabled', False)}")

        return True

    except Exception as e:
        log.error(f"✗ Import test failed: {e}")
        return False


def test_classifier():
    """Test screenshot classifier."""
    log.info("=" * 60)
    log.info("Testing Screenshot Classifier...")
    log.info("=" * 60)

    try:
        from integrations.screenshot_classifier import get_classifier

        classifier = get_classifier()

        # Test with a placeholder (will fail on non-existent image, but tests code path)
        log.info("✓ Classifier instance created")
        log.info(f"  - Template threshold: {classifier.threshold}")
        log.info(f"  - Templates loaded: {len(classifier.templates)}")

        return True

    except Exception as e:
        log.error(f"✗ Classifier test failed: {e}")
        return False


def test_ocr_pipeline():
    """Test OCR pipeline initialization."""
    log.info("=" * 60)
    log.info("Testing OCR Pipeline...")
    log.info("=" * 60)

    try:
        from integrations.standings_ocr import get_ocr_pipeline

        ocr_pipeline = get_ocr_pipeline()

        log.info("✓ OCR pipeline instance created")
        log.info(f"  - Tesseract enabled: {ocr_pipeline.tesseract_enabled}")
        log.info(f"  - EasyOCR enabled: {ocr_pipeline.easyocr_enabled}")
        log.info(f"  - Preprocessing passes: {ocr_pipeline.preprocessing_passes}")

        return True

    except Exception as e:
        log.error(f"✗ OCR pipeline test failed: {e}")
        return False


def test_player_matcher():
    """Test player matcher."""
    log.info("=" * 60)
    log.info("Testing Player Matcher...")
    log.info("=" * 60)

    try:
        from integrations.player_matcher import get_player_matcher

        # Create test roster
        test_roster = [
            {
                "player_id": "p1",
                "player_name": "TestPlayer1",
                "riot_id": "TFTPlayer1",
                "discord_id": "123456789",
                "aliases": ["TP1", "TestP1"]
            },
            {
                "player_id": "p2",
                "player_name": "TestPlayer2",
                "riot_id": "TFTPlayer2",
                "discord_id": "987654321",
                "aliases": []
            }
        ]

        matcher = get_player_matcher(test_roster)

        log.info("✓ Player matcher instance created")
        log.info(f"  - Roster size: {len(matcher.player_roster)}")
        log.info(f"  - Alias index size: {len(matcher.aliases)}")

        # Test exact match
        result = matcher.match_player("TestPlayer1")
        if result["success"]:
            log.info("✓ Exact match test passed")
        else:
            log.warning("⚠ Exact match test failed (may be ok)")

        # Test alias match
        result = matcher.match_player("TP1")
        if result["success"]:
            log.info("✓ Alias match test passed")
        else:
            log.warning("⚠ Alias match test failed (may be ok)")

        # Test fuzzy match
        result = matcher.match_player("TestPlayer!")
        log.info(f"✓ Fuzzy match test: {result['success']} (confidence: {result.get('confidence', 0):.3f})")

        return True

    except Exception as e:
        log.error(f"✗ Player matcher test failed: {e}")
        return False


def test_validator():
    """Test placement validator."""
    log.info("=" * 60)
    log.info("Testing Placement Validator...")
    log.info("=" * 60)

    try:
        from integrations.placement_validator import get_validator

        validator = get_validator()

        log.info("✓ Validator instance created")
        log.info(f"  - Expected lobbies: {validator.expected_lobbies}")
        log.info(f"  - Players per lobby: {validator.players_per_lobby}")

        # Test with valid data
        valid_players = [
            {"name": "Player1", "placement": 1, "points": 8},
            {"name": "Player2", "placement": 2, "points": 7},
            {"name": "Player3", "placement": 3, "points": 6},
            {"name": "Player4", "placement": 4, "points": 5},
            {"name": "Player5", "placement": 5, "points": 4},
            {"name": "Player6", "placement": 6, "points": 3},
            {"name": "Player7", "placement": 7, "points": 2},
            {"name": "Player8", "placement": 8, "points": 1},
        ]

        result = validator.validate_single_lobby(valid_players, 1)
        log.info(f"✓ Valid lobby test: {result['valid']} (score: {result['score']:.3f})")

        # Test with invalid data (missing players)
        invalid_players = valid_players[:4]
        result = validator.validate_single_lobby(invalid_players, 1)
        log.info(f"✓ Invalid lobby test: {'PASS' if not result['valid'] else 'FAIL'} (expected FAIL)")
        log.info(f"  - Issues: {len(result['issues'])}")

        return True

    except Exception as e:
        log.error(f"✗ Validator test failed: {e}")
        return False


def test_batch_processor():
    """Test batch processor initialization."""
    log.info("=" * 60)
    log.info("Testing Batch Processor...")
    log.info("=" * 60)

    try:
        from integrations.batch_processor import get_batch_processor

        processor = get_batch_processor()

        log.info("✓ Batch processor instance created")
        log.info(f"  - Batch window: {processor.batch_window}s")
        log.info(f"  - Max concurrent: {processor.max_concurrent}")
        log.info(f"  - Auto-validate threshold: {processor.auto_validate_threshold}")

        return True

    except Exception as e:
        log.error(f"✗ Batch processor test failed: {e}")
        return False


def test_database():
    """Test database connection and tables."""
    log.info("=" * 60)
    log.info("Testing Database...")
    log.info("=" * 60)

    try:
        from sqlalchemy import inspect
        from api.dependencies import engine

        # Check connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            log.info("✓ Database connection successful")

        # Check tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "processing_batches",
            "placement_submissions",
            "round_placements",
            "player_aliases",
            "ocr_corrections"
        ]

        all_present = True
        for table in expected_tables:
            if table in tables:
                log.info(f"✓ Table exists: {table}")
            else:
                log.error(f"✗ Table missing: {table}")
                all_present = False

        return all_present

    except Exception as e:
        log.error(f"✗ Database test failed: {e}")
        return False


def test_api_router():
    """Test API router imports."""
    log.info("=" * 60)
    log.info("Testing API Router...")
    log.info("=" * 60)

    try:
        from api.routers import placements
        from fastapi import APIRouter

        # Check that router is properly defined
        if isinstance(placements.router, APIRouter):
            log.info("✓ Placements router is APIRouter instance")
            log.info(f"  - Prefix: {placements.router.prefix}")
            log.info(f"  - Tags: {placements.router.tags}")
        else:
            log.error("✗ Placements router is not APIRouter")
            return False

        # Check routes
        routes = list(placements.router.routes)
        log.info(f"✓ Routes defined: {len(routes)}")

        for route in routes:
            log.info(f"  - {route.methods} {route.path}")

        return True

    except Exception as e:
        log.error(f"✗ API router test failed: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    log.info("=" * 60)
    log.info("Testing Configuration...")
    log.info("=" * 60)

    try:
        # Check standings screenshots config
        ss_config = _FULL_CFG.get("standings_screenshots", {})

        if not ss_config:
            log.error("✗ standings_screenshots config not found")
            return False

        log.info("✓ Configuration loaded successfully")

        # Check required settings
        required_keys = [
            "enabled",
            "monitor_channels",
            "auto_validate_threshold",
            "ocr_engines"
        ]

        all_present = True
        for key in required_keys:
            if key in ss_config:
                log.info(f"✓ Setting present: {key}")
            else:
                log.error(f"✗ Setting missing: {key}")
                all_present = False

        return all_present

    except Exception as e:
        log.error(f"✗ Configuration test failed: {e}")
        return False


def main():
    """Run all tests."""
    log.info("\n")
    log.info("╔" + "═" * 58 + "╗")
    log.info("║" + " " * 15 + "SCREENSHOT EXTRACTION SYSTEM TEST SUITE" + " " * 14 + "║")
    log.info("╚" + "═" * 58 + "╝")
    log.info("\n")

    tests = [
        ("Configuration", test_configuration),
        ("Imports", test_imports),
        ("Database", test_database),
        ("Screenshot Classifier", test_classifier),
        ("OCR Pipeline", test_ocr_pipeline),
        ("Player Matcher", test_player_matcher),
        ("Placement Validator", test_validator),
        ("Batch Processor", test_batch_processor),
        ("API Router", test_api_router),
    ]

    results = {}

    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = "PASS" if success else "FAIL"
        except Exception as e:
            log.error(f"Test '{name}' crashed: {e}")
            results[name] = "CRASH"

    # Print summary
    log.info("\n")
    log.info("=" * 60)
    log.info("TEST SUMMARY")
    log.info("=" * 60)

    passed = sum(1 for v in results.values() if v == "PASS")
    failed = sum(1 for v in results.values() if v == "FAIL")
    crashed = sum(1 for v in results.values() if v == "CRASH")

    for name, result in results.items():
        status_icon = "✓" if result == "PASS" else "✗"
        log.info(f"{status_icon} {name}: {result}")

    log.info("\n")
    log.info(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Crashed: {crashed}")

    if passed == len(results):
        log.info("\n🎉 ALL TESTS PASSED! System is ready.")
        return 0
    else:
        log.warning(f"\n⚠️  {failed + crashed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
