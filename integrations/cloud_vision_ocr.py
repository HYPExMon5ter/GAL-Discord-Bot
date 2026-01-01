"""
Google Cloud Vision API OCR Engine for TFT Screenshots

Simple, accurate, and production-ready OCR using Google's Vision API.
Replaces complex PaddleOCR/Tesseract multi-engine preprocessing pipelines.

Cost: $1.50 per 1,000 images (first 1,000/month FREE)
For 16 images/month: $0.024/month (~2.4 cents) - under free tier
"""

import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import os

from google.cloud import vision
from google.api_core import exceptions as google_exceptions

from config import _FULL_CFG

log = logging.getLogger(__name__)

# TFT placement points mapping
PLACEMENT_POINTS = {
    1: 8, 2: 7, 3: 6, 4: 5,
    5: 4, 6: 3, 7: 2, 8: 1
}


class CloudVisionOCR:
    """Google Cloud Vision API OCR engine for TFT screenshots."""
    
    def __init__(self):
        """Initialize Cloud Vision client."""
        config = _FULL_CFG
        settings = config.get("standings_screenshots", {})
        
        self.timeout_seconds = settings.get("timeout_seconds", 30)
        self.focus_left_side = settings.get("focus_left_side", True)
        self.left_crop_percent = settings.get("left_crop_percent", 0.5)
        
        # Initialize Vision API client
        # Credentials are loaded from GOOGLE_APPLICATION_CREDENTIALS environment variable
        # or from Railway/deployment environment
        try:
            self.client = vision.ImageAnnotatorClient()
            log.info("Google Cloud Vision API client initialized")
        except Exception as e:
            log.error(f"Failed to initialize Vision API client: {e}")
            raise
    
    def extract_from_image(self, image_path: str) -> Dict:
        """
        Extract TFT standings data from screenshot using Cloud Vision API.
        
        Args:
            image_path: Path to screenshot image file
            
        Returns:
            Dictionary with structured data, raw results, and success status
        """
        try:
            # Read image file
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            with open(image_path, 'rb') as f:
                content = f.read()
            
            # Create Vision API image object
            image = vision.Image(content=content)
            
            # Call Vision API for text detection
            log.info(f"Calling Cloud Vision API for: {Path(image_path).name}")
            response = self.client.text_detection(image=image)
            
            # Check for API errors
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            # Parse text annotations
            text_annotations = response.text_annotations
            
            # Extract bounding boxes and text
            raw_detections = self._parse_annotations(text_annotations)
            
            # Merge adjacent text items for multi-word names
            raw_detections = self._merge_adjacent_text(raw_detections)
            
            if not text_annotations or len(text_annotations) < 2:
                log.warning(f"No text detected in {image_path}")
                return {
                    "success": False,
                    "error": "No text detected",
                    "structured_data": {
                        "players": [],
                        "player_count": 0,
                        "expected_players": 8
                    }
                }
            
            # Structure data into TFT standings format
            structured = self._structure_tft_data(raw_detections, image_path)
            
            # Calculate confidence
            scores = self._calculate_confidence(raw_detections, structured)
            
            return {
                "structured_data": structured,
                "raw_results": raw_detections,
                "scores": scores,
                "success": True
            }
            
        except google_exceptions.GoogleAPIError as e:
            log.error(f"Google API error: {e}")
            return {
                "success": False,
                "error": f"Google API error: {str(e)}"
            }
        except Exception as e:
            log.error(f"OCR extraction error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_annotations(self, annotations: List) -> List[Dict]:
        """
        Parse Vision API text annotations into structured format.
        
        Args:
            annotations: List of TextAnnotation objects from Vision API
            
        Returns:
            List of detection dicts with text, bounding box, and confidence
        """
        detections = []
        
        # Skip first annotation (full page text)
        for annotation in annotations[1:]:
            text = annotation.description.strip()
            
            if not text:
                continue
            
            # Get bounding box
            vertices = annotation.bounding_poly.vertices
            
            # Calculate center and bounds
            x_coords = [v.x for v in vertices]
            y_coords = [v.y for v in vertices]
            
            x_min = min(x_coords)
            x_max = max(x_coords)
            y_min = min(y_coords)
            y_max = max(y_coords)
            
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2
            
            # Cloud Vision doesn't provide per-word confidence for text_detection
            # Use a default high confidence (Vision API is very accurate)
            confidence = 0.95
            
            detections.append({
                "text": text,
                "center_x": center_x,
                "center_y": center_y,
                "bbox": [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]],
                "confidence": confidence
            })
        
        # Sort by vertical position (top to bottom)
        detections.sort(key=lambda x: x["center_y"])
        
        # Merge adjacent text items (e.g., "Baby" + "Llama" -> "Baby Llama")
        detections = self._merge_adjacent_text(detections)
        
        return detections
    
    def _merge_adjacent_text(self, detections: List[Dict]) -> List[Dict]:
        """
        Merge adjacent text items that likely belong to one name.
        
        Examples:
        - "Baby" + "Llama" (same row, close) -> "Baby Llama"
        - "Matt" + "Green" (same row, close) -> "Matt Green"
        - "Lauren" + "TheCorgi" (same row, close) -> "LaurenTheCorgi"
        
        Args:
            detections: List of text detection dicts
            
        Returns:
            List with merged text items
        """
        if len(detections) < 2:
            return detections
        
        merged = []
        used_indices = set()
        
        for i, item1 in enumerate(detections):
            if i in used_indices:
                continue
            
            best_merge = None
            best_gap = float('inf')
            
            # Check for items that could be merged with this one
            for j, item2 in enumerate(detections):
                if i == j or j in used_indices:
                    continue
                
                # Calculate gap between items
                x_gap = abs(item2["center_x"] - item1["center_x"])
                y_gap = abs(item2["center_y"] - item1["center_y"])
                
                # MERGE CONDITIONS:
                # 1. Items must be on same row (Y gap < 15px)
                # 2. Items must be close horizontally (X gap < 150px)
                # 3. Items must be in left-to-right order (item2 is to the right of item1)
                # 4. Neither item should be a single digit (placement number)
                text1 = item1["text"].strip()
                text2 = item2["text"].strip()
                
                # Skip if either is a single digit (likely placement number)
                if text1.isdigit() or text2.isdigit():
                    continue
                
                # Skip if items are too far apart vertically
                if y_gap > 15:
                    continue
                
                # Skip if items are too far apart horizontally or in wrong order
                if x_gap > 200 or item2["center_x"] < item1["center_x"]:
                    continue
                
                # This is a potential merge
                # Prefer closest item with smallest total gap
                gap = x_gap * 0.3 + y_gap * 3.0
                if gap < best_gap:
                    best_gap = gap
                    best_merge = (j, x_gap, y_gap)
            
            # If we found a merge, combine text
            if best_merge:
                j, x_gap, y_gap = best_merge
                item2 = detections[j]
                
                # Determine order: leftmost first
                if item1["center_x"] < item2["center_x"]:
                    merged_text = f"{item1['text'].strip()}{item2['text'].strip()}"
                else:
                    merged_text = f"{item2['text'].strip()}{item1['text'].strip()}"
                
                # Calculate combined bounding box
                x1 = min(item1["bbox"][0][0], item2["bbox"][0][0])
                y1 = min(item1["bbox"][0][1], item2["bbox"][0][1])
                x2 = max(item1["bbox"][2][0], item2["bbox"][2][0])
                y2 = max(item1["bbox"][2][1], item2["bbox"][2][1])
                
                merged.append({
                    "text": merged_text,
                    "center_x": (x1 + x2) / 2,
                    "center_y": (y1 + y2) / 2,
                    "bbox": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                    "confidence": (item1["confidence"] + item2["confidence"]) / 2
                })
                
                used_indices.add(i)
                used_indices.add(j)
            else:
                # No merge found, keep original
                merged.append(item1)
                used_indices.add(i)
        
        # Sort merged items by Y position
        merged.sort(key=lambda x: x["center_y"])
        
        return merged
    
    def _structure_tft_data(self, detections: List[Dict], image_path: str) -> Dict:
        """
        Structure OCR detections into TFT standings format.
        
        Matches placement numbers (1-8) with player names based on position.
        
        Args:
            detections: List of text detection dicts
            image_path: Path to image (for width calculation if needed)
            
        Returns:
            Dict with players list and metadata
        """
        # Filter UI keywords that aren't player names
        skip_keywords = [
            'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
            'NORMAL', 'GAME', 'ONLINE', 'SUMMONER', 'ROUND',
            'CHAMPIONS', 'PLAY', 'AGAIN', 'CONTINUE', 'PLAYER',
            'SOCIAL', 'GENERAL', 'SQUAD', 'GameID'  # Skip sidebar/social area
        ]
        
        # Get image width to filter by position
        img_width = None
        try:
            img = cv2.imread(image_path)
            if img is not None:
                img_width = img.shape[1]  # width in pixels
                log.debug(f"Image width: {img_width}px")
        except:
            pass
        
        placements = []  # (placement_num, y_pos, x_pos)
        names = []  # (name, y_pos, x_pos)
        
        for item in detections:
            text = item["text"].strip()
            text_upper = text.upper()
            y_pos = item["center_y"]
            x_pos = item["center_x"]
            
            # Skip UI keywords
            if any(kw in text_upper for kw in skip_keywords):
                continue
            
            # Skip very short text (likely fragments), BUT allow single digits (placements 1-8)
            # Placement numbers are single characters like "1", "2", etc.
            if len(text) < 2 and not text.isdigit():
                continue
            
            # Check if this is a placement number (1-8)
            # Handle formats: "1", "#1", "1ST", "2ND", "3RD", "4TH-8TH"
            placement_num = self._extract_placement(text)
            
            if placement_num is not None:
                placements.append((placement_num, y_pos, x_pos))
                log.debug(f"Placement {placement_num} at ({x_pos:.0f}, {y_pos:.0f})")
                continue
            
            # Check if this looks like a player name
            # Must have at least 3 alpha characters and be 4-20 chars total
            alpha_count = sum(c.isalpha() for c in text)
            
            # DEBUG: Log filtering decisions for first few items
            if len(names) < 15:
                log.debug(f"  Text '{text}': len={len(text)}, alpha={alpha_count}, y={y_pos:.0f}")
            
            if alpha_count >= 3 and 4 <= len(text) <= 20:
                # Avoid duplicates (case insensitive)
                if not any(n[0].upper() == text_upper for n in names):
                    names.append((text, y_pos, x_pos))
                    log.debug(f"Name '{text}' at ({x_pos:.0f}, {y_pos:.0f})")
        
        log.info(f"Detected {len(placements)} placements and {len(names)} names")
        
        # DEBUG: Show what was collected
        log.debug(f"Placements collected: {placements}")
        log.debug(f"Names collected: {names}")
        
        # Match placements to names by vertical position
        players = self._match_placements_to_names(placements, names)
        
        return {
            "players": players,
            "player_count": len(players),
            "expected_players": 8
        }
    
    def _extract_placement(self, text: str) -> Optional[int]:
        """
        Extract placement number (1-8) from text.
        
        Handles formats:
        - "1" - "8" (single digit)
        - "#1" - "#8"
        - "1ST", "2ND", "3RD", "4TH-8TH"
        - "P1" - "P8"
        
        Args:
            text: Text string to parse
            
        Returns:
            Placement number (1-8) or None
        """
        text = text.strip().upper()
        
        # Single digit
        if text.isdigit() and 1 <= int(text) <= 8:
            return int(text)
        
        # #1 format
        if text.startswith('#') and len(text) >= 2:
            try:
                num = int(text[1:])
                if 1 <= num <= 8:
                    return num
            except ValueError:
                pass
        
        # P1 format (common in some TFT layouts)
        if text.startswith('P') and len(text) >= 2:
            try:
                num = int(text[1:])
                if 1 <= num <= 8:
                    return num
            except ValueError:
                pass
        
        # Ordinal format (1ST, 2ND, 3RD, 4TH-8TH)
        ordinals = {
            '1ST': 1, '2ND': 2, '3RD': 3, '4TH': 4,
            '5TH': 5, '6TH': 6, '7TH': 7, '8TH': 8
        }
        
        if text in ordinals:
            return ordinals[text]
        
        return None
    
    def _match_placements_to_names(
        self, 
        placements: List[Tuple[int, float, float]], 
        names: List[Tuple[str, float, float]]
    ) -> List[Dict]:
        """
        Match placement numbers to player names by position.
        
        Strategy:
        1. Sort both by Y position (top to bottom)
        2. For each placement, find closest unused name
        3. Strict requirements: name MUST be to the RIGHT of placement and close in Y
        
        Args:
            placements: List of (placement, y_pos, x_pos) tuples
            names: List of (name, y_pos, x_pos) tuples
            
        Returns:
            List of player dicts with placement, name, and points
        """
        players = []
        
        if not placements or not names:
            log.warning(f"Missing data: {len(placements)} placements, {len(names)} names")
            return players
        
        # Sort by Y position
        placements_sorted = sorted(placements, key=lambda x: x[1])
        names_sorted = sorted(names, key=lambda x: x[1])
        
        used_names = set()
        
        for placement_num, p_y, p_x in placements_sorted:
            best_name = None
            best_dist = float('inf')
            best_idx = -1
            
            for idx, (name, n_y, n_x) in enumerate(names_sorted):
                if idx in used_names:
                    continue
                
                # Calculate distances
                y_dist = abs(n_y - p_y)
                x_dist = abs(n_x - p_x)
                
                # REQUIREMENT: Name MUST be to the right of placement
                # In TFT screenshots, placements are on left, names on right
                # If name is to the left, it's probably from a different column
                if n_x <= p_x:
                    continue
                
                # REQUIREMENT: Minimum horizontal gap (at least 10px to the right)
                if n_x - p_x < 10:
                    continue
                
                # REQUIREMENT: Must be on same row (within 50px vertically)
                if y_dist > 50:
                    continue
                
                # DEBUG: Show why this name is being considered
                if placement_num == 1:  # Only for first placement
                    log.debug(f"  Considering name '{name} for placement {placement_num}: x_gap={n_x - p_x:.0f}, y_gap={y_dist:.0f}")
                
                # Weighted distance (Y is more important)
                dist = y_dist * 3.0 + x_dist * 0.3
                
                if dist < best_dist:
                    best_dist = dist
                    best_name = name
                    best_idx = idx
            
            if best_name and best_idx >= 0:
                players.append({
                    "placement": placement_num,
                    "name": best_name,
                    "points": PLACEMENT_POINTS.get(placement_num, 0)
                })
                used_names.add(best_idx)
                log.debug(f"Matched: {placement_num} -> {best_name}")
            else:
                log.warning(f"No name found for placement {placement_num}")
        
        # Sort by placement
        players.sort(key=lambda x: x["placement"])
        
        return players
    
    def _calculate_confidence(self, detections: List[Dict], structured: Dict) -> Dict:
        """
        Calculate confidence scores for extraction.
        
        Args:
            detections: Raw OCR detections
            structured: Structured TFT data
            
        Returns:
            Dict with confidence scores
        """
        scores = {}
        
        # 1. OCR confidence (Cloud Vision is consistently high)
        if detections:
            avg_conf = sum(d["confidence"] for d in detections) / len(detections)
            scores["character"] = avg_conf
            scores["ocr_consensus"] = avg_conf
        else:
            scores["character"] = 0.0
            scores["ocr_consensus"] = 0.0
        
        # 2. Structural confidence (correct number of players)
        player_count = structured.get("player_count", 0)
        expected = structured.get("expected_players", 8)
        
        if player_count == expected:
            scores["structural"] = 1.0
        elif player_count >= expected - 1:
            scores["structural"] = 0.9
        elif player_count >= expected - 2:
            scores["structural"] = 0.7
        else:
            scores["structural"] = max(0.3, player_count / expected)
        
        # 3. Overall confidence (weighted average)
        scores["overall"] = (
            scores["character"] * 0.4 +
            scores["structural"] * 0.6
        )
        
        return scores


# Singleton instance
_cloud_vision_instance = None


def get_cloud_vision_ocr() -> CloudVisionOCR:
    """Get singleton Cloud Vision OCR instance."""
    global _cloud_vision_instance
    if _cloud_vision_instance is None:
        _cloud_vision_instance = CloudVisionOCR()
    return _cloud_vision_instance
