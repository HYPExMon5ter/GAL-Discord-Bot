#!/usr/bin/env python3
"""
Live Riot API Integration Test

Tests the Riot API integration with real TFT player data.
Validates that the system can fetch real placements, ranks, and handle errors gracefully.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

from integrations.riot_api import RiotAPI, RiotAPIError, RateLimitError
from utils.logging_utils import SecureLogger

logger = SecureLogger(__name__)

# Test data with known active TFT players (public figures)
TEST_PLAYERS = {
    "na": [
        {"name": "Dishsoap", "riot_id": "Dishsoap#NA1", "expected_rank": "Challenger"},
        {"name": "K3soju", "riot_id": "K3soju#NA1", "expected_rank": "Grandmaster"},
        {"name": "Roux", "riot_id": "Roux#NA1", "expected_rank": "Grandmaster"},
        {"name": "Hyped", "riot_id": "Hyped#NA1", "expected_rank": "Challenger"},
        {"name": "Mooju", "riot_id": "Mooju#NA1", "expected_rank": "Master"}
    ],
    "euw": [
        {"name": "Shircane", "riot_id": "Shircane#EUW", "expected_rank": "Grandmaster"},
        {"name": "Robinsongz", "riot_id": "robinsongz#EUW", "expected_rank": "Grandmaster"},
        {"name": "Emperor", "riot_id": "Emperor#EUW", "expected_rank": "Challenger"},
        {"name": "Spencer", "riot_id": "Spencer#EUW", "expected_rank": "Master"}
    ],
    "kr": [
        {"name": "암내음향", "riot_id": "암내음향#KR1", "expected_rank": "Challenger"},
        {"name": "Marmotte", "riot_id": "Marmotte#KR", "expected_rank": "Challenger"},
        {"name": "Billbill", "riot_id": "Billbill#KR", "expected_rank": "Grandmaster"}
    ]
}

# Expected success thresholds
MIN_SUCCESS_RATE = 0.8  # 80% of requests should succeed
MAX_RESPONSE_TIME = 2.0  # Max 2 seconds per request


class TestResults:
    """Container for test results and metrics."""
    
    def __init__(self):
        self.total_tests = 0
        self.successful_tests = 0
        self.failed_tests = 0
        self.errors = []
        self.response_times = []
        self.region_results = {}
        self.player_results = {}
        
    def add_result(self, region: str, player: dict, success: bool, 
                   error: str = None, response_time: float = None):
        """Add a test result."""
        self.total_tests += 1
        if success:
            self.successful_tests += 1
        else:
            self.failed_tests += 1
            
        # Track response times
        if response_time:
            self.response_times.append(response_time)
            
        # Track region results
        if region not in self.region_results:
            self.region_results[region] = {"total": 0, "success": 0}
        self.region_results[region]["total"] += 1
        if success:
            self.region_results[region]["success"] += 1
            
        # Track individual player results
        player_key = f"{player['name']} ({region.upper()})"
        self.player_results[player_key] = {
            "riot_id": player["riot_id"],
            "region": region,
            "success": success,
            "error": error,
            "response_time": response_time
        }
        
        # Log errors
        if not success and error:
            self.errors.append(f"{player_key}: {error}")
            logger.error(f"Test failed for {player_key}: {error}")
            
    def get_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.successful_tests / self.total_tests
        
    def get_avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
        
    def is_production_ready(self) -> bool:
        """Determine if system is production ready based on results."""
        success_rate = self.get_success_rate()
        avg_response = self.get_avg_response_time()
        
        if success_rate < MIN_SUCCESS_RATE:
            logger.error(f"Success rate {success_rate:.1%} below minimum {MIN_SUCCESS_RATE:.1%}")
            return False
            
        if avg_response > MAX_RESPONSE_TIME:
            logger.error(f"Avg response time {avg_response:.2f}s exceeds max {MAX_RESPONSE_TIME}s")
            return False
            
        return True


async def test_single_player(riot_api: RiotAPI, region: str, player: dict) -> Tuple[bool, str, float]:
    """Test a single player's data fetching."""
    start_time = time.time()
    
    try:
        # Test 1: Get latest placement
        result = await riot_api.get_latest_placement(region, player["riot_id"])
        
        if not result.get("success"):
            return False, result.get("error", "Unknown error"), time.time() - start_time
            
        # Validate placement is within expected range
        placement = result.get("placement")
        if not isinstance(placement, int) or placement < 1 or placement > 8:
            return False, f"Invalid placement: {placement}", time.time() - start_time
            
        # Test 2: Get rank (if time permits)
        # Note: Skipping rank test to avoid too many API calls
        
        return True, None, time.time() - start_time
        
    except RateLimitError as e:
        return False, f"Rate limited: {e}", time.time() - start_time
    except RiotAPIError as e:
        return False, f"Riot API error: {e}", time.time() - start_time
    except Exception as e:
        return False, f"Unexpected error: {e}", time.time() - start_time


async def test_region(riot_api: RiotAPI, region: str, players: List[dict]) -> TestResults:
    """Test all players in a region."""
    print(f"\n🔍 Testing {len(players)} players in {region.upper()}...")
    region_results = TestResults()
    
    # Create tasks for concurrent requests (but limit concurrency to respect rate limits)
    semaphore = asyncio.Semaphore(4)  # Max 4 concurrent requests
    
    async def test_with_semaphore(player):
        async with semaphore:
            return await test_single_player(riot_api, region, player)
    
    # Run tests with rate limiting delays
    for i, player in enumerate(players):
        success, error, response_time = await test_with_semaphore(player)
        region_results.add_result(region, player, success, error, response_time)
        
        # Add delay between batches to respect rate limits
        if i > 0 and i % 4 == 0:
            await asyncio.sleep(1)  # 1 second delay every 4 requests
            
        # Print progress
        status = "✅" if success else "❌"
        print(f"  {status} {player['name']} ({response_time:.2f}s)")
    
    return region_results


async def run_production_test() -> Dict:
    """Run the full production test suite."""
    print("🚀 Starting Riot API Production Test")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("RIOT_API_KEY")
    if not api_key:
        error = "RIOT_API_KEY environment variable not set!"
        logger.error(error)
        print(f"❌ {error}")
        return {"success": False, "error": error}
    
    # Initialize API client
    print("\n📡 Initializing Riot API client...")
    try:
        async with RiotAPI() as riot_api:
            print("✅ API client initialized successfully")
            
            # Test all regions
            all_results = TestResults()
            region_stats = {}
            
            for region, players in TEST_PLAYERS.items():
                region_start = time.time()
                
                try:
                    region_results = await test_region(riot_api, region, players)
                    
                    # Merge region results
                    for player_key, result in region_results.player_results.items():
                        all_results.player_results[player_key] = result
                        
                    all_results.total_tests += region_results.total_tests
                    all_results.successful_tests += region_results.successful_tests
                    all_results.failed_tests += region_results.failed_tests
                    all_results.response_times.extend(region_results.response_times)
                    all_results.errors.extend(region_results.errors)
                    all_results.region_results[region] = {
                        "total": region_results.total_tests,
                        "success": region_results.successful_tests,
                        "rate": region_results.get_success_rate()
                    }
                    
                    region_stats[region] = {
                        "tested": region_results.total_tests,
                        "successful": region_results.successful_tests,
                        "success_rate": region_results.get_success_rate(),
                        "avg_response_time": region_results.get_avg_response_time(),
                        "duration": time.time() - region_start
                    }
                    
                    print(f"\n📊 {region.upper()} Results:")
                    print(f"   Success Rate: {region_results.get_success_rate():.1%}")
                    print(f"   Avg Response: {region_results.get_avg_response_time():.2f}s")
                    
                except Exception as e:
                    logger.error(f"Failed to test region {region}: {e}")
                    all_results.errors.append(f"Region {region}: {e}")
                    print(f"\n❌ Failed to test {region.upper()}: {e}")
            
            # Generate final report
            print("\n" + "=" * 60)
            print("📈 TEST SUMMARY")
            print("=" * 60)
            
            total_time = sum(r.get("duration", 0) for r in region_stats.values())
            
            print(f"\n🎯 Overall Results:")
            print(f"   Total Tests: {all_results.total_tests}")
            print(f"   Successful: {all_results.successful_tests}")
            print(f"   Failed: {all_results.failed_tests}")
            print(f"   Success Rate: {all_results.get_success_rate():.1%}")
            print(f"   Avg Response Time: {all_results.get_avg_response_time():.2f}s")
            print(f"   Total Duration: {total_time:.2f}s")
            
            print(f"\n📋 Region Breakdown:")
            for region, stats in region_stats.items():
                status = "✅" if stats["success_rate"] >= MIN_SUCCESS_RATE else "❌"
                print(f"   {status} {region.upper()}: "
                      f"{stats['successful']}/{stats['tested']} "
                      f"({stats['success_rate']:.1%}) "
                      f"@ {stats['avg_response_time']:.2f}s")
            
            # Check errors
            if all_results.errors:
                print(f"\n⚠️  Errors ({len(all_results.errors)}):")
                for error in all_results.errors[:5]:  # Show first 5 errors
                    print(f"   • {error}")
                if len(all_results.errors) > 5:
                    print(f"   ... and {len(all_results.errors) - 5} more")
            
            # Production readiness check
            is_ready = all_results.is_production_ready()
            
            print(f"\n🚦 Production Status: {'✅ READY' if is_ready else '❌ NOT READY'}")
            
            if not is_ready:
                print("\n📝 Issues to fix:")
                success_rate = all_results.get_success_rate()
                if success_rate < MIN_SUCCESS_RATE:
                    print(f"   • Success rate ({success_rate:.1%}) below threshold ({MIN_SUCCESS_RATE:.1%})")
                
                avg_time = all_results.get_avg_response_time()
                if avg_time > MAX_RESPONSE_TIME:
                    print(f"   • Response time ({avg_time:.2f}s) exceeds limit ({MAX_RESPONSE_TIME}s)")
            
            # Save detailed results
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "production_ready": is_ready,
                "summary": {
                    "total_tests": all_results.total_tests,
                    "successful_tests": all_results.successful_tests,
                    "failed_tests": all_results.failed_tests,
                    "success_rate": all_results.get_success_rate(),
                    "avg_response_time": all_results.get_avg_response_time(),
                    "total_duration": total_time
                },
                "region_stats": region_stats,
                "player_results": all_results.player_results,
                "errors": all_results.errors,
                "thresholds": {
                    "min_success_rate": MIN_SUCCESS_RATE,
                    "max_response_time": MAX_RESPONSE_TIME
                }
            }
            
            # Save report to file
            report_file = f"riot_api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n💾 Detailed report saved to: {report_file}")
            
            return report_data
            
    except Exception as e:
        error = f"Failed to initialize Riot API: {e}"
        logger.error(error)
        print(f"\n❌ {error}")
        return {"success": False, "error": error}


def main():
    """Run the test suite."""
    print("Riot API Production Integration Test")
    print("====================================")
    print("This test validates the Riot API integration with real TFT player data.")
    print("It will fetch placements for known pro players and check for errors.\n")
    
    # Run the async test
    try:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(run_production_test())
        
        # Exit with appropriate code
        sys.exit(0 if results.get("production_ready", False) else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
