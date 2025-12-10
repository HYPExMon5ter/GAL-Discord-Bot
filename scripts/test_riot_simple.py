#!/usr/bin/env python3
"""
Simple Riot API Test for Windows

Tests the Riot API integration with basic text output for Windows compatibility.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.riot_api import RiotAPI

# Test players (subset for quick test)
TEST_PLAYERS = [
    {"name": "Dishsoap", "riot_id": "Dishsoap#NA1"},
    {"name": "K3soju", "riot_id": "K3soju#NA1"},
    {"name": "Roux", "riot_id": "Roux#NA1"}
]


async def test_riot_api():
    """Test basic Riot API functionality."""
    print("Riot API Test")
    print("=============")
    
    # Check API key
    api_key = os.getenv("RIOT_API_KEY")
    if not api_key:
        print("ERROR: RIOT_API_KEY environment variable not set!")
        return False
        
    print("API key found")
    
    # Test with players
    success_count = 0
    total_count = len(TEST_PLAYERS)
    
    try:
        async with RiotAPI() as riot_api:
            print("\nTesting players...")
            
            for player in TEST_PLAYERS:
                print(f"\nTesting {player['name']} ({player['riot_id']})...")
                
                try:
                    result = await riot_api.get_latest_placement("na", player["riot_id"])
                    
                    if result.get("success"):
                        placement = result.get("placement")
                        print(f"  SUCCESS: Placement {placement}")
                        success_count += 1
                    else:
                        error = result.get("error", "Unknown error")
                        print(f"  FAILED: {error}")
                        
                except Exception as e:
                    print(f"  ERROR: {str(e)}")
                    
                # Small delay to respect rate limits
                await asyncio.sleep(0.5)
                
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        return False
        
    # Summary
    print(f"\nResults:")
    print(f"--------")
    print(f"Successful: {success_count}/{total_count}")
    print(f"Success Rate: {success_count/total_count*100:.1f}%")
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_players": total_count,
        "successful": success_count,
        "success_rate": success_count/total_count,
        "production_ready": success_count/total_count >= 0.8
    }
    
    report_file = f"riot_api_simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nReport saved to: {report_file}")
    print(f"Production Ready: {'YES' if report['production_ready'] else 'NO'}")
    
    return report["production_ready"]


def main():
    """Run the test."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(test_riot_api())
        sys.exit(0 if result else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(2)
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
