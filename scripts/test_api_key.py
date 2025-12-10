#!/usr/bin/env python3
"""
Simple Riot API Key Test (Windows compatible)
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

print("Loading .env from:", env_path)
print("Riot API Key loaded:", bool(os.getenv('RIOT_API_KEY')))


async def test_api():
    api_key = os.getenv('RIOT_API_KEY')
    
    if not api_key:
        print("ERROR: RIOT_API_KEY not found!")
        return False
        
    print(f"API Key length: {len(api_key)}")
    print(f"Starts with RGAPI: {api_key.startswith('RGAPI')}")
    
    headers = {"X-Riot-Token": api_key}
    url = "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Dishsoap/NA1"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"\nStatus Code: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"SUCCESS! Found player: {data.get('gameName')}#{data.get('tagLine')}")
                    print(f"API key is VALID!")
                    return True
                elif response.status == 401:
                    error = await response.text()
                    print(f"ERROR: 401 Unauthorized")
                    print(f"Response: {error[:100]}")
                    print("\nAPI key appears to be invalid")
                    return False
                else:
                    error = await response.text()
                    print(f"ERROR: Status {response.status}")
                    print(f"Response: {error[:100]}")
                    return False
                    
    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(test_api())
        
        if result:
            print("\n=== API KEY IS VALID ===")
            print("\nYou can now run:")
            print("  python scripts/test_riot_simple.py")
            print("  python scripts/test_infrastructure.py")
        else:
            print("\n=== API KEY IS INVALID ===")
            print("\nPlease:")
            print("1. Get a new key from https://developer.riotgames.com")
            print("2. Update .env file")
            print("3. Try again")
            
        sys.exit(0 if result else 1)
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
