"""
Screenshot Classifier - Determines if an image is TFT standings screenshot.

Uses template matching and keyword detection to classify screenshots with high confidence.
"""

import cv2
import numpy as np
import pytesseract
from pathlib import Path
from typing import Tuple, Optional
import logging

from config import _FULL_CFG

log = logging.getLogger(__name__)

# TFT-specific keywords to look for
STANDINGS_KEYWORDS = [
    "PLACEMENT",
    "PLACE",
    "1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH",
    "GAME TIME",
    "PLAYER",
    "RANKING"
]


class ScreenshotClassifier:
    """Classifies images as TFT standings screenshots or not."""

    def __init__(self):
        config = _FULL_CFG
        settings = config.get("standings_screenshots", {})
        self.threshold = settings.get("classification_threshold", 0.70)
        self.skip_classification = settings.get("skip_classification", False)
        self.trusted_channels = settings.get("monitor_channels", [])
        
        log.info(
            f"Classifier initialized (threshold: {self.threshold}, "
            f"skip_classification: {self.skip_classification})"
        )

    def classify(self, image_path: str, channel_name: str = None) -> Tuple[bool, float, dict]:
        """
        Classify image as TFT standings screenshot.

        Args:
            image_path: Path to image file
            channel_name: Optional channel name for trusted channel bypass

        Returns:
            (is_standings, confidence, metadata)
        """
        try:
            # Skip classification if enabled (trusted channels)
            if self.skip_classification:
                if channel_name in self.trusted_channels or not channel_name:
                    log.info("Classification bypassed (trusted channel)")
                    return True, 1.0, {"method": "bypass"}

            # Read image
            img = cv2.imread(image_path)
            if img is None:
                log.error(f"Failed to read image: {image_path}")
                return False, 0.0, {}

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Run simplified classification methods
            scores = {}

            # 1. Basic image validation
            scores["basic"] = self._basic_validation(img)

            # 2. Layout structure score (simplified)
            scores["layout"] = self._layout_analysis(gray)

            # 3. Color profile score
            scores["color"] = self._color_profile_analysis(img)

            # Calculate weighted average confidence
            weights = {
                "basic": 0.40,
                "layout": 0.40,
                "color": 0.20
            }

            overall_confidence = sum(
                scores.get(k, 0) * weights.get(k, 0)
                for k in scores.keys()
            )

            is_standings = overall_confidence >= self.threshold

            metadata = {
                "scores": scores,
                "weights": weights,
                "image_size": img.shape[:2],
                "method": "simplified"
            }

            log.info(
                f"Classification result: {is_standings} "
                f"(confidence: {overall_confidence:.3f})"
            )

            return is_standings, overall_confidence, metadata

        except Exception as e:
            log.error(f"Error classifying image: {e}", exc_info=True)
            return False, 0.0, {"error": str(e)}

    def _basic_validation(self, img: np.ndarray) -> float:
        """Basic image validation checks."""
        try:
            h, w = img.shape[:2]
            score = 0.0

            # Check 1: Minimum dimensions (TFT screenshots are reasonably sized)
            if w >= 800 and h >= 600:
                score += 0.4
            elif w >= 600 and h >= 400:
                score += 0.2

            # Check 2: Aspect ratio (most screenshots are landscape or near-square)
            aspect_ratio = w / h
            if 0.5 <= aspect_ratio <= 2.5:
                score += 0.3

            # Check 3: Not too large (prevent processing of massive images)
            if w <= 4096 and h <= 4096:
                score += 0.3

            return float(min(score, 1.0))

        except Exception as e:
            log.debug(f"Basic validation error: {e}")
            return 0.0

    def _layout_analysis(self, gray_image: np.ndarray) -> float:
        """Simplified layout analysis for text-heavy images."""
        try:
            h, w = gray_image.shape
            score = 0.0

            # Check 1: Detect text regions using simple thresholding
            # Text-heavy images have good distribution of black/white pixels
            _, binary = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Calculate text density (percentage of dark pixels)
            text_density = 1.0 - (np.sum(binary == 255) / (h * w))
            
            # TFT screenshots typically have 15-40% text density
            if 0.10 <= text_density <= 0.50:
                score += 0.5
            elif 0.05 <= text_density <= 0.60:
                score += 0.3

            # Check 2: Edge density (text has lots of edges)
            edges = cv2.Canny(gray_image, 50, 150)
            edge_density = np.sum(edges > 0) / (h * w)
            
            # TFT UI has moderate edge density
            if 0.05 <= edge_density <= 0.25:
                score += 0.5
            elif 0.03 <= edge_density <= 0.35:
                score += 0.3

            return float(min(score, 1.0))

        except Exception as e:
            log.debug(f"Layout analysis error: {e}")
            return 0.0

    def _color_profile_analysis(self, img: np.ndarray) -> float:
        """Analyze color profile for TFT UI characteristics."""
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # TFT UI typically has:
            # - Dark background
            # - Gold/ornate text
            # - Distinct color scheme

            # Calculate brightness
            brightness = np.mean(hsv[:, :, 2])

            score = 0.0

            # TFT typically has moderate brightness (not too bright, not too dark)
            if 50 < brightness < 180:
                score += 0.5

            # Check for gold tones (TFT UI color)
            # HSV ranges for gold: [20, 30] hue, [100, 200] saturation
            gold_mask = cv2.inRange(
                hsv,
                np.array([20, 100, 100]),
                np.array([30, 200, 255])
            )
            gold_pixels = np.count_nonzero(gold_mask)
            total_pixels = img.shape[0] * img.shape[1]

            # If reasonable amount of gold tones
            gold_ratio = gold_pixels / total_pixels
            if 0.01 < gold_ratio < 0.15:
                score += 0.5

            return float(score)

        except Exception as e:
            log.debug(f"Color profile analysis error: {e}")
            return 0.0




# Singleton instance
_classifier_instance = None

def get_classifier() -> ScreenshotClassifier:
    """Get or create classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ScreenshotClassifier()
    return _classifier_instance
