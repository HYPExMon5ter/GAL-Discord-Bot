"""
Placement Validator - Validates extracted placement data against TFT rules.

Ensures data integrity: 8 players, unique placements, valid lobbies, etc.
"""

from typing import Dict, List, Tuple
import logging

from config import _FULL_CFG

log = logging.getLogger(__name__)

# TFT-specific validation rules
PLAYERS_PER_LOBBY = 8
VALID_PLACEMENTS = set(range(1, 9))  # 1-8


class PlacementValidator:
    """Validates placement data against TFT tournament rules."""

    def __init__(self):
        config = _FULL_CFG
        settings = config.get("standings_screenshots", {})

        self.expected_lobbies = settings.get("expected_lobbies", 4)
        self.players_per_lobby = settings.get("players_per_lobby", 8)
        self.strict_validation = settings.get("strict_validation", True)

        log.info(
            f"Validator initialized (lobbies: {self.expected_lobbies}, "
            f"players: {self.players_per_lobby}, strict: {self.strict_validation})"
        )

    def validate_single_lobby(
        self,
        players: List[Dict],
        lobby_number: int
    ) -> Dict:
        """
        Validate extracted data for a single lobby.

        Args:
            players: List of player data with placement and name
            lobby_number: Lobby identifier

        Returns:
            Validation result with score and issues
        """
        issues = []
        score = 1.0

        # Validation 1: Player count
        if len(players) != self.players_per_lobby:
            issues.append({
                "type": "wrong_player_count",
                "expected": self.players_per_lobby,
                "actual": len(players),
                "severity": "error"
            })
            score -= 0.3

        # Validation 2: All players have placement
        for i, player in enumerate(players):
            if "placement" not in player:
                issues.append({
                    "type": "missing_placement",
                    "player": player.get("name", f"Unknown_{i}"),
                    "severity": "error"
                })
                score -= 0.1

        # Validation 3: All players have name
        for i, player in enumerate(players):
            if not player.get("name"):
                issues.append({
                    "type": "missing_name",
                    "player": f"Player_{i}",
                    "severity": "error"
                })
                score -= 0.1

        # Validation 4: Placements are valid (1-8)
        placements = [p.get("placement") for p in players if "placement" in p]
        for placement in placements:
            if placement not in VALID_PLACEMENTS:
                issues.append({
                    "type": "invalid_placement",
                    "placement": placement,
                    "severity": "error"
                })
                score -= 0.2

        # Validation 5: No duplicate placements
        placement_counts = {}
        for placement in placements:
            placement_counts[placement] = placement_counts.get(placement, 0) + 1

        for placement, count in placement_counts.items():
            if count > 1:
                issues.append({
                    "type": "duplicate_placement",
                    "placement": placement,
                    "count": count,
                    "severity": "error"
                })
                score -= 0.2

        # Validation 6: No duplicate player names
        names = [p.get("name", "").lower().strip() for p in players]
        name_counts = {}
        for name in names:
            name_counts[name] = name_counts.get(name, 0) + 1

        for name, count in name_counts.items():
            if count > 1:
                issues.append({
                    "type": "duplicate_player",
                    "name": name,
                    "count": count,
                    "severity": "error"
                })
                score -= 0.2

        # Validation 7: All placements present (1-8)
        present_placements = set(placements)
        missing_placements = VALID_PLACEMENTS - present_placements

        if missing_placements and self.strict_validation:
            issues.append({
                "type": "missing_placements",
                "missing": sorted(list(missing_placements)),
                "severity": "error"
            })
            score -= 0.1 * len(missing_placements)

        # Ensure score doesn't go below 0
        score = max(0, score)

        is_valid = score >= 0.7  # 70% threshold

        log.info(
            f"Lobby {lobby_number} validation: {'PASS' if is_valid else 'FAIL'} "
            f"(score: {score:.3f}, issues: {len(issues)})"
        )

        return {
            "valid": is_valid,
            "score": score,
            "lobby_number": lobby_number,
            "issues": issues,
            "player_count": len(players)
        }

    def validate_cross_lobby(
        self,
        lobbies: List[Dict]
    ) -> Dict:
        """
        Validate data across multiple lobbies for a round.

        Args:
            lobbies: List of lobby data with players

        Returns:
            Cross-lobby validation result
        """
        issues = []
        score = 1.0

        # Flatten all players across all lobbies
        all_players = []
        for lobby in lobbies:
            all_players.extend(lobby.get("players", []))

        # Validation 1: Expected lobby count
        if len(lobbies) != self.expected_lobbies:
            issues.append({
                "type": "wrong_lobby_count",
                "expected": self.expected_lobbies,
                "actual": len(lobbies),
                "severity": "warning"  # Not an error, could be partial round
            })
            score -= 0.1

        # Validation 2: No player in multiple lobbies
        player_lobbies = {}
        for player in all_players:
            player_name = player.get("name", "").lower().strip()
            lobby_num = player.get("lobby_number")

            if player_name in player_lobbies:
                issues.append({
                    "type": "player_in_multiple_lobbies",
                    "player": player_name,
                    "lobbies": [player_lobbies[player_name], lobby_num],
                    "severity": "error"
                })
                score -= 0.2
            else:
                player_lobbies[player_name] = lobby_num

        # Validation 3: Total player count
        total_players = len(all_players)
        expected_total = self.expected_lobbies * self.players_per_lobby

        if total_players != expected_total:
            issues.append({
                "type": "wrong_total_players",
                "expected": expected_total,
                "actual": total_players,
                "severity": "error"
            })
            score -= 0.15

        # Validation 4: All placements accounted for across lobbies
        all_placements = []
        for player in all_players:
            placement = player.get("placement")
            if placement:
                all_placements.append(placement)

        # Each placement (1-8) should appear exactly N times across M lobbies
        placement_counts = {}
        for placement in all_placements:
            placement_counts[placement] = placement_counts.get(placement, 0) + 1

        for placement, count in placement_counts.items():
            expected_count = len(lobbies)  # Each placement appears once per lobby
            if count != expected_count and self.strict_validation:
                issues.append({
                    "type": "placement_count_mismatch",
                    "placement": placement,
                    "expected": expected_count,
                    "actual": count,
                    "severity": "error"
                })
                score -= 0.1

        # Ensure score doesn't go below 0
        score = max(0, score)

        is_valid = score >= 0.7

        log.info(
            f"Cross-lobby validation: {'PASS' if is_valid else 'FAIL'} "
            f"(score: {score:.3f}, issues: {len(issues)})"
        )

        return {
            "valid": is_valid,
            "score": score,
            "issues": issues,
            "lobby_count": len(lobbies),
            "total_players": total_players
        }

    def validate_player_match_confidence(
        self,
        matched_players: List[Dict]
    ) -> Dict:
        """
        Validate that all players were matched to roster with good confidence.

        Args:
            matched_players: List of players with match results

        Returns:
            Match confidence validation result
        """
        issues = []
        score = 1.0

        # Check for unmatched players
        unmatched = [
            p for p in matched_players
            if not p.get("match_result", {}).get("success", False)
        ]

        if unmatched:
            issues.append({
                "type": "unmatched_players",
                "count": len(unmatched),
                "players": [p.get("name") for p in unmatched],
                "severity": "error"
            })
            score -= 0.3 * len(unmatched)

        # Check for low confidence matches
        low_confidence = [
            p for p in matched_players
            if p.get("match_confidence", 0) < 0.90
        ]

        if low_confidence and self.strict_validation:
            issues.append({
                "type": "low_confidence_matches",
                "count": len(low_confidence),
                "players": [p.get("name") for p in low_confidence],
                "severity": "warning"
            })
            score -= 0.1 * len(low_confidence)

        # Calculate average match confidence
        confidences = [
            p.get("match_confidence", 0)
            for p in matched_players
            if p.get("match_confidence") is not None
        ]

        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            if avg_confidence < 0.90:
                issues.append({
                    "type": "low_average_confidence",
                    "average": avg_confidence,
                    "threshold": 0.90,
                    "severity": "warning"
                })
                score -= 0.1

        # Ensure score doesn't go below 0
        score = max(0, score)

        is_valid = score >= 0.7

        log.info(
            f"Player match validation: {'PASS' if is_valid else 'FAIL'} "
            f"(score: {score:.3f}, issues: {len(issues)})"
        )

        # Calculate average confidence manually (avg function not defined)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "valid": is_valid,
            "score": score,
            "issues": issues,
            "unmatched_count": len(unmatched),
            "average_confidence": avg_confidence
        }


# Singleton instance
_validator_instance = None

def get_validator() -> PlacementValidator:
    """Get or create validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = PlacementValidator()
    return _validator_instance
