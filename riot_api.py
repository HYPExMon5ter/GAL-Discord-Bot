# gal_discord_bot/riot_api.py

import urllib.parse

import requests

from config import RIOT_API_KEY

RIOT_API_REGION = "na1"
TFT_REGION = "americas"

def riot_headers():
    return {"X-Riot-Token": RIOT_API_KEY}

def sanitize_riot_ign(ign):
    # Remove everything after '#' (e.g., "Setts Tiddies#NA1" => "Setts Tiddies")
    return ign.split("#")[0].strip()

def get_summoner_info(ign):
    clean_ign = sanitize_riot_ign(ign)
    url_ign = urllib.parse.quote(clean_ign)
    url = f"https://{RIOT_API_REGION}.api.riotgames.com/tft/summoner/v1/summoners/by-name/{url_ign}"
    r = requests.get(url, headers=riot_headers())
    if r.status_code == 200:
        return r.json()
    return None

def get_latest_tft_placement(puuid):
    matchlist_url = f"https://{TFT_REGION}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count=1"
    r = requests.get(matchlist_url, headers=riot_headers())
    if r.status_code != 200 or not r.json():
        return None
    match_id = r.json()[0]
    match_url = f"https://{TFT_REGION}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    r2 = requests.get(match_url, headers=riot_headers())
    if r2.status_code != 200:
        return None
    match = r2.json()
    for participant in match["info"]["participants"]:
        if participant["puuid"] == puuid:
            return participant.get("placement")
    return None