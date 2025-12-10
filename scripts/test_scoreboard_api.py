#!/usr/bin/env python3
"""
Scoreboard API Integration Test

Tests the full backend pipeline:
1. Creates a test tournament with real player data
2. Triggers scoreboard refresh with Riot API
3. Validates data processing and persistence
4. Verifies API endpoints return correct data
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.models import Base
from api.schemas.scoreboard import ScoreboardRefreshRequest
from api.services.standings_service import StandingsService
from api.services.standings_aggregator import StandingsAggregator

logger = print  # Using print for simplicity

# Test configuration
TEST_GUILD_ID = 999999  # Use a test guild ID
TEST_TOURNAMENT_ID = "test_riot_integration"
TEST_TOURNAMENT_NAME = "Riot API Integration Test"
TEST_REGION = "na"

# Test players with real Riot IDs (subset from test_riot_integration.py)
TEST_PLAYERS = [
    {"player_name": "Dishsoap", "ign": "Dishsoap#NA1", "discord_tag": "dishsoap#1234"},
    {"player_name": "K3soju", "ign": "K3soju#NA1", "discord_tag": "k3soju#5678"},
    {"player_name": "Roux", "ign": "Roux#NA1", "discord_tag": "roux#9012"},
    {"player_name": "Hyped", "ign": "Hyped#NA1", "discord_tag": "hyped#3456"},
    {"player_name": "Mooju", "ign": "Mooju#NA1", "discord_tag": "mooju#7890"},
    # Add some invalid players to test error handling
    {"player_name": "Invalid Player", "ign": "InvalidPlayer#NA1", "discord_tag": "invalid#0000"},
    {"player_name": "No Games", "ign": "NoGamesPlayer#NA1", "discord_tag": "nogames#1111"}
]

# Expected points conversion (placement -> points)
PLACEMENT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}


class ScoreboardTestResults:
    """Container for scoreboard test results."""
    
    def __init__(self):
        self.test_start = time.time()
        self.api_test_results = {}
        self.database_results = {}
        self.errors = []
        self.success = False
        
    def add_api_result(self, test_name: str, success: bool, data: Dict = None, error: str = None):
        """Add an API test result."""
        self.api_test_results[test_name] = {
            "success": success,
            "data": data,
            "error": error,
            "timestamp": time.time()
        }
        if error:
            self.errors.append(f"{test_name}: {error}")
            
    def add_database_result(self, test_name: str, success: bool, data: Dict = None, error: str = None):
        """Add a database validation result."""
        self.database_results[test_name] = {
            "success": success,
            "data": data,
            "error": error,
            "timestamp": time.time()
        }
        if error:
            self.errors.append(f"DB:{test_name}: {error}")
            
    def is_successful(self) -> bool:
        """Check if all tests passed."""
        api_success = all(r.get("success", False) for r in self.api_test_results.values())
        db_success = all(r.get("success", False) for r in self.database_results.values())
        return api_success and db_success and len(self.errors) == 0
        
    def get_duration(self) -> float:
        """Get total test duration."""
        return time.time() - self.test_start


async def test_scoreboard_refresh(aggregator: StandingsAggregator) -> Dict:
    """Test the scoreboard refresh endpoint functionality."""
    logger.info("🔄 Testing scoreboard refresh with Riot API...")
    
    # Create snapshot override with test players
    snapshot_override = {
        "mode": "normal",
        "metadata": {"source": "integration_test"},
        "standings": [
            {
                "player_name": p["player_name"],
                "ign": p["ign"],
                "discord_tag": p["discord_tag"],
                "points": 0,  # Will be populated from Riot API
                "round_scores": {},  # Will be populated from Riot API
                "sheet_row": str(i + 1)
            }
            for i, p in enumerate(TEST_PLAYERS)
        ]
    }
    
    try:
        # Perform scoreboard refresh
        start_time = time.time()
        snapshot = await aggregator.refresh_scoreboard(
            guild_id=TEST_GUILD_ID,
            tournament_id=TEST_TOURNAMENT_ID,
            tournament_name=TEST_TOURNAMENT_NAME,
            region=TEST_REGION,
            fetch_riot=True,
            sync_sheet=False,  # Skip Google Sheets
            source="integration_test",
            snapshot_override=snapshot_override
        )
        
        refresh_time = time.time() - start_time
        
        # Validate basic snapshot data
        if not snapshot:
            return {
                "success": False,
                "error": "No snapshot returned",
                "refresh_time": refresh_time
            }
            
        # Extract snapshot data
        snapshot_data = {
            "tournament_id": snapshot.tournament_id,
            "tournament_name": snapshot.tournament_name,
            "source": snapshot.source,
            "round_names": snapshot.round_names,
            "total_players": len(snapshot.entries),
            "refresh_time": refresh_time
        }
        
        # Validate entries
        entries_data = []
        for entry in snapshot.entries:
            entry_data = {
                "player_name": entry.player_name,
                "riot_id": entry.riot_id,
                "total_points": entry.total_points,
                "standing_rank": entry.standing_rank,
                "round_scores": entry.round_scores or {}
            }
            entries_data.append(entry_data)
            
            # Validate points are reasonable
            if entry.total_points < 0 or entry.total_points > 100:
                return {
                    "success": False,
                    "error": f"Invalid total_points for {entry.player_name}: {entry.total_points}",
                    "refresh_time": refresh_time
                }
                
        snapshot_data["entries"] = entries_data
        
        return {
            "success": True,
            "data": snapshot_data,
            "refresh_time": refresh_time
        }
        
    except Exception as e:
        logger.error(f"Scoreboard refresh failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "refresh_time": time.time() - start_time if 'start_time' in locals() else 0
        }


def test_database_persistence(service: StandingsService) -> Dict:
    """Test that data was correctly persisted to database."""
    logger.info("💾 Testing database persistence...")
    
    try:
        # Test 1: Get latest snapshot
        latest = service.get_latest_snapshot(
            tournament_id=TEST_TOURNAMENT_ID,
            guild_id=str(TEST_GUILD_ID)
        )
        
        if not latest:
            return {
                "success": False,
                "error": "No snapshot found in database"
            }
            
        # Validate snapshot metadata
        if latest.tournament_id != TEST_TOURNAMENT_ID:
            return {
                "success": False,
                "error": f"Tournament ID mismatch: {latest.tournament_id} != {TEST_TOURNAMENT_ID}"
            }
            
        # Test 2: Validate entries
        entries = service._session.query(service._session.bind.execute(
            "SELECT * FROM scoreboard_entries WHERE snapshot_id = :sid",
            {"sid": latest.id}
        ).fetchall())
        
        if not entries:
            return {
                "success": False,
                "error": "No entries found in database"
            }
            
        # Test 3: Validate round scores
        round_scores_valid = True
        for entry in latest.entries or []:
            if not entry.round_scores:
                continue
            for round_name, score in entry.round_scores.items():
                if not isinstance(score, int) or score < 0:
                    round_scores_valid = False
                    break
                    
        return {
            "success": True,
            "data": {
                "snapshot_id": latest.id,
                "total_entries": len(latest.entries) if latest.entries else 0,
                "round_names": latest.round_names or [],
                "round_scores_valid": round_scores_valid
            }
        }
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def test_data_quality(snapshot_data: Dict) -> Dict:
    """Test the quality and correctness of the processed data."""
    logger.info("🔍 Testing data quality...")
    
    issues = []
    
    # Check 1: All test players are present
    snapshot_players = {e["player_name"] for e in snapshot_data.get("entries", [])}
    expected_players = {p["player_name"] for p in TEST_PLAYERS}
    
    missing_players = expected_players - snapshot_players
    if missing_players:
        issues.append(f"Missing players: {missing_players}")
        
    # Check 2: Points are correctly calculated
    for entry in snapshot_data.get("entries", []):
        total = entry["total_points"]
        round_scores = entry.get("round_scores", {})
        
        if "round_1" in round_scores:
            # Points should match placement conversion
            expected_total = round_scores["round_1"]
            if total != expected_total:
                issues.append(f"Points mismatch for {entry['player_name']}: {total} != {expected_total}")
                
    # Check 3: Rankings are correct
    sorted_by_points = sorted(
        snapshot_data.get("entries", []),
        key=lambda e: e["total_points"],
        reverse=True
    )
    
    for i, entry in enumerate(sorted_by_points):
        expected_rank = i + 1
        actual_rank = entry.get("standing_rank")
        if actual_rank and actual_rank != expected_rank:
            issues.append(f"Ranking mismatch for {entry['player_name']}: {actual_rank} != {expected_rank}")
            
    # Check 4: Invalid players handled correctly
    for entry in snapshot_data.get("entries", []):
        if "Invalid" in entry["player_name"] or "No Games" in entry["player_name"]:
            # These should have 0 points
            if entry["total_points"] > 0:
                issues.append(f"Invalid player has points: {entry['player_name']} - {entry['total_points']}")
                
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "data_quality_score": max(0, 100 - len(issues) * 10)
    }


def cleanup_test_data(service: StandingsService) -> None:
    """Clean up test data from database."""
    logger.info("🧹 Cleaning up test data...")
    
    try:
        # Get test snapshot
        snapshot = service.get_latest_snapshot(
            tournament_id=TEST_TOURNAMENT_ID,
            guild_id=str(TEST_GUILD_ID)
        )
        
        if snapshot:
            # Delete snapshot (cascade deletes entries)
            service.delete_snapshot(snapshot.id)
            logger.info(f"✅ Deleted test snapshot {snapshot.id}")
        else:
            logger.info("ℹ️ No test snapshot found to clean up")
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to clean up test data: {e}")


async def run_integration_test() -> Dict:
    """Run the full scoreboard API integration test."""
    print("🚀 Starting Scoreboard API Integration Test")
    print("=" * 60)
    
    # Initialize database
    logger.info("🔧 Setting up test database...")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    session = SessionLocal()
    try:
        # Initialize services
        standings_service = StandingsService(session)
        aggregator = StandingsAggregator(standings_service)
        
        # Test results container
        results = ScoreboardTestResults()
        
        # Run tests
        logger.info("\n1️⃣ Testing scoreboard refresh...")
        refresh_result = await test_scoreboard_refresh(aggregator)
        results.add_api_result(
            "scoreboard_refresh",
            refresh_result["success"],
            refresh_result.get("data"),
            refresh_result.get("error")
        )
        
        if refresh_result["success"]:
            snapshot_data = refresh_result["data"]
            
            logger.info("✅ Scoreboard refresh successful")
            logger.info(f"   - Processed {snapshot_data['total_players']} players")
            logger.info(f"   - Refresh took {snapshot_data['refresh_time']:.2f}s")
            
            # Test data quality
            logger.info("\n2️⃣ Testing data quality...")
            quality_result = test_data_quality(snapshot_data)
            results.add_api_result(
                "data_quality",
                quality_result["success"],
                {"score": quality_result.get("data_quality_score", 0)},
                "; ".join(quality_result.get("issues", []))
            )
            
            # Test database persistence
            logger.info("\n3️⃣ Testing database persistence...")
            db_result = test_database_persistence(standings_service)
            results.add_database_result(
                "persistence",
                db_result["success"],
                db_result.get("data"),
                db_result.get("error")
            )
        else:
            logger.error(f"❌ Scoreboard refresh failed: {refresh_result.get('error')}")
            
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        print(f"\n✅ Successful Tests:")
        for name, result in results.api_test_results.items():
            if result["success"]:
                print(f"   • {name}")
                
        if results.database_results:
            print(f"\n💾 Database Tests:")
            for name, result in results.database_results.items():
                status = "✅" if result["success"] else "❌"
                print(f"   {status} {name}")
                
        if results.errors:
            print(f"\n❌ Errors:")
            for error in results.errors:
                print(f"   • {error}")
                
        print(f"\n⏱️ Total Duration: {results.get_duration():.2f}s")
        
        # Final status
        success = results.is_successful()
        print(f"\n🚦 Status: {'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
        
        results.success = success
        
        # Prepare report
        report = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "duration": results.get_duration(),
            "api_tests": results.api_test_results,
            "database_tests": results.database_results,
            "errors": results.errors,
            "test_players": len(TEST_PLAYERS)
        }
        
        # Save report
        report_file = f"scoreboard_api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to: {report_file}")
        
        # Cleanup
        logger.info("\n🧹 Cleaning up...")
        cleanup_test_data(standings_service)
        
        return report
        
    finally:
        session.close()
        engine.dispose()
        logger.info("✅ Test database cleaned up")


def main():
    """Run the scoreboard API integration test."""
    print("Scoreboard API Integration Test")
    print("===============================")
    print("This test validates the full backend pipeline:")
    print("1. Creates a test tournament with real player data")
    print("2. Triggers scoreboard refresh with Riot API")
    print("3. Validates data processing and persistence")
    print("4. Verifies API endpoints return correct data\n")
    
    # Run the async test
    try:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(run_integration_test())
        
        # Exit with appropriate code
        sys.exit(0 if results.get("success", False) else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
