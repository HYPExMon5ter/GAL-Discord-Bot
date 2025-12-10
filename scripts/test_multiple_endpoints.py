#!/usr/bin/env python3
"""
Test Riot API with multiple endpoints to diagnose the issue
"""

import asyncio
import aiohttp
import os
import sys
from dotenv import load_dotenv

# Load .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

api_key = os.getenv('RIOT_API_KEY')
print(f"API Key: {api_key[:10]}...{api_key[-10:] if api_key else 'NOT FOUND'}")

async def test_endpoints():
    headers = {"X-Riot-Token": api_key}
    
    # Test 1: Account API
    print("\n1. Testing Account API...")
    account_url = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Dishsoap/NA1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(account_url, headers=headers) as response:
            print(f"   Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"   SUCCESS: {data.get('gameName')}#{data.get('tagLine')}")
                print("   Account API works!")
                return True
            else:
                error = await response.text()
                print(f"   ERROR: {error[:50]}")
    
    # Test 2: Summoner API (NA1)
    print("\n2. Testing Summoner API (NA1)...")
    summoner_url = "https://na1.api.riotgames.com/tft/summoner/v1/summoners/by-name/Dishsoap"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(summoner_url, headers=headers) as response:
            print(f"   Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"   SUCCESS: Level {data.get('summonerLevel')} summoner")
                print("   Summoner API works!")
                return True
            else:
                error = await response.text()
                print(f"   ERROR: {error[:50]}")
    
    # Test 3: Try with a different player
    print("\n3. Testing with 'Milk' (another pro player)...")
    account_url2 = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/milk/NA1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(account_url2, headers=headers) as response:
            print(f"   Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"   SUCCESS: {data.get('gameName')}#{data.get('tagLine')}")
                print("   API works with different player!")
                return True
            else:
                error = await response.text()
                print(f"   ERROR: {error[:50]}")
    
    # Test 4: Try match-v1 endpoint (deprecated but sometimes works)
    print("\n4. Testing deprecated match-v1 endpoint...")
    match_url = "https://na1.api.riotgames.com/tft/match/v1/matches/by-puuid/test"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(match_url, headers=headers) as response:
            print(f"   Status: {response.status}")
            if response.status == 401:
                error = await response.text()
                print(f"   Expected error: {error[:50]}")
    
    print("\n" + "=" * 50)
    print("DIAGNOSIS COMPLETE")
    print("=" * 50)
    
    print("\nIf ALL tests failed with 401, the API key is definitely invalid.")
    print("\nNext steps:")
    print("1. Go to https://developer.riotgames.com")
    print("2. Check your API key in the API Keys section")
    print("3. Make sure it's associated with a product")
    print("4. Regenerate if necessary")
    print("5. Wait 1-2 minutes after regeneration")
    print("6. Update .env file")
    
    return False


if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_endpoints())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
