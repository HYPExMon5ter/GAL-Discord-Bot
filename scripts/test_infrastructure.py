#!/usr/bin/env python3
"""
Infrastructure Test

Tests the basic infrastructure without requiring external API keys.
Validates that the system components are properly configured.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_environment():
    """Test environment configuration."""
    print("Environment Test")
    print("================")
    
    results = {
        "riot_api_key": bool(os.getenv("RIOT_API_KEY")),
        "database_url": bool(os.getenv("DATABASE_URL")),
        "discord_token": bool(os.getenv("DISCORD_TOKEN"))
    }
    
    for key, value in results.items():
        status = "OK" if value else "MISSING"
        print(f"{key}: {status}")
        
    return all(results.values())


def test_imports():
    """Test that all required modules can be imported."""
    print("\nImport Test")
    print("=============")
    
    modules = {
        "RiotAPI": "integrations.riot_api",
        "MockRiotAPI": "api.services.mock_riot_api",
        "StandingsAggregator": "api.services.standings_aggregator",
        "StandingsService": "api.services.standings_service"
    }
    
    results = {}
    
    for name, module in modules.items():
        try:
            __import__(module)
            results[name] = True
            print(f"{name}: OK")
        except ImportError as e:
            results[name] = False
            print(f"{name}: FAILED - {e}")
            
    return all(results.values())


async def test_mock_riot_api():
    """Test the MockRiotAPI service."""
    print("\nMock Riot API Test")
    print("===================")
    
    try:
        from api.services.mock_riot_api import MockRiotAPI
        
        # Test basic functionality
        async with MockRiotAPI() as mock_api:
            # Test a known player
            result = await mock_api.get_latest_placement("na", "Alice#NA1")
            
            if result.get("success") and result.get("placement") == 1:
                print("Mock API: OK - Returns expected data")
                return True
            else:
                print(f"Mock API: FAILED - Unexpected result: {result}")
                return False
                
    except Exception as e:
        print(f"Mock API: ERROR - {e}")
        return False


def test_database_setup():
    """Test database configuration."""
    print("\nDatabase Test")
    print("==============")
    
    try:
        from sqlalchemy import create_engine
        from api.models import Base
        
        # Test creating an in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        
        print("Database schema: OK")
        return True
        
    except Exception as e:
        print(f"Database: ERROR - {e}")
        return False


def test_scoreboard_schemas():
    """Test scoreboard schema definitions."""
    print("\nSchema Test")
    print("=============")
    
    try:
        from api.schemas.scoreboard import (
            ScoreboardSnapshotCreate,
            ScoreboardEntryCreate,
            ScoreboardRefreshRequest
        )
        
        # Test creating a sample entry
        entry = ScoreboardEntryCreate(
            player_name="Test Player",
            total_points=10,
            round_scores={"round_1": 5, "round_2": 5}
        )
        
        # Test creating a refresh request
        request = ScoreboardRefreshRequest(
            guild_id=12345,
            fetch_riot=True,
            region="na"
        )
        
        print("Schemas: OK")
        return True
        
    except Exception as e:
        print(f"Schemas: ERROR - {e}")
        return False


async def main():
    """Run all infrastructure tests."""
    print("GAL Infrastructure Test")
    print("======================\n")
    
    results = {
        "environment": test_environment(),
        "imports": test_imports(),
        "mock_riot_api": await test_mock_riot_api(),
        "database": test_database_setup(),
        "schemas": test_scoreboard_schemas()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
        
    print(f"\nPassed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "total": total_tests,
            "passed": passed_tests,
            "success_rate": passed_tests/total_tests
        },
        "infrastructure_ready": passed_tests >= total_tests * 0.8
    }
    
    # Save report
    report_file = f"infrastructure_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nReport saved to: {report_file}")
    print(f"Infrastructure Ready: {'YES' if report['infrastructure_ready'] else 'NO'}")
    
    return report["infrastructure_ready"]


if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(main())
        sys.exit(0 if result else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(2)
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(3)
