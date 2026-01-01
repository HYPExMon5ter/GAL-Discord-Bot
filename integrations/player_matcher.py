"""
Player Matching Engine - Matches extracted names to registered tournament players.

Uses exact matching, alias lookup, and fuzzy matching with character confusion handling.
"""

import re
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
import logging

from config import _FULL_CFG

log = logging.getLogger(__name__)

# Common character confusions in OCR
CHARACTER_CONFUSIONS = {
    '1': ['l', 'I', '|'],
    'l': ['1', 'I', '|'],
    'I': ['1', 'l', '|'],
    '0': ['O', 'o'],
    'O': ['0', 'o'],
    '5': ['S', 's'],
    'S': ['5', 's'],
    '8': ['B'],
    'B': ['8'],
    'rn': ['m'],
    'm': ['rn'],
}


class PlayerMatcher:
    """Matches extracted player names to registered players."""

    def __init__(self, player_roster: Optional[List[Dict]] = None):
        config = _FULL_CFG
        settings = config.get("standings_screenshots", {})

        self.threshold = settings.get("player_match_threshold", 0.95)
        self.player_roster = player_roster or []
        self.aliases = self._build_alias_index()

        log.info(
            f"Player Matcher initialized (threshold: {self.threshold}, "
            f"roster size: {len(self.player_roster)})"
        )

    def _build_alias_index(self) -> Dict[str, Dict]:
        """Build index of player aliases for fast lookup."""
        alias_index = {}

        for player in self.player_roster:
            player_id = player.get("player_id") or player.get("discord_id")
            player_name = player.get("player_name") or player.get("riot_id") or ""

            # Add canonical name
            alias_index[self._normalize(player_name)] = {
                "player_id": player_id,
                "player_name": player_name,
                "type": "canonical",
                "priority": 10
            }

            # Add Riot IGN
            riot_id = player.get("riot_id")
            if riot_id and riot_id != player_name:
                alias_index[self._normalize(riot_id)] = {
                    "player_id": player_id,
                    "player_name": player_name,
                    "type": "ign",
                    "priority": 8
                }

            # Add Discord username
            discord_name = player.get("discord_name")
            if discord_name:
                alias_index[self._normalize(discord_name)] = {
                    "player_id": player_id,
                    "player_name": player_name,
                    "type": "discord_name",
                    "priority": 7
                }

            # Add registered aliases (if available)
            for alias in player.get("aliases", []):
                alias_index[self._normalize(alias)] = {
                    "player_id": player_id,
                    "player_name": player_name,
                    "type": "alias",
                    "priority": 6
                }

        log.info(f"Built alias index with {len(alias_index)} entries")
        return alias_index

    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        # Remove special characters
        text = re.sub(r'[^a-zA-Z0-9]', '', text)

        # Convert to lowercase
        text = text.lower()

        # Remove extra spaces
        text = re.sub(r'\s+', '', text)

        # Handle common OCR confusions
        for correct_char, confused_chars in CHARACTER_CONFUSIONS.items():
            for confused in confused_chars:
                text = text.replace(confused, correct_char)

        return text

    def match_player(
        self,
        extracted_name: str,
        fallback_to_fuzzy: bool = True
    ) -> Dict:
        """
        Match extracted name to registered player.

        Args:
            extracted_name: Name from OCR extraction
            fallback_to_fuzzy: Use fuzzy matching if exact/alias fails

        Returns:
            Dictionary with match result and confidence
        """
        normalized_extracted = self._normalize(extracted_name)

        # Tier 1: Exact match (via normalization)
        if normalized_extracted in self.aliases:
            match = self.aliases[normalized_extracted]
            log.info(f"Exact match found: '{extracted_name}' -> {match['player_name']}")

            return {
                "success": True,
                "player_id": match["player_id"],
                "matched_name": match["player_name"],
                "match_method": "exact",
                "match_type": match["type"],
                "confidence": 1.0,
                "original_text": extracted_name
            }

        # Tier 2: Case-insensitive exact match
        for alias, match in self.aliases.items():
            if alias == normalized_extracted:
                log.info(f"Case-insensitive match: '{extracted_name}' -> {match['player_name']}")

                return {
                    "success": True,
                    "player_id": match["player_id"],
                    "matched_name": match["player_name"],
                    "match_method": "case_insensitive",
                    "match_type": match["type"],
                    "confidence": 0.99,
                    "original_text": extracted_name
                }

        # Tier 3: Fuzzy match
        if fallback_to_fuzzy:
            return self._fuzzy_match(extracted_name, normalized_extracted)

        # No match found
        log.warning(f"No match found for: '{extracted_name}'")
        return {
            "success": False,
            "player_id": None,
            "matched_name": None,
            "match_method": "none",
            "match_type": None,
            "confidence": 0.0,
            "original_text": extracted_name
        }

    def _fuzzy_match(
        self,
        original_text: str,
        normalized_text: str
    ) -> Dict:
        """Perform fuzzy matching against player roster."""
        # Build list of candidate names
        candidates = []

        for player in self.player_roster:
            player_name = player.get("player_name") or player.get("riot_id") or ""

            # Add canonical name
            candidates.append({
                "player_id": player.get("player_id"),
                "player_name": player_name,
                "search_text": self._normalize(player_name),
                "type": "canonical"
            })

            # Add aliases
            for alias in player.get("aliases", []):
                candidates.append({
                    "player_id": player.get("player_id"),
                    "player_name": player_name,
                    "search_text": self._normalize(alias),
                    "type": "alias"
                })

        if not candidates:
            return {
                "success": False,
                "player_id": None,
                "matched_name": None,
                "match_method": "none",
                "confidence": 0.0,
                "original_text": original_text
            }

        # Perform fuzzy matching
        # Use weighted ratio (partial ratio)
        result = process.extractOne(
            normalized_text,
            [c["search_text"] for c in candidates],
            scorer=fuzz.WRatio
        )

        if result:
            score = result[1] / 100  # Normalize to 0-1
            best_match = candidates[result[2]]

            log.info(
                f"Fuzzy match: '{original_text}' -> {best_match['player_name']} "
                f"(confidence: {score:.3f})"
            )

            if score >= self.threshold:
                return {
                    "success": True,
                    "player_id": best_match["player_id"],
                    "matched_name": best_match["player_name"],
                    "match_method": "fuzzy",
                    "match_type": best_match["type"],
                    "confidence": score,
                    "original_text": original_text
                }
            else:
                log.warning(
                    f"Fuzzy match below threshold: '{original_text}' -> "
                    f"{best_match['player_name']} (score: {score:.3f}, threshold: {self.threshold})"
                )
                return {
                    "success": False,
                    "player_id": None,
                    "matched_name": best_match["player_name"],
                    "match_method": "fuzzy_low_confidence",
                    "match_type": best_match["type"],
                    "confidence": score,
                    "original_text": original_text
                }

        return {
            "success": False,
            "player_id": None,
            "matched_name": None,
            "match_method": "none",
            "confidence": 0.0,
            "original_text": original_text
        }

    def match_players(
        self,
        extracted_players: List[Dict],
        fallback_to_fuzzy: bool = True
    ) -> List[Dict]:
        """
        Match multiple extracted players to roster.

        Args:
            extracted_players: List of extracted player data
            fallback_to_fuzzy: Use fuzzy matching

        Returns:
            List of match results
        """
        results = []

        for player_data in extracted_players:
            extracted_name = player_data.get("name", "")

            if not extracted_name:
                continue

            # Attempt match
            match_result = self.match_player(extracted_name, fallback_to_fuzzy)

            # Combine with original player data
            combined = {
                **player_data,
                "match_result": match_result,
                "matched_player": match_result["matched_name"] if match_result["success"] else None,
                "matched_player_id": match_result["player_id"] if match_result["success"] else None,
                "match_confidence": match_result["confidence"],
                "match_method": match_result["match_method"]
            }

            results.append(combined)

        return results

    def update_roster(self, new_players: List[Dict]):
        """Update player roster with new players."""
        self.player_roster.extend(new_players)
        self.aliases = self._build_alias_index()
        log.info(f"Updated roster (new size: {len(self.player_roster)})")


# Singleton instance
_matcher_instance = None

def get_player_matcher(
    player_roster: Optional[List[Dict]] = None
) -> PlayerMatcher:
    """Get or create player matcher instance."""
    global _matcher_instance
    if _matcher_instance is None or player_roster:
        _matcher_instance = PlayerMatcher(player_roster)
    return _matcher_instance
