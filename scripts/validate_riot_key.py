#!/usr/bin/env python3
"""
Validate Riot API Key

Tests the Riot API key directly to diagnose authentication issues.
"""

import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

print(f"Loading .env from: {env_path}")
print(f".env exists: {os.path.exists(env_path)}")


async def validate_key():
    """Validate the Riot API key with a simple test call."""
    print("\n" + "=" * 50)
    print("RIOT API KEY VALIDATION")
    print("=" * 50)
    
    api_key = os.getenv('RIOT_API_KEY')
    
    if not api_key:
        print("❌ ERROR: RIOT_API_KEY not found in environment")
        print("\nTroubleshooting:")
        print("1. Check that .env file exists in project root")
        print("2. Ensure RIOT_API_KEY=RGAPI-xxxx is in .env file")
        print("3. Verify no extra spaces in the key")
        return False
        
    print(f"✅ API Key found: {len(api_key)} characters")
    print(f"✅ Starts with 'RGAPI': {api_key.startswith('RGAPI')}")
    print(f"✅ Ends correctly: {api_key.endswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))}")
    
    # Test API key format
    if len(api_key) != 42:
        print(f"⚠️  WARNING: API key length is {len(api_key)} (expected 42)")
    
    # Test with a simple API call
    print("\n" + "-" * 50)
    print("TESTING API CALL")
    print("-" * 50)
    
    headers = {"X-Riot-Token": api_key}
    
    # Try to get account info for Dishsoap
    url = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Dishsoap/NA1"
    print(f"Testing endpoint: {url}")
    
    start_time = asyncio.get_event_loop().time()
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                duration = asyncio.get_event_loop().time() - start_time
                print(f"Response time: {duration:.2f}s")
                
                print(f"\nStatus Code: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ SUCCESS! Found player: {data.get('gameName')}#{data.get('tagLine')}")
                    print(f"✅ PUUID: {data.get('puuid')[:20]}...")
                    print(f"✅ Account created: {data.get('createdAt')}")
                    return True
                    
                elif response.status == 401:
                    error_text = await response.text()
                    print(f"❌ ERROR: 401 Unauthorized")
                    print(f"Response: {error_text}")
                    
                    print(f"\n📋 Possible causes:")
                    print(f"   1. API key is expired or invalid")
                    print(f"   2. API key was just regenerated (wait 1-2 minutes)")
                    print(f"   3. API key copied with extra characters")
                    print(f"   4. Developer console products not properly configured")
                    
                    # Provide curl command for testing
                    print(f"\n💡 Test with curl:")
                    print(f'curl -H "X-Riot-Token: {api_key[:10]}..." \\\\n     "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Dishsoap/NA1"')
                    
                    return False
                    
                elif response.status == 404:
                    error_text = await response.text()
                    print(f"⚠️  WARNING: 404 Not Found")
                    print(f"Response: {error_text}")
                    print(f"\nNote: This might mean the player changed their Riot ID")
                    print(f"The API key might still be valid. Testing with another endpoint...")
                    
                    # Try a different endpoint
                    print(f"\nTrying summoner lookup...")
                    summoner_url = "https://na1.api.riotgames.com/tft/summoner/v1/summoners/by-name/Dishsoap"
                    
                    async with session.get(summoner_url, headers=headers) as resp:
                        print(f"Summoner lookup status: {resp.status}")
                        if resp.status == 200:
                            summoner_data = await resp.json()
                            print(f"✅ Summoner found: Level {summoner_data.get('summonerLevel')}")
                            print("API key appears to be valid!")
                            return True
                        else:
                            print(f"❌ Summoner lookup also failed")
                            return False
                    
                else:
                    error_text = await response.text()
                    print(f"❌ ERROR: Status {response.status}")
                    print(f"Response: {error_text}")
                    return False
                    
        except aiohttp.ClientError as e:
            print(f"❌ Network error: {e}")
            print("\nTroubleshooting:")
            print("1. Check internet connection")
            print("2. Verify firewall allows API calls")
            print("3. Try again in a few minutes")
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False


def check_env_loading():
    """Check if environment is loading correctly."""
    print("\n" + "=" * 50)
    print("ENVIRONMENT CHECK")
    print("=" * 50)
    
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"Parent directory: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    
    print("\nChecking for .env file...")
    locations = [
        ".env",
        "../.env",
        "../../.env",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    ]
    
    for location in locations:
        full_path = os.path.abspath(location)
        exists = os.path.exists(full_path)
        print(f"  {location}: {'✅' if exists else '❌'} {full_path}")


async def main():
    """Run validation."""
    check_env_loading()
    
    result = await validate_key()
    
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    if result:
        print("✅ API key is VALID and working!")
        print("\nYou can now run the full test suite:")
        print("  python scripts/test_riot_simple.py")
        print("  python scripts/test_scoreboard_api.py")
        print("  python scripts/production_dry_run.py")
    else:
        print("❌ API key is INVALID or not working!")
        print("\nNext steps:")
        print("1. Go to https://developer.riotgames.com")
        print("2. Generate a new API key")
        print("3. Update .env file with the new key")
        print("4. Wait 1-2 minutes if key was just generated")
        print("5. Run this script again: python scripts/validate_riot_key.py")
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_key_valid": result,
        "validation_time": datetime.now().isoformat()
    }
    
    report_file = f"riot_key_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        import json
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to: {report_file}")
    
    return result


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Validation interrupted")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)
