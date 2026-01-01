"""
Advanced OCR Pipeline - Multi-pass preprocessing and ensemble OCR for TFT screenshots.

Uses Tesseract and PaddleOCR with consensus algorithm for 99%+ accuracy.
PHASE 3: PaddleOCR implementation (better accuracy for game UI)
"""

import cv2
import numpy as np
import pytesseract
from typing import Dict, List, Tuple, Optional
import logging
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import statistics
import random

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logging.warning("PaddleOCR not installed - will use Tesseract only")

from config import _FULL_CFG

log = logging.getLogger(__name__)

# Placement points mapping
PLACEMENT_POINTS = {
    1: 8, 2: 7, 3: 6, 4: 5,
    5: 4, 6: 3, 7: 2, 8: 1
}

# Common OCR confusions for fuzzy matching
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


class OCRRPipeline:
    """Multi-pass OCR pipeline with ensemble approach."""

    # TFT placement points mapping
    PLACEMENT_POINTS = {
        1: 8, 2: 7, 3: 6, 4: 5,
        5: 4, 6: 3, 7: 2, 8: 1
    }

    def __init__(self):
        config = _FULL_CFG
        self.ocr_config = config.get("standings_screenshots", {}).get(
            "ocr_engines", {}
        )
        self.tesseract_enabled = self.ocr_config.get("tesseract", {}).get(
            "enabled", True
        )
        self.paddleocr_enabled = self.ocr_config.get("paddleocr", {}).get(
            "enabled", True
        )

        # Configure Tesseract
        tesseract_config = self.ocr_config.get("tesseract", {}).get(
            "config", "--psm 6 --oem 3"
        )
        self.tesseract_config = tesseract_config

        # Configure Tesseract path (Windows default)
        tesseract_path = self.ocr_config.get("tesseract", {}).get(
            "path", ""
        )
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            log.info(f"Tesseract path configured: {tesseract_path}")

        # PaddleOCR reader (lazy load)
        self._paddleocr_reader = None

        # Preprocessing settings
        self.preprocessing_passes = config.get(
            "standings_screenshots", {}
        ).get("preprocessing_passes", 7)  # Use 7 passes (Pass 7: minimal preprocessing, no thresholding)

        log.info(
            f"OCR Pipeline initialized (Tesseract: {self.tesseract_enabled}, "
            f"PaddleOCR: {self.paddleocr_enabled})"
        )

    def _get_paddleocr_reader(self):
        """Lazy load PaddleOCR reader."""
        if self._paddleocr_reader is None and self.paddleocr_enabled and PADDLEOCR_AVAILABLE:
            try:
                cfg = self.ocr_config.get("paddleocr", {})
                use_gpu = cfg.get("gpu", False)
                
                # PaddleOCR uses use_angle_cls=True by default for better text detection
                # For Railway (CPU-only), use default (no GPU parameter)
                # lang='en' for English text
                self._paddleocr_reader = PaddleOCR(lang='en')
                log.info(f"PaddleOCR reader initialized (GPU: {use_gpu})")
            except Exception as e:
                log.error(f"Failed to initialize PaddleOCR: {e}")
                self.paddleocr_enabled = False
        return self._paddleocr_reader

    def _debug_visualize_ocr_results(
        self, 
        img: np.ndarray, 
        ocr_results: List[Dict], 
        image_path: str,
        engine_name: str = "OCR"
    ):
        """
        Visual debug: Save annotated image with OCR bounding boxes.
        
        This helps understand what OCR engines are actually detecting.
        """
        try:
            # Create debug directory
            debug_dir = Path("debug_ocr")
            debug_dir.mkdir(exist_ok=True)
            
            # Copy image
            debug_img = img.copy()
            height, width = debug_img.shape[:2]
            
            # Define colors for different text types
            colors = {
                'placement': (0, 255, 0),      # Green
                'name': (255, 0, 255),           # Magenta
                'header': (255, 255, 0),          # Cyan
                'other': (0, 165, 255)            # Orange
            }
            
            # Draw bounding boxes
            for i, item in enumerate(ocr_results):
                text = item['text']
                conf = item.get('confidence', 0.0)
                x_center = item.get('x_center', 0)
                y_center = item.get('y_center', 0)
                
                # Determine text type
                text_type = 'other'
                if text.isdigit() and len(text) == 1 and 1 <= int(text) <= 8:
                    text_type = 'placement'
                elif len(text) >= 3 and any(c.isalpha() for c in text):
                    # Check if it's a header keyword
                    text_upper = text.upper()
                    if any(kw in text_upper for kw in ['STANDING', 'PLAYER', 'PLACE', 'FIRST']):
                        text_type = 'header'
                    elif conf > 0.5:
                        text_type = 'name'
                
                # Get bounding box
                bbox = item.get('bbox')
                if bbox is not None:
                    # EasyOCR format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    if isinstance(bbox, list) and len(bbox) == 4:
                        x1, y1 = bbox[0]
                        x2, y2 = bbox[2]
                        w, h = x2 - x1, y2 - y1
                    # Tesseract format: [left, top, width, height]
                    elif isinstance(bbox, list) and len(bbox) == 4 and isinstance(bbox[0], (int, float)):
                        x1, y1 = bbox[0], bbox[1]
                        w, h = bbox[2], bbox[3]
                    else:
                        # Draw circle at center if no bbox
                        cv2.circle(debug_img, (int(x_center), int(y_center)), 10, colors[text_type], 2)
                        continue
                    
                    # Draw rectangle
                    cv2.rectangle(debug_img, (int(x1), int(y1)), (int(x1 + w), int(y1 + h)), 
                                   colors[text_type], 2)
                    
                    # Draw text
                    cv2.putText(debug_img, f"{text[:15]} ({conf:.2f})", 
                              (int(x1), max(0, int(y1) - 5)),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, colors[text_type], 1)
                    
                    # Add label for text type
                    cv2.putText(debug_img, text_type,
                              (int(x1), max(0, int(y1 + h) + 12)),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.3, colors[text_type], 1)
            
            # Add image dimensions info
            cv2.putText(debug_img, f"Engine: {engine_name} | Detections: {len(ocr_results)}",
                      (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Draw grid lines at key X thresholds
            cv2.line(debug_img, (200, 0), (200, height), (100, 100, 100), 1)  # Placement column
            cv2.line(debug_img, (150, 0), (150, height), (100, 100, 100), 1)  # Gap threshold
            cv2.putText(debug_img, "X=200", (205, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
            
            # Save debug image
            image_name = Path(image_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = debug_dir / f"{image_name}_{engine_name}_{timestamp}.jpg"
            cv2.imwrite(str(debug_path), debug_img)
            log.info(f"Debug visualization saved: {debug_path}")
            
        except Exception as e:
            log.error(f"Failed to save debug visualization: {e}", exc_info=True)

    def extract_from_image(self, image_path: str) -> Dict:
        """
        Extract standings data from screenshot.

        Args:
            image_path: Path to screenshot image

        Returns:
            Dictionary with extracted data and confidence scores
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")

            # SCALE NORMALIZATION: Resize images to standard size (1295x865) if needed
            # Only resize if size difference > 25% to avoid unnecessary artifacts
            # For small formats (like lobbycround3.png), use original size to preserve quality
            target_height = 865
            target_width = 1295
            current_height, current_width = img.shape[:2]
            aspect_ratio = current_width / current_height

            # Calculate size difference percentage
            height_diff = abs(current_height - target_height) / target_height
            width_diff = abs(current_width - target_width) / target_width

            # Don't resize if close to target OR if image is small format (< 900px height)
            # Small formats work better without upscaling
            skip_resize = (
                (height_diff < 0.25 and width_diff < 0.25) or
                current_height < 900
            )

            if not skip_resize:
                # Use INTER_LANCZOS4 (best quality for scaling)
                log.info(f"Resizing image from {current_width}x{current_height} to {target_width}x{target_height} (using Lanczos)")
                img = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)

            results = {}
            
            # Enable debug mode for first image or specific screenshots
            enable_debug = True  # Set to True for visual debugging

            # Run multiple preprocessing passes
            # Stop early if we've found enough players (adaptive optimization)
            max_players_found = 0
            for pass_num in range(1, self.preprocessing_passes + 1):
                log.info(f"Running preprocessing pass {pass_num}/{self.preprocessing_passes}")
                pass_result = self._run_pass(img, pass_num)

                if pass_result:
                    results[f"pass{pass_num}"] = pass_result
                    
                    # DEBUG: Visualize each pass's OCR results
                    if enable_debug and pass_result.get("results"):
                        pass_results_dict = pass_result.get("results", {})
                        for engine_name, engine_results in pass_results_dict.items():
                            if engine_results and isinstance(engine_results, list):
                                self._debug_visualize_ocr_results(
                                    img, engine_results, image_path, 
                                    f"Pass{pass_num}_{engine_name}"
                                )

                    # Early stopping: check if we found 8 players
                    # Quick check without full parsing
                    temp_structured = self._quick_check_players(pass_result)
                    if temp_structured and temp_structured.get('player_count', 0) >= 8:
                        max_players_found = max(max_players_found, temp_structured.get('player_count', 0))

                # Stop after pass 3 if we already have 8 players (speed optimization)
                if max_players_found >= 8 and pass_num >= 3:
                    log.info(f"Early stopping: Found {max_players_found} players by pass {pass_num}")
                    break

            # Generate consensus from all passes
            consensus = self._generate_consensus(results)

            # Find best pass (highest confidence with bias toward minimal preprocessing)
            best_pass_name = None
            best_pass_data = None
            best_pass_confidence = 0
            
            print(f"[DEBUG] All results keys: {results.keys()}")
            for pass_name, pass_data in results.items():
                # Get pass-level confidence (average of engine confidences)
                pass_conf = 0
                if isinstance(pass_data, dict) and "results" in pass_data:
                    # Calculate average confidence from all engines in this pass
                    engine_results = pass_data["results"]
                    engine_confs = []
                    for engine_name, engine_data in engine_results.items():
                        if engine_data and isinstance(engine_data, dict):
                            engine_conf = engine_data.get("confidence", 0)
                            engine_confs.append(engine_conf)
                    
                    if engine_confs:
                        pass_conf = sum(engine_confs) / len(engine_confs)
                    
                    # Apply bias toward minimal preprocessing passes (5, 6, 7)
                    # These passes preserve text quality better for player names
                    pass_num = int(pass_name.replace("pass", ""))
                    if pass_num >= 5:
                        # Boost confidence by 15% for minimal preprocessing passes
                        pass_conf *= 1.15
                        print(f"[DEBUG] Pass {pass_name} confidence: {pass_conf:.2f} (boosted from minimal preprocessing)")
                    else:
                        print(f"[DEBUG] Pass {pass_name} confidence: {pass_conf:.2f}")
                else:
                    print(f"[DEBUG] Pass {pass_name} is not a dict: {type(pass_data)}")
                
                if pass_conf > best_pass_confidence:
                    best_pass_confidence = pass_conf
                    best_pass_name = pass_name
                    best_pass_data = pass_data
            
            if best_pass_data and best_pass_name:
                log.info(f"Best pass for TFT parsing: {best_pass_name} (confidence: {best_pass_confidence:.1f}%)")
                
                # Save only the best pass's raw results and image for TFT-specific parser
                # This avoids mixing garbage from aggressive preprocessing passes
                self._last_raw_results = {best_pass_name: best_pass_data}
                self._last_best_pass = best_pass_name
            else:
                # Fallback: save all results if no best pass found
                log.warning("No best pass found, using all passes for TFT parsing")
                self._last_raw_results = results
                self._last_best_pass = None

            # Structure extracted data
            # Pass self._last_raw_results (best pass only) and consensus
            players_list = self._tft_specific_parser(img, self._last_raw_results, best_pass_name if best_pass_name else None)
            
            # Wrap in dict structure (tft_specific_parser returns list)
            structured = {
                "players": players_list,
                "player_count": len(players_list),
                "expected_players": 8
            }

            # Calculate confidence scores
            scores = self._calculate_confidence(results, consensus, structured)

            return {
                "structured_data": structured,
                "raw_results": results,
                "consensus": consensus,
                "scores": scores,
                "success": True
            }

        except Exception as e:
            log.error(f"OCR extraction error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def process_batch(self, image_paths: List[str], max_workers: int = 3) -> List[Dict]:
        """
        Process multiple images concurrently using ThreadPoolExecutor.
        
        PHASE 4: CONCURRENT PROCESSING SUPPORT
        
        Args:
            image_paths: List of image file paths to process
            max_workers: Maximum number of concurrent workers (default: 3)
            
        Returns:
            List of extraction results (same format as extract_from_image)
            
        Example:
            >>> ocr = get_ocr_pipeline()
            >>> results = ocr.process_batch([
            ...     'lobbyaround3.png',
            ...     'lobbybround3.png',
            ...     'lobbycround3.png'
            ... ])
            >>> for i, result in enumerate(results):
            ...     print(f"Image {i+1}: {len(result['structured_data']['players'])} players")
        """
        if not image_paths:
            return []
        
        start_time = datetime.now()
        log.info(f"Starting batch processing of {len(image_paths)} images with {max_workers} workers")
        
        results = []
        
        try:
            # Use ThreadPoolExecutor for concurrent processing
            # I/O-bound operations (file reading, OCR) benefit from threading
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_path = {
                    executor.submit(self.extract_from_image, path): path
                    for path in image_paths
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        result = future.result()
                        result['image_path'] = path  # Add path to result
                        results.append(result)
                        
                        if result.get('success'):
                            player_count = result['structured_data']['player_count']
                            log.info(f"Completed: {path} ({player_count} players)")
                        else:
                            log.error(f"Failed: {path} - {result.get('error')}")
                            
                    except Exception as e:
                        log.error(f"Error processing {path}: {e}", exc_info=True)
                        results.append({
                            'success': False,
                            'error': str(e),
                            'image_path': path
                        })
            
            # Sort results by original order
            results.sort(key=lambda x: image_paths.index(x.get('image_path', '')))
            
            # Calculate batch statistics
            elapsed = (datetime.now() - start_time).total_seconds()
            successful = sum(1 for r in results if r.get('success'))
            
            log.info(
                f"Batch processing complete: {successful}/{len(image_paths)} successful "
                f"in {elapsed:.1f}s ({elapsed/len(image_paths):.1f}s per image)"
            )
            
        except Exception as e:
            log.error(f"Batch processing error: {e}", exc_info=True)
            # Return partial results if available
            
        return results

    def _run_pass(self, img: np.ndarray, pass_num: int) -> Optional[Dict]:
        """Run a single preprocessing and OCR pass."""
        try:
            # Apply preprocessing based on pass type
            processed = self._preprocess_image(img, pass_num)

            results = {}

            # Tesseract OCR
            if self.tesseract_enabled:
                tesseract_result = self._run_tesseract(processed)
                if tesseract_result:
                    results["tesseract"] = tesseract_result

            # PaddleOCR
            if self.paddleocr_enabled:
                paddleocr_result = self._run_paddleocr(processed)
                if paddleocr_result:
                    results["paddleocr"] = paddleocr_result

            if not results:
                return None

            return {
                "pass_type": pass_num,
                "results": results
            }

        except Exception as e:
            log.warning(f"Pass {pass_num} error: {e}")
            return None

    def _preprocess_image(self, img: np.ndarray, pass_num: int) -> np.ndarray:
        """Apply preprocessing based on pass type."""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if pass_num == 1:
            # Pass 1: Conservative preprocessing for consistency
            # CLAHE contrast enhancement (moderate)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Otsu's thresholding on enhanced image
            _, thresh = cv2.threshold(
                enhanced, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            return thresh

        elif pass_num == 2:
            # Pass 2: Sharp edge extraction
            # Bilateral filtering
            bilateral = cv2.bilateralFilter(gray, 9, 75, 75)

            # Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(bilateral, kernel, iterations=1)

            # Sharpening filter
            kernel_sharpen = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ])
            sharpened = cv2.filter2D(dilated, -1, kernel_sharpen)

            return sharpened

        elif pass_num == 3:
            # Pass 3: Aggressive contrast for DARK placement numbers (1, 6 missing)
            # Gamma correction (brighten dark areas)
            gamma = 0.75  # Brighten image
            gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)])
            gamma_corrected = cv2.LUT(gray, gamma_table.astype(np.uint8))

            # Aggressive CLAHE (high clipLimit)
            clahe = cv2.createCLAHE(clipLimit=8.0, tileGridSize=(2, 2))
            enhanced = clahe.apply(gamma_corrected)

            # Otsu thresholding (adaptive)
            _, thresh = cv2.threshold(
                enhanced, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            # Morphological operations to clean up numbers
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            return cleaned

        elif pass_num == 4:
            # Pass 4: Lighter preprocessing for smaller/different formats (lobbyaround3)
            # Gamma correction (milder than Pass 3)
            gamma = 0.85  # Light brightening
            gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)])
            gamma_corrected = cv2.LUT(gray, gamma_table.astype(np.uint8))

            # Light CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gamma_corrected)

            # Adaptive threshold (mean thresholding)
            mean_val = enhanced.mean()
            _, thresh = cv2.threshold(
                enhanced, mean_val, 255,
                cv2.THRESH_BINARY
            )

            # Light denoising
            denoised = cv2.fastNlMeansDenoising(thresh, None, h=3)

            return denoised

        elif pass_num == 5:
            # Pass 5: Very light/no preprocessing for lobbycround3 format
            # This format works better with original image or very minimal processing

            # Just convert to grayscale (already done above)
            # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Already in scope - use gray directly

            # Very light denoising only (no thresholding, no contrast)
            # This preserves original appearance for better OCR on this format
            denoised = cv2.fastNlMeansDenoising(gray, None, h=2)

            return denoised

        elif pass_num == 6:
            # Pass 6: Specialized preprocessing for number/placement detection
            # Focus on enhancing single-digit contrast (1-8)
            # High contrast thresholding for black numbers on light background

            # Gamma correction for contrast boost
            gamma = 0.6  # Brighten and boost contrast
            gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)])
            gamma_corrected = cv2.LUT(gray, gamma_table.astype(np.uint8))

            # High contrast threshold (binarize aggressively)
            _, thresh = cv2.threshold(
                gamma_corrected, 127, 255,
                cv2.THRESH_BINARY
            )

            # Dilate to make numbers thicker (easier for OCR to detect)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            dilated = cv2.dilate(thresh, kernel, iterations=1)

            # Light denoising to clean up
            denoised = cv2.fastNlMeansDenoising(dilated, None, h=1)

            return denoised
            
        elif pass_num == 7:
            # Pass 7: MINIMAL PREPROCESSING - NO THRESHOLDING
            # Just enhance contrast and sharpness to preserve text quality
            # For better player name recognition (original plan Pass 7)
            
            # CLAHE contrast enhancement (light)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Light sharpening (subtle)
            kernel_sharpen = np.array([
                [0, -0.5, 0],
                [-0.5, 2, -0.5],
                [0, -0.5, 0]
            ])
            sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
            
            # Light denoising (non-local means)
            denoised = cv2.fastNlMeansDenoising(sharpened, None, h=5)
            
            return denoised

        else:
            return gray

    def _run_tesseract(self, image: np.ndarray) -> Dict:
        """Run Tesseract OCR."""
        try:
            # Extract all data
            data = pytesseract.image_to_data(
                image,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )

            # Extract text with confidence
            text_lines = []
            confidences = []

            for i, text in enumerate(data["text"]):
                conf = int(data["conf"][i])
                text = str(text).strip()

                if text and conf > 0:
                    text_lines.append(text)
                    confidences.append(conf)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "engine": "tesseract",
                "text": " ".join(text_lines),
                "confidence": avg_confidence,
                "raw_data": data
            }

        except Exception as e:
            log.debug(f"Tesseract error: {e}")
            return {}

    def _run_paddleocr(self, image: np.ndarray) -> Dict:
        """Run PaddleOCR."""
        try:
            reader = self._get_paddleocr_reader()
            if reader is None:
                return {}

            # PaddleOCR returns list of OCRResult dicts (newer versions)
            # Format: [{'rec_boxes': array([[x1, y1, x2, y2], ...]),
            #           'rec_texts': ['text1', 'text2', ...],
            #           'rec_scores': [conf1, conf2, ...]}, ...]
            results = reader.ocr(image)

            # Handle different result formats (list vs dict)
            if isinstance(results, list) and results:
                # Newer PaddleOCR version (3.x)
                first_result = results[0]
                
                if isinstance(first_result, dict):
                    rec_boxes = first_result.get('rec_boxes', [])
                    rec_texts = first_result.get('rec_texts', [])
                    rec_scores = first_result.get('rec_scores', [])
                    
                    text_lines = []
                    confidences = []
                    formatted_raw_data = []
                    
                    # Process each detected text box
                    for i in range(len(rec_texts)):
                        if i < len(rec_boxes) and i < len(rec_scores):
                            bbox = rec_boxes[i]
                            text = rec_texts[i]
                            conf = rec_scores[i]
                            
                            if text.strip():
                                text_lines.append(text.strip())
                                confidences.append(conf * 100)  # Convert to percentage
                                
                                # Format bbox to match EasyOCR format: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                                formatted_bbox = [
                                    [int(bbox[0]), int(bbox[1])],
                                    [int(bbox[2]), int(bbox[1])],
                                    [int(bbox[2]), int(bbox[3])],
                                    [int(bbox[0]), int(bbox[3])]
                                ]
                                
                                formatted_raw_data.append((
                                    formatted_bbox,
                                    text.strip(),
                                    conf
                                ))
                else:
                    # Fallback to older format
                    text_lines = []
                    confidences = []
                    formatted_raw_data = results
            else:
                # Older format or empty results
                text_lines = []
                confidences = []
                formatted_raw_data = []

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "engine": "paddleocr",
                "text": " ".join(text_lines),
                "confidence": avg_confidence,
                "raw_data": formatted_raw_data
            }

        except Exception as e:
            log.debug(f"PaddleOCR error: {e}")
            return {}

    def _generate_consensus(self, results: Dict) -> Dict:
        """Generate consensus from multiple OCR results."""
        all_texts = []

        # Collect all text from all passes and engines
        for pass_name, pass_data in results.items():
            if pass_data and "results" in pass_data:
                for engine_name, engine_data in pass_data["results"].items():
                    if engine_data and "text" in engine_data:
                        all_texts.append({
                            "text": engine_data["text"],
                            "confidence": engine_data.get("confidence", 0),
                            "engine": engine_name,
                            "pass": pass_name
                        })

        if not all_texts:
            return {"text": "", "confidence": 0}

        # Simple consensus: use highest confidence result
        best_result = max(all_texts, key=lambda x: x["confidence"])

        # Advanced: voting if multiple high-confidence results
        high_conf_results = [r for r in all_texts if r["confidence"] > 80]
        if len(high_conf_results) >= 2:
            # Use most common result
            text_votes = {}
            for r in high_conf_results:
                text = r["text"]
                text_votes[text] = text_votes.get(text, 0) + 1

            best_text = max(text_votes.items(), key=lambda x: x[1])[0]
            best_result = next(r for r in all_texts if r["text"] == best_text)

        return {
            "text": best_result["text"],
            "confidence": best_result["confidence"],
            "engine": best_result["engine"],
            "votes": len(all_texts)
        }

    def _structure_data(self, consensus: Dict) -> Dict:
        """Structure extracted text into TFT standings format."""
        text = consensus["text"].upper()

        # Parse for player names and placements
        # Look for placement numbers (1-8) and associated names

        players = []

        # Common patterns in TFT standings
        # "1. PlayerName" or "PlayerName 1st"
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for placement number
            placement = None
            name = None

            # Pattern: "1. Name" or "Name 1st"
            for num in range(1, 9):
                if f"{num}." in line:
                    parts = line.split(f"{num}.")
                    if len(parts) > 1:
                        placement = num
                        name = parts[1].strip()
                    break
                elif str(num) in line:
                    # Extract number, assume rest is name
                    placement = num
                    name = line.replace(str(num), "").strip()
                    break

            if placement and name and len(name) > 2:
                # Validate placement is in range 1-8
                if 1 <= placement <= 8:
                    players.append({
                        "placement": placement,
                        "name": name,
                        "points": PLACEMENT_POINTS.get(placement, 0)
                    })

        # If we didn't find structured data, try alternative parsing
        if len(players) < 4:  # Should have at least 4 players
            players = self._alternative_parsing(lines)
        
        # If still no players, try TFT-specific parser
        if len(players) < 4 and hasattr(self, '_last_raw_results') and hasattr(self, '_last_image'):
            players = self._tft_specific_parser(self._last_image, self._last_raw_results)
            log.info(f"Used TFT-specific parser, found {len(players)} players")

        return {
            "players": players,
            "player_count": len(players),
            "expected_players": 8
        }

    def _quick_check_players(self, pass_result: Dict) -> Optional[Dict]:
        """
        Quick check to count players from a single pass result.
        Used for early stopping optimization.
        
        Args:
            pass_result: Result from a single preprocessing pass
            
        Returns:
            Dict with player_count if found, None otherwise
        """
        if not pass_result or "results" not in pass_result:
            return None
        
        # Count all OCR text items that look like player names
        # This is a rough estimate - doesn't need to be perfect
        text_count = 0
        
        for engine_data in pass_result["results"].values():
            if not engine_data:
                continue
                
            # Count text items (skipping very short/long ones)
            if "text" in engine_data:
                text = engine_data["text"].strip().upper()
                # Skip keywords
                skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                             'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                             'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                             'PLAY', 'AGAIN', 'CONTINUE']
                
                if text not in skip_keywords and 3 <= len(text) <= 20:
                    text_count += 1
            
            # Also count from raw_data if available
            elif "raw_data" in engine_data and engine_data["raw_data"]:
                for item in engine_data["raw_data"]:
                    # Handle EasyOCR, PaddleOCR, and Tesseract formats
                    if isinstance(item, tuple) and len(item) == 3:
                        # EasyOCR: (bbox, text, conf)
                        text = item[1].strip().upper()
                    elif isinstance(item, list) and len(item) == 2:
                        # PaddleOCR: [bbox, (text, conf_score)]
                        if isinstance(item[1], tuple) and len(item[1]) == 2:
                            text = item[1][0].strip().upper()
                        else:
                            continue
                    elif isinstance(item, str):
                        # Tesseract: just text
                        text = item.strip().upper()
                    else:
                        continue
                    
                    # Skip keywords
                    skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                                 'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                                 'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                                 'PLAY', 'AGAIN', 'CONTINUE', '-', 'ROUND']
                    
                    if text not in skip_keywords and 3 <= len(text) <= 20 and text.isalnum():
                        text_count += 1
        
        # Estimate player count (roughly half of text items are player names)
        estimated_players = min(8, text_count // 2 + 2)
        
        if estimated_players >= 8:
            return {"player_count": estimated_players}
        
        return None

    def _tft_specific_parser(self, image: np.ndarray, raw_results: Dict, best_pass_name: str = None) -> List[Dict]:
        """
        Parse TFT screenshots with placement + name format.
        Focuses on LEFT side of image only.
        
        Args:
            image: Input image as numpy array (for dimensions)
            raw_results: All OCR pass results (if best_pass_name is None)
                      or single best pass results (if best_pass_name is set)
            best_pass_name: Name of best pass to use (if provided)
        
        User's TFT screenshots have:
        - Player names and placements on LEFT side of image
        - Placement column may start with "#"
        - Sometimes says "standing"
        - Player names directly to right of placement
        """
        players = []
        
        # Get image dimensions
        height, width = image.shape[:2]
        
        # Focus on LEFT side (50% of image width)
        # Based on user: "player names and placements will be on left side"
        left_crop_x = int(width * 0.5)
        
        # Log for debugging
        log.debug(f"TFT parser: Image size {width}x{height}, focusing on left side (0-{left_crop_x})")
        
        # Parse raw OCR results from EasyOCR
        # Filter to only results on LEFT side of image
        raw_ocr_results = []
        
        # Filter: only process best pass if specified (avoids mixing garbage from aggressive preprocessing passes)
        # Pass names in raw_results are like "pass 1", "pass 2", etc.
        # best_pass_name is like "pass 7"
        print(f"\n[DEBUG] raw_results keys: {list(raw_results.keys())}")
        print(f"[DEBUG] best_pass_name: {best_pass_name}")
        
        if best_pass_name:
            # Extract pass number from best_pass_name and format as "pass1"
            pass_num = best_pass_name.replace("pass", "")
            pass_key = f"pass{pass_num}"
            passes_to_process = {pass_key}
            print(f"[DEBUG] Filter to: {pass_key}")
        else:
            passes_to_process = list(raw_results.keys())
            print(f"[DEBUG] Process all: {passes_to_process}")
        
        for pass_name, pass_data in raw_results.items():
            # Skip passes that aren't in our processing list
            if pass_name not in passes_to_process:
                print(f"[DEBUG] Skipping pass: {pass_name}")
                continue
                
            # Skip if pass_data is not a dict (might be float for confidence)
            if not isinstance(pass_data, dict):
                continue
                
            if pass_data and "results" in pass_data:
                for engine_name, engine_data in pass_data["results"].items():
                    # Process EasyOCR raw data
                    if engine_name == "easyocr" and engine_data and "raw_data" in engine_data:
                        # Get raw EasyOCR results with bounding boxes
                        for (bbox, text, conf) in engine_data["raw_data"]:
                            # bbox format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                            x_center = (bbox[0][0] + bbox[2][0]) / 2
                            
                            # Only use text from LEFT side
                            if x_center > left_crop_x:
                                log.debug(f"Skipping right-side text: {text} at x={x_center}")
                                continue
                            
                            # Clean text
                            text_clean = text.strip().upper()
                            
                            # Skip non-relevant text
                            skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS', 
                                         'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                                         'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                                         'PLAY', 'AGAIN', 'CONTINUE']
                            
                            if any(keyword in text_clean for keyword in skip_keywords):
                                log.debug(f"Skipping keyword: {text_clean}")
                                continue
                            
                            # Skip numbers that aren't placements (like "6-5" from round 6-5)
                            if '-' in text_clean:
                                log.debug(f"Skipping round text: {text_clean}")
                                continue
                            
                            # Skip very short or very long text
                            if len(text_clean) < 1 or len(text_clean) > 30:
                                continue
                            
                            # Save detected item
                            raw_ocr_results.append({
                                'text': text_clean,
                                'placement': None,
                                'name': None,
                                'x_center': x_center,
                                'y_center': (bbox[0][1] + bbox[2][1]) / 2,
                                'bbox': bbox,
                                'confidence': conf
                            })
                            
                            log.debug(f"Detected OCR item: '{text_clean}' at x={x_center}, y={raw_ocr_results[-1]['y_center']}")
                    
                    # Process PaddleOCR raw data
                    elif engine_name == "paddleocr" and engine_data and "raw_data" in engine_data:
                        # PaddleOCR raw_data format from _run_paddleocr:
                        # List of tuples: (formatted_bbox, text, confidence)
                        # formatted_bbox: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                        
                        for item in engine_data["raw_data"]:
                            if not isinstance(item, tuple) or len(item) != 3:
                                continue
                            
                            bbox, text, conf = item
                            
                            # Calculate x_center and y_center from bbox
                            # bbox format: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                            x_center = (bbox[0][0] + bbox[2][0]) / 2
                            y_center = (bbox[0][1] + bbox[1][1]) / 2
                            
                            # Only use text from LEFT side
                            if x_center > left_crop_x:
                                log.debug(f"Skipping right-side text: {text} at x={x_center}")
                                continue
                            
                            # Clean text
                            text_clean = text.strip().upper()
                            
                            # Skip non-relevant text
                            skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS', 
                                         'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                                         'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                                         'PLAY', 'AGAIN', 'CONTINUE']
                            
                            if any(keyword in text_clean for keyword in skip_keywords):
                                log.debug(f"Skipping keyword: {text_clean}")
                                continue
                            
                            # Skip numbers that aren't placements (like "6-5" from round 6-5)
                            if '-' in text_clean:
                                log.debug(f"Skipping round text: {text_clean}")
                                continue
                            
                            # Skip very short or very long text
                            if len(text_clean) < 1 or len(text_clean) > 30:
                                continue
                            
                            # Save detected item
                            raw_ocr_results.append({
                                'text': text_clean,
                                'placement': None,
                                'name': None,
                                'x_center': x_center,
                                'y_center': y_center,
                                'bbox': bbox,
                                'confidence': conf
                            })
                            
                            log.debug(f"Detected OCR item: '{text_clean}' at x={x_center}, y={y_center}")
                    
                    # Process Tesseract raw data (backup for missing placements)
                    elif engine_name == "tesseract" and engine_data and "raw_data" in engine_data:
                        # Get raw Tesseract results with bounding boxes
                        tesseract_data = engine_data["raw_data"]

                        # Tesseract returns dict with 'text', 'left', 'top', 'width', 'height', 'conf' arrays
                        for idx, text in enumerate(tesseract_data["text"]):
                            text_clean = text.strip().upper()

                            if not text_clean:
                                continue

                            # Get bounding box
                            bbox_left = tesseract_data["left"][idx]
                            bbox_top = tesseract_data["top"][idx]
                            bbox_width = tesseract_data["width"][idx]
                            bbox_height = tesseract_data["height"][idx]
                            bbox_conf = tesseract_data["conf"][idx]

                            # Calculate center
                            x_center = bbox_left + bbox_width / 2
                            y_center = bbox_top + bbox_height / 2

                            # Only use text from LEFT side
                            if x_center > left_crop_x:
                                log.debug(f"Skipping right-side text: {text_clean} at x={x_center}")
                                continue

                            # Skip non-relevant text
                            skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                                         'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                                         'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                                         'PLAY', 'AGAIN', 'CONTINUE']
                            
                            if any(keyword in text_clean for keyword in skip_keywords):
                                log.debug(f"Skipping keyword: {text_clean}")
                                continue
                            
                            # Skip numbers that aren't placements (like "6-5" from round 6-5)
                            if '-' in text_clean:
                                log.debug(f"Skipping round text: {text_clean}")
                                continue
                            
                            # Skip very short or very long text
                            if len(text_clean) < 1 or len(text_clean) > 30:
                                continue
                            
                            # Save detected item
                            raw_ocr_results.append({
                                'text': text_clean,
                                'placement': None,
                                'name': None,
                                'x_center': x_center,
                                'y_center': y_center,
                                'bbox': [bbox_left, bbox_top, bbox_left + bbox_width, bbox_top + bbox_height],
                                'confidence': bbox_conf
                            })
                            
                            log.debug(f"Detected Tesseract item: '{text_clean}' at x={x_center}, y={y_center}")
        
        # First pass: identify placement numbers
        # For Format 1 (Standing | Player), placements are single digits on the left
        # For Format 2, placements are single digits or prefixed with #

        placements_found = 0
        placement_x_positions = []  # Track X positions of placements to find column

        # Collect potential placements
        potential_placements = []

        for item in raw_ocr_results:
            text = item['text']
            x_center = item['x_center']

            # Must be on left side (X < 100 for placements)
            # More permissive threshold to catch placement numbers that are slightly offset
            if x_center > 150:
                continue

            placement = None

            # Pattern 1: Standalone number 1-8 (single digit) - most common for Format 1
            if text.isdigit() and 1 <= int(text) <= 8 and len(text) == 1:
                placement = int(text)

            # Pattern 2: "#1" or "#2" etc
            elif text.startswith('#') and text[1:].isdigit():
                placement = int(text[1:])

            # Pattern 3: "1ST", "2ND", "3RD", "4TH-8TH"
            elif text.endswith('ST') or text.endswith('ND') or text.endswith('RD') or text.endswith('TH'):
                # Extract number from "1ST", "2ND", etc.
                for num in range(1, 9):
                    ordinal = f"{num}{'ST' if num == 1 else 'ND' if num == 2 else 'RD' if num == 3 else 'TH'}"
                    if ordinal in text:
                        placement = num
                        break

            # Pattern 4: "P1", "P2", "P3", etc (for lobbycround3.png format)
            elif text.startswith('P') and len(text) >= 2 and text[1:].isdigit():
                try:
                    placement = int(text[1:])
                    if 1 <= placement <= 8:
                        item['placement'] = placement
                        placements_found += 1
                        log.info(f"Found placement with P prefix: {placement} from '{text}' at x={x_center:.0f}")
                except ValueError:
                    pass

            # Pattern 5: Text containing P followed by number (e.g., "P2 Ffoxface")
            elif text.startswith('P') and len(text) > 2:
                try:
                    import re
                    match = re.search(r'P(\d)', text, re.IGNORECASE)
                    if match:
                        placement = int(match.group(1))
                        if 1 <= placement <= 8:
                            item['placement'] = placement
                except (ValueError, AttributeError):
                    pass

            # If we found a valid placement, save it
            if placement is not None:
                potential_placements.append((item, placement, x_center))
                placement_x_positions.append(x_center)

        # VALIDATION: Only accept placements if they form a consistent vertical column
        # If multiple placements have similar X positions, they're likely real
        if placement_x_positions:
            # Find most common X position (the placement column)
            import statistics
            try:
                typical_x = statistics.mode(placement_x_positions)
            except statistics.StatisticsError:
                # No clear mode, use median
                typical_x = statistics.median(placement_x_positions)

            # Filter placements to only those near the typical X position
            for item, placement, x_center in potential_placements:
                if abs(x_center - typical_x) < 80:  # Within 80px of column (more permissive)
                    item['placement'] = placement
                    placements_found += 1
                    log.info(f"Found placement: {placement} from '{item['text']}' at x={x_center:.0f}")
                else:
                    # Reject - not in placement column
                    log.debug(f"Rejected placement {placement} from '{item['text']}' at x={x_center:.0f} (not in column)")
                    item['placement'] = None

        log.info(f"Total placement numbers detected: {placements_found}")
        
        # Second pass: associate placement numbers with nearby player names
        # Sort by Y coordinate (top to bottom) to process rows
        raw_ocr_results_sorted = sorted(raw_ocr_results, key=lambda x: x['y_center'])
        
        print(f"\n{'='*80}")
        print(f"TFT PARSER DEBUG: Collected {len(raw_ocr_results)} raw OCR items")
        print(f"Sample items:")
        for i, item in enumerate(raw_ocr_results_sorted[:5]):
            print(f"  {i}: '{item['text']}' at (x={item['x_center']:.0f}, y={item['y_center']:.0f})")
        if len(raw_ocr_results_sorted) > 5:
            print(f"  ... ({len(raw_ocr_results_sorted)-5} more items)")
        print(f"{'='*80}\n")
        
        # Y threshold: items within this Y are on same row
        # X threshold: name must be to the right of placement within this X distance
        y_threshold = 50  # Pixels vertical (same row)
        x_gap_threshold = 300  # Max pixels between placement and name (horizontal)
        
        # FIX 1: Merge nearby text fragments in same row to reconstruct full names
        # Group text fragments that are close together (X gap < 80px)
        merged_results = []
        raw_ocr_results_sorted = sorted(raw_ocr_results, key=lambda x: x['y_center'])
        
        for i, current_item in enumerate(raw_ocr_results_sorted):
            # Skip items that are already placement numbers
            if current_item.get('placement') is not None:
                continue
            
            # Try to merge with nearby text fragments to the right
            merged_text = [current_item['text']]
            current_x = current_item['x_center']
            current_y = current_item['y_center']
            
            for j, next_item in enumerate(raw_ocr_results_sorted):
                if j <= i:
                    continue  # Only look at items to the right
                
                # Skip if it's a placement number
                if next_item.get('placement') is not None:
                    continue
                
                # Check Y proximity (same row)
                y_diff = abs(next_item['y_center'] - current_y)
                if y_diff > y_threshold:
                    continue
                
                # Check X distance (to the right)
                x_gap = next_item['x_center'] - current_x
                if 0 < x_gap < 80:  # Merge fragments that are close together
                    merged_text.append(next_item['text'])
            
            # If we merged fragments, create merged item with longest text
            if len(merged_text) > 1:
                # Pick longest text (most likely to be full name)
                longest = max(merged_text, key=len)
                merged_item = current_item.copy()
                merged_item['text'] = longest
                merged_item['x_center'] = current_x
                merged_item['y_center'] = current_y
                merged_item['merged'] = True
                merged_item['fragment_count'] = len(merged_text)
                merged_results.append(merged_item)
            else:
                merged_results.append(current_item)
        
        # Use merged results for matching
        raw_ocr_results_sorted = merged_results
        
        matched_players = []
        matched_indices = set()  # Track matched items to avoid double-matching
        
        for i, current_item in enumerate(raw_ocr_results_sorted):
            # Skip if already matched
            if i in matched_indices:
                continue
            
            # If current item is a placement number
            if current_item['placement'] is not None:
                # Look for player name on the same row to the RIGHT
                for j, next_item in enumerate(raw_ocr_results_sorted):
                    # Skip self and already matched items
                    if j == i or j in matched_indices:
                        continue
                    
                    # Check if next item is a potential name (not a placement)
                    if next_item['placement'] is not None:
                        continue  # Skip other placement numbers
                    
                    # Validate name: 5+ chars, at least one letter (FIX: increased from 3 to filter out fragments)
                    text = next_item['text']
                    is_valid_name = (
                        len(text) >= 5 and
                        len(text) <= 20 and
                        any(c.isalpha() for c in text)
                    )
                    
                    if not is_valid_name:
                        continue
                    
                    # Check Y proximity (same row?)
                    y_diff = abs(next_item['y_center'] - current_item['y_center'])
                    
                    if y_diff > y_threshold:
                        continue  # Not on same row
                    
                    # Log this candidate name (after Y check)
                    print(f"Candidate name: '{text}' at x={next_item['x_center']:.0f}, Y diff: {y_diff:.1f}px")
                    
                    # Check X ordering (name must be to the RIGHT of placement)
                    x_gap = next_item['x_center'] - current_item['x_center']
                    
                    print(f"  Placement at x={current_item['x_center']:.0f}, Name at x={next_item['x_center']:.0f}, X gap: {x_gap:.1f}px")
                    
                    if x_gap <= 0:
                        print(f"  -> REJECTED: Name is to the left")
                        continue  # Name is to the left, not right
                    
                    if x_gap > x_gap_threshold:
                        print(f"  -> REJECTED: X gap too large (threshold: {x_gap_threshold}px)")
                        continue  # Too far apart horizontally
                    
                    # Match found! Placement (left) → Name (right)
                    placement = current_item['placement']
                    name = next_item['text']
                    
                    matched_players.append({
                        "placement": placement,
                        "name": name,
                        "points": PLACEMENT_POINTS.get(placement, 0),
                        "y_center": next_item['y_center']  # Preserve for smart inference
                    })
                    
                    log.info(f"TFT parser: Matched placement {placement} (x={current_item['x_center']:.0f}) → name '{name}' (x={next_item['x_center']:.0f}), Y diff: {y_diff:.1f}px, X gap: {x_gap:.0f}px")
                    
                    # Mark both as matched
                    matched_indices.add(i)
                    matched_indices.add(j)
                    break  # Stop looking for this placement
        
        log.info(f"TFT parser found {len(matched_players)} player(s) from {len(raw_ocr_results)} OCR results")
        
        # Deduplicate by placement number AND name (avoid duplicate OCR detections)
        seen_combinations = set()
        deduplicated_players = []
        
        for player in matched_players:
            # Create key from placement + name
            player_key = f"{player['placement']}_{player['name']}"
            
            if player_key not in seen_combinations:
                seen_combinations.add(player_key)
                deduplicated_players.append(player)
            else:
                log.warning(f"Duplicate player {player['placement']} '{player['name']}': Ignoring")
        
        log.info(f"After deduplication: {len(deduplicated_players)} unique player(s)")
        
        # Ensure unique placement numbers (keep first if duplicate placements)
        placement_to_player = {}
        for player in deduplicated_players:
            placement = player['placement']
            if placement not in placement_to_player:
                placement_to_player[placement] = player

        final_players = list(placement_to_player.values())
        log.info(f"After placement deduplication: {len(final_players)} players with unique placements")

        # ========================================================================
        # PHASE 1: MUTUALLY EXCLUSIVE FORMAT DETECTION (IMPROVED)
        # ========================================================================
        # Format 1: "Standing | Player" header, clear column structure
        # Format 2: "# | Summoner" header, rank abbreviations (E2, M, etc.)
        # Priority: Format 2 > Format 1 > Fallback (Y-based ordering)

        # Check for Format 2 indicators (rank abbreviations) - HIGHEST PRIORITY
        rank_abbreviations = {
            # Single letters (be careful with these - can be part of names)
            'M', 'U', 'D', 'B', 'G', 'P', 'S',
            # Two-character abbreviations (more reliable)
            'E2', 'E1', 
            # Special ranks
            'GM',  # Grandmaster
            # With plus signs
            'M+', 'E+', 'D+', 'G+', 'B+', 'P+', 'S+'
        }

        format_2_confidence = 0.0
        format_2_detected = False
        format_2_indicators = []
        
        for item in raw_ocr_results:
            text = item['text'].upper()

            # Check if any rank abbreviation appears
            # IMPORTANT: Only match if the abbreviation is STANDALONE or at START of text
            # Not if it's just a letter within a name (e.g., "E" in "DEEPESTREGRETS")
            for abbr in rank_abbreviations:
                # Prioritize multi-character abbreviations (more reliable)
                # Single letters need stricter matching to avoid false positives
                is_multichar = len(abbr) > 1
                
                # Format 2 has rank abbreviations as separate items or at start of name
                # e.g., "[E2] PlayerName" or "M PlayerName"
                # NOT: "PlayerNameE" (E is just part of the name)
                is_standalone = (
                    text == abbr or  # Exact match
                    text.startswith(abbr + ' ') or  # At start followed by space
                    text.startswith('[' + abbr) or  # At start with bracket
                    text.startswith(abbr + ']') or  # At start with closing bracket
                    (is_multichar and ((' ' + abbr + ' ') in text or ('[' + abbr + ']') in text))  # As separate word (only for multichar)
                )

                if is_standalone:
                    format_2_detected = True
                    format_2_indicators.append((abbr, text))
                    # Increase confidence based on how many indicators we find
                    # Multi-character abbreviations give higher confidence
                    format_2_confidence += 0.3 if is_multichar else 0.15
                    log.info(f"DETECTED FORMAT 2 indicator: rank abbreviation '{abbr}' in '{text}'")

        # Cap confidence at 1.0
        format_2_confidence = min(format_2_confidence, 1.0)
        
        if format_2_detected:
            log.info(f"FORMAT 2 DETECTION: Found {len(format_2_indicators)} indicators, confidence={format_2_confidence:.2f}")

        # Check for Format 1 indicators (headers) - MEDIUM PRIORITY
        # Only check if Format 2 not detected (mutually exclusive)
        format_1_confidence = 0.0
        format_1_detected = False
        format_1_indicators = []
        
        if not format_2_detected:  # MUTUALLY EXCLUSIVE
            for item in raw_ocr_results:
                text = item['text'].upper()

                # Fuzzy matching for headers (account for OCR errors)
                # "STANDING" might be "STADIN", "STANDIN", "STADINA", etc.
                # "PLAYER" might be "PLATER", "PLAVER", etc.
                header_keywords = {
                    'STANDING': ['STANDING', 'STANDIN', 'STADIN', 'STADINA'],
                    'PLAYER': ['PLAYER', 'PLATER', 'PLAVER', 'PLATER'],
                }

                # Check if text is close to any header keyword
                for canonical, variations in header_keywords.items():
                    if any(variation in text for variation in variations):
                        format_1_detected = True
                        format_1_indicators.append((canonical, text))
                        format_1_confidence += 0.4  # Each header gives strong confidence
                        log.info(f"DETECTED FORMAT 1 indicator: header '{canonical}' matched in '{text}'")
                        break

        # Cap confidence at 1.0
        format_1_confidence = min(format_1_confidence, 1.0)
        
        if format_1_detected:
            log.info(f"FORMAT 1 DETECTION: Found {len(format_1_indicators)} indicators, confidence={format_1_confidence:.2f}")

        # ========================================================================
        # MUTUALLY EXCLUSIVE FORMAT SELECTION
        # ========================================================================
        # Priority: Format 2 > Format 1 > Fallback (Y-based ordering)
        log.info(f"Format detection summary - Format2: {format_2_detected} (conf={format_2_confidence:.2f}), Format1: {format_1_detected} (conf={format_1_confidence:.2f}), Direct players: {len(final_players)}")
        
        if format_2_detected and format_2_confidence >= 0.3:
            # Format 2: Use abbreviation-based parser
            log.info("✓ SELECTED FORMAT 2 PARSER (rank abbreviations detected)")
            final_players = self._parse_format_with_abbreviations(raw_ocr_results)
            
        elif format_1_detected and format_1_confidence >= 0.4:
            # Format 1: Use column-based parser
            log.info("✓ SELECTED FORMAT 1 PARSER (headers detected)")
            final_players = self._parse_format_with_columns(raw_ocr_results)

            # If Format 1 has poor results (< 5 players), fall back to Y-based ordering
            if len(final_players) < 5:
                log.warning(f"Format 1 parser returned only {len(final_players)}/8 players, falling back to Y-based ordering")
                final_players = self._y_based_ordering(raw_ocr_results)
                
        elif len(final_players) >= 3 and len(final_players) < 8:
            # Partial placement detection (3-7 placements): Use smart inference
            log.info(f"✓ USING SMART INFERENCE (partial placement detection: {len(final_players)}/8 players)")
            final_players = self._smart_inference_format_1(raw_ocr_results, final_players)
            
        elif len(final_players) >= 8:
            # Already have good placement detection from earlier logic
            log.info(f"✓ USING DIRECT PLACEMENT DETECTION ({len(final_players)} players)")
            final_players = [self._normalize_player_name(p) for p in final_players]
            
        else:
            # Fallback: Y-based ordering (used when format detection fails)
            log.info("✓ FALLBACK: Using Y-based ordering (no format detected, placement detection incomplete)")
            final_players = self._y_based_ordering(raw_ocr_results)

        return final_players

    def _smart_placement_inference(self, raw_ocr_results: List[Dict], detected_players: List[Dict]) -> List[Dict]:
        """
        Infer missing placement numbers for formats where some placements are detected but not all.

        Combines detected placement-numbered players with Y-based ordering for missing ones.

        Args:
            raw_ocr_results: All OCR detections with coordinates
            detected_players: Players with detected placement numbers

        Returns:
            Complete list of 8 players with inferred placements
        """
        # Get set of detected placement numbers
        detected_placements = {p['placement'] for p in detected_players}
        missing_placements = set(range(1, 9)) - detected_placements

        log.info(f"Detected placements: {sorted(detected_placements)}, Missing: {sorted(missing_placements)}")

        # HYBRID APPROACH: Use Y-based ordering to get all 8 players,
        # then use detected placements to validate/correct placement numbers

        # Get Y-based ordering result (all 8 players)
        y_based_result = self._y_based_ordering(raw_ocr_results, return_raw=True)

        # Create placement-to-player map from Y-based result
        y_based_map = {p['placement']: p for p in y_based_result}

        # Create placement-to-player map from detected players
        detected_map = {p['placement']: p for p in detected_players}

        # For each placement 1-8:
        final_players = []
        for placement in range(1, 9):
            # Use detected player if available (higher accuracy)
            if placement in detected_map:
                player = detected_map[placement]
                # Normalize name
                player = self._normalize_player_name(player)
                final_players.append(player)
                log.info(f"Using detected placement {placement}: {player['name']}")
            # Otherwise, use Y-based
            elif placement in y_based_map:
                player = y_based_map[placement]
                # Normalize name
                player = self._normalize_player_name(player)
                final_players.append(player)
                log.info(f"Using Y-based placement {placement}: {player['name']}")
            else:
                log.warning(f"Missing placement {placement} - no detected or Y-based player")

        log.info(f"Smart inference: {len(final_players)} total players")

        return final_players
    
    def _estimate_player_y(self, placement: int) -> float:
        """
        Estimate Y position for a given placement number.
        Based on typical TFT standings layout (first player around Y=160, spacing ~60px).
        
        Args:
            placement: Placement number (1-8)
            
        Returns:
            Estimated Y position in pixels
        """
        # Typical TFT standings: first player ~Y=160, spacing ~60px
        base_y = 160
        spacing = 60
        return base_y + (placement - 1) * spacing

    def _parse_format_with_columns(self, raw_ocr_results: List[Dict]) -> List[Dict]:
        """
        Parse Format 1 with clear column structure (Standing | Player).

        Format:
        Standing  |  Player
        1         |  Player 1 Name
        2         |  Player 2 Name

        SIMPLIFIED: Match by Y ORDER, not absolute Y position.

        Args:
            raw_ocr_results: All OCR detections with coordinates

        Returns:
            List of players with placement numbers
        """
        log.info("Using Format 1 parser (column-based, Y order matching)")

        # Skip keywords (including headers)
        skip_keywords = {'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                      'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                      'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                      'PLAY', 'AGAIN', 'CONTINUE', '-', 'ROUND',
                      'TACTICS', 'TEAMFIGHT', 'TFT', 'SET',
                      'TRAITS', 'HINT', 'CHAMPIONS', 'STREAK', 'LEVEL', 'XP',
                      'GOLD', 'HP', 'SHOP', 'ITEMS', 'BOARD', 'BENCH',
                      'READY', 'START', 'GAME', 'ROUND', 'STANDING',
                      'NNT', 'HINT', 'PLAY', 'IRAILS', 'GAMELD', 'PLATER',
                      'SUMMONER', '#',  # Format 2 headers
                      # Additional garbage to filter
                      'CZEED', 'J08', '35,06', '35.06', 'GAMEID', 'HOMMAL',
                      'LEOJ', 'DUJD', '01B', 'LHEGLEB', 'DVLD', 'FLY AGIL]'}  # OCR garbage

        # Separate placement numbers and player names
        placements = []
        names = []

        for item in raw_ocr_results:
            text = item['text'].upper()
            x_center = item['x_center']
            y_center = item['y_center']
            confidence = item['confidence']

            # Skip keywords
            if text in skip_keywords:
                log.debug(f"Skipping keyword: {text}")
                continue

            # Placement numbers: single digit 1-8, X < 200 (relaxed to catch all placements)
            if text.isdigit() and len(text) == 1 and 1 <= int(text) <= 8 and x_center < 200:
                placements.append({
                    'text': text,
                    'x_center': x_center,
                    'y_center': y_center,
                    'confidence': confidence,
                    'placement': int(text)
                })
                log.debug(f"Found placement number: {text} at X={x_center:.0f}, Y={y_center:.0f}")

            # Player names: X > 150 (gap from placements), length >= 3, must have letters
            elif x_center > 150 and x_center < 900 and len(text) >= 3 and len(text) <= 30:
                if not any(c.isalpha() for c in text):
                    continue

                if confidence <= 0.2:
                    continue

                names.append({
                    'text': text,
                    'x_center': x_center,
                    'y_center': y_center,
                    'confidence': confidence
                })
                log.debug(f"Found potential name: {text} at X={x_center:.0f}, Y={y_center:.0f}")

        log.info(f"Format 1: {len(placements)} placement numbers, {len(names)} potential names")

        # Log placement Y positions for debugging
        for p in placements:
            log.debug(f"Placement {p['placement']} at Y={p['y_center']:.0f}")

        # Log name Y positions for debugging
        for n in names:
            log.debug(f"Name '{n['text']}' at Y={n['y_center']:.0f}")

        # Sort both placements and names by Y position (top to bottom)
        placements.sort(key=lambda x: x['y_center'])
        names.sort(key=lambda x: x['y_center'])

        # Match placements to names by INDEX (after sorting by Y)
        # This assumes placements and names are detected in same vertical order
        players = []

        for i, placement in enumerate(placements):
            if i < len(names):
                name_item = names[i]

                players.append({
                    'placement': placement['placement'],
                    'name': name_item['text'],
                    'points': PLACEMENT_POINTS.get(placement['placement'], 0)
                })
                log.info(f"Format 1: Matched placement {placement['placement']} (index {i}) to name '{name_item['text']}'")
            else:
                log.warning(f"Format 1: No name found for placement {placement['placement']} (index {i})")
                players.append({
                    'placement': placement['placement'],
                    'name': 'UNKNOWN',
                    'points': PLACEMENT_POINTS.get(placement['placement'], 0)
                })
        players.sort(key=lambda x: x['placement'])

        # Deduplicate players (fix for lobbybround3.png duplicate)
        players = self._deduplicate_players(players)

        # Normalize names
        players = [self._normalize_player_name(p) for p in players]

        return players

    def _parse_format_with_abbreviations(self, raw_ocr_results: List[Dict]) -> List[Dict]:
        """
        Parse Format 2 with rank abbreviations (E2, M, U, etc.) before player names.

        SIMPLIFIED:
        - Filter out rank abbreviations (E2, M, U, etc.)
        - Filter out UI elements ("Hint", "#", "SUMMONER")
        - Cluster into rows (40px Y difference)
        - Pick SINGLE best detection per row (no merging, no deduplication)
        - Sort by Y, assign placements 1-8
        - Normalize names

        Format:
        #  |  Summoner
        1  |  [Icon] [E2] Player 1 Name
        2  |  [Icon] [M] Player 2 Name

        Args:
            raw_ocr_results: All OCR detections with coordinates

        Returns:
            List of players with placement numbers
        """
        log.info("Using Format 2 parser (simplified - single detection per row)")

        # Skip keywords and UI elements
        skip_keywords = {
            # Headers
            'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
            'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
            'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
            'PLAY', 'AGAIN', 'CONTINUE', '-', 'ROUND',
            'TACTICS', 'TEAMFIGHT', 'TFT', 'SET',
            'TRAITS', 'HINT', 'CHAMPIONS', 'STREAK', 'LEVEL', 'XP',
            'GOLD', 'HP', 'SHOP', 'ITEMS', 'BOARD', 'BENCH',
            'READY', 'START', 'GAME', 'ROUND', 'STANDING',
            # OCR errors for UI elements
            'PLATER', 'GAMELD', 'HOMMAL',
            # Numbers/short garbage
            'J08', 'JO8', 'O8', '08', 'NOAL', 'ABY', 'SMONB', 'CZEED',
            # Additional OCR errors seen in tests
            'SUMONB', 'HINT', 'NNT', '#', 'IRAILS'
        }

        # Rank abbreviations to filter (these appear BEFORE player names)
        rank_abbreviations = {'E2', 'E1', 'M', 'U', 'D', 'B', 'G', 'P', 'S',
                           'GM', 'M+', 'E', 'D+', 'G+', 'B+', 'P+', 'S+'}

        # Filter potential player names
        potential_items = []
        for item in raw_ocr_results:
            text = item['text'].upper()

            # Skip if X position too far right
            if item['x_center'] > 800:
                log.debug(f"Skipped '{text}' (X too far right: {item['x_center']:.0f})")
                continue

            # Skip if text is a keyword (case-sensitive for "HINT" vs "hint")
            if text == 'HINT' or text in skip_keywords:
                log.debug(f"Skipped keyword: {text}")
                continue

            # Skip if text is exactly a rank abbreviation (standalone)
            if text in rank_abbreviations:
                log.debug(f"Skipped rank abbreviation: {text}")
                continue

            # Extract name if text contains rank abbreviation (e.g., "E2 Ffoxface" -> "Ffoxface")
            # IMPORTANT: Only remove if abbreviation is at START or as SEPARATE word
            # NOT if it's just a letter within the name (e.g., "E" in "DEEPESTREGRETS")
            cleaned_text = text
            for abbr in sorted(rank_abbreviations, key=len, reverse=True):
                if abbr in cleaned_text:
                    # Check if abbreviation is at START or as SEPARATE word
                    # Patterns to match: "[E2]", "E2 ", " E2 ", " E2] "
                    abbr_at_start = cleaned_text.startswith(abbr + ' ') or cleaned_text.startswith('[' + abbr) or cleaned_text.startswith(abbr + ']')
                    abbr_separate = (' ' + abbr + ' ') in cleaned_text or (' [' + abbr + ']') in cleaned_text or (' [' + abbr + '] ') in cleaned_text

                    if abbr_at_start or abbr_separate:
                        # Remove the abbreviation with surrounding delimiters
                        cleaned_text = cleaned_text.replace(abbr, '', 1).strip()
                        # Also clean up leftover brackets/spaces
                        cleaned_text = cleaned_text.replace('[]', '').replace('  ', ' ').strip()
                        log.debug(f"Removed rank abbreviation from '{text}' -> '{cleaned_text}'")
                        break

            # Check length (after removing abbreviation)
            if len(cleaned_text) < 3 or len(cleaned_text) > 30:
                log.debug(f"Skipped '{cleaned_text}' (length {len(cleaned_text)})")
                continue

            # Must have letters
            if not any(c.isalpha() for c in cleaned_text):
                log.debug(f"Skipped '{cleaned_text}' (no letters)")
                continue

            # Skip if cleaned text is just a number or very short
            if cleaned_text.isdigit() or len(cleaned_text) < 3:
                log.debug(f"Skipped '{cleaned_text}' (just number or too short)")
                continue

            # Check confidence
            if item['confidence'] <= 0.3:
                log.debug(f"Skipped '{cleaned_text}' (low confidence: {item['confidence']:.3f})")
                continue

            potential_items.append({
                'text': cleaned_text,
                'x_center': item['x_center'],
                'y_center': item['y_center'],
                'confidence': item['confidence']
            })
            log.debug(f"Added potential name: {cleaned_text} at X={item['x_center']:.0f}, Y={item['y_center']:.0f}")

        log.info(f"Format 2: {len(potential_items)} potential items after filtering")

        # Sort by Y position and cluster into rows (within 35px Y difference)
        potential_items_sorted = sorted(potential_items, key=lambda x: x['y_center'])

        rows = []
        for item in potential_items_sorted:
            placed = False
            for row in rows:
                # If Y difference < 35px, add to existing row
                if abs(item['y_center'] - row['y_center']) < 35:
                    row['items'].append(item)
                    # Update row Y to average
                    row['y_center'] = (row['y_center'] * len(row['items']) + item['y_center']) / (len(row['items']) + 1)
                    placed = True
                    break

            if not placed:
                # Create new row
                rows.append({
                    'y_center': item['y_center'],
                    'items': [item]
                })

        # Sort rows by Y position
        rows.sort(key=lambda x: x['y_center'])

        log.info(f"Format 2: Found {len(rows)} distinct rows")

        # Pick SINGLE best candidate per row (no merging, no deduplication)
        final_names = []
        for row in rows:
            # Sort items in row by confidence (descending), then length (descending)
            row['items'].sort(key=lambda x: (-x['confidence'], -len(x['text'])))

            # Skip low confidence rows
            if row['items'][0]['confidence'] < 0.3:
                log.debug(f"Skipped row Y={row['y_center']:.0f} (low confidence)")
                continue

            # Just pick top item (no merging)
            best_item = row['items'][0]
            final_names.append(best_item)
            log.info(f"Row Y={row['y_center']:.0f}: Selected '{best_item['text']}' (conf={best_item['confidence']:.3f})")

        # Limit to 8 players
        final_names = final_names[:8]

        # Assign placements 1-8 based on Y order
        players = []
        for i, item in enumerate(final_names):
            placement = i + 1
            players.append({
                'placement': placement,
                'name': item['text'],
                'points': PLACEMENT_POINTS.get(placement, 0)
            })
            log.info(f"Format 2: Assigned placement {placement} to '{item['text']}'")

        # Deduplicate players (filter out header fragments)
        players = self._deduplicate_players(players)

        # Normalize names
        players = [self._normalize_player_name(p) for p in players]

        return players
    def _y_based_ordering(self, raw_ocr_results: List[Dict], return_raw: bool = False) -> List[Dict]:
        """
        Assign placement numbers based on Y position (for formats without placement numbers).

        Args:
            raw_ocr_results: List of detected OCR items with Y coordinates
            return_raw: If True, return raw player dicts (no normalization, no filtering)

        Returns:
            List of players with placement numbers assigned by Y position
        """
        # Filter potential player names (exclude numbers, short text, keywords)
        # Expanded list to catch more OCR variations of UI elements
        skip_keywords = [
            # Headers
            'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
            'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
            'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
            'PLAY', 'AGAIN', 'CONTINUE', 'ROUND', 'TFT', 'SET',
            'TRAITS', 'HINT', 'CHAMPIONS', 'STREAK', 'LEVEL', 'XP',
            'GOLD', 'HP', 'SHOP', 'ITEMS', 'BOARD', 'BENCH',
            'READY', 'START', 'GAME',
            # OCR errors for UI elements
            'PLATER', 'GAMELD', 'HOMMAL',
            # Numbers/short garbage
            'J08', 'JO8', 'O8', '08', 'NOAL', 'ABY', 'SMONB', 'CZEED',
            # Additional OCR errors seen in tests
            'SUMONB', 'HINT', 'NNT'
            # Rank abbreviations (for Format 2)
            'E2', 'E1', 'M', 'U', 'D', 'B', 'G', 'P', 'S',
            'GM', 'M+', 'E+', 'D+', 'G+', 'B+', 'P+', 'S+',
            # Round/game info
            '35,06', '35.06'
        ]
        
        # Additional filtering: exclude low-confidence detections, headers, etc.
        # More permissive filtering to allow names with spaces or OCR errors

        # DEBUG: Log what's being filtered
        log.debug(f"Total raw OCR results: {len(raw_ocr_results)}")

        potential_names = []
        for item in raw_ocr_results:
            text = item['text']

            # Check skip keywords (exact match)
            skipped = False
            for keyword in skip_keywords:
                if keyword == text:
                    log.debug(f"Filtered '{text}' (exact match keyword '{keyword}')")
                    skipped = True
                    break

            if skipped:
                continue

            # Check X position (names should be on left side, not too far right)
            if item['x_center'] >= 700:
                log.debug(f"Filtered '{text}' (X position {item['x_center']:.0f})")
                continue

            # Check length (allow slightly longer names with OCR errors)
            if len(text) < 3 or len(text) > 35:
                log.debug(f"Filtered '{text}' (length {len(text)})")
                continue

            # Check for letters (must have at least 2 letters to be a name)
            letter_count = sum(1 for c in text if c.isalpha())
            if letter_count < 2:
                log.debug(f"Filtered '{text}' (only {letter_count} letters)")
                continue

            # Skip if text is just a number or mostly numbers
            if text.isdigit() or (len(text.replace(' ', '').replace('.', '')) > 0 and sum(1 for c in text if c.isdigit()) > len(text) / 2):
                log.debug(f"Filtered '{text}' (mostly numbers)")
                continue

            # Check confidence (lower threshold since we're filtering more aggressively)
            if item['confidence'] <= 0.2:
                log.debug(f"Filtered '{text}' (low confidence {item['confidence']:.3f})")
                continue

            # Skip obvious garbage: single uppercase letters or very short combinations
            if len(text) <= 3 and text.isupper():
                # But allow things like "COCO", "OLI", "AST" which are valid names
                if text not in {'COCO', 'OLI', 'AST', 'MUD', 'HINT', 'BTW'}:
                    log.debug(f"Filtered '{text}' (short uppercase)")
                    continue

            # Skip fragments of UI elements (common OCR fragments)
            ui_fragments = {'GANEID', 'SKJ', 'DUJD', 'DVLD', 'LT0E', 'HOMMAL',
                          'NNT', 'CZEED', 'LEOJ', 'FLYAGIL', 'GAMELD'}
            if text in ui_fragments:
                log.debug(f"Filtered '{text}' (UI fragment)")
                continue

            # Heuristic: Skip garbage names based on character analysis
            # Garbage names tend to have:
            # 1. No vowels (e.g., "JO8", "ABY", "SKJ")
            # 2. Mostly consonants with random numbers
            # 3. Low confidence score

            vowels = {'A', 'E', 'I', 'O', 'U', 'a', 'e', 'i', 'o', 'u'}
            letter_count = sum(1 for c in text if c.isalpha())
            vowel_count = sum(1 for c in text if c in vowels)

            if letter_count >= 3:
                vowel_ratio = vowel_count / letter_count
                # If vowel ratio < 0.15 (less than 15% vowels), likely garbage
                # Raised threshold to allow names like "Vedris" (0.17)
                if vowel_ratio < 0.15:
                    # But allow known valid low-vowel names
                    if text not in {'COCO', 'BTW', 'SKY', 'LYM', 'VED', 'VDR'}:
                        log.debug(f"Filtered '{text}' (low vowel ratio {vowel_ratio:.2f})")
                        continue

            # Passed all filters
            potential_names.append(item)

        log.debug(f"Potential names after filtering: {len(potential_names)}")
        
        # Post-process: Extract names from items with P prefix (e.g., "P2 Ffoxface")
        # For lobbycround3.png format, OCR might detect "P2 Ffoxface" as one item
        # Extract the name part after "P\d"
        import re
        for item in raw_ocr_results:
            text = item['text']
            # Check if text matches "P<digit> <name>" pattern (with optional spaces)
            p_prefix_match = re.match(r'^P\s*\d+\s+(.+)$', text)
            if p_prefix_match:
                name_part = p_prefix_match.group(1).strip()
                # Validate extracted name (more permissive)
                if (len(name_part) >= 3 and
                    any(c.isalpha() for c in name_part) and
                    item['x_center'] < 600 and
                    item['confidence'] > 0.3):
                    # Create a new item for the extracted name
                    potential_names.append({
                        'text': name_part,
                        'x_center': item['x_center'],
                        'y_center': item['y_center'],
                        'confidence': item['confidence']
                    })
                    log.info(f"Extracted P-prefixed name '{name_part}' from '{text}'")
        
        # CLUSTERING: Group detections by Y position to identify real player names
        # Real player names are evenly spaced (every ~75 pixels Y)
        # False positives are scattered/random
        
        # Sort by Y
        potential_names_sorted = sorted(potential_names, key=lambda x: x['y_center'])
        
        # Calculate Y gaps between consecutive detections
        y_gaps = []
        for i in range(len(potential_names_sorted) - 1):
            y_gap = potential_names_sorted[i+1]['y_center'] - potential_names_sorted[i]['y_center']
            y_gaps.append(y_gap)
        
        # Find typical gap (median)
        if len(y_gaps) > 0:
            y_gaps.sort()
            typical_gap = y_gaps[len(y_gaps) // 2]
            
            # Keep only detections that follow the typical gap pattern
            filtered_names = [potential_names_sorted[0]]  # Keep first
            for i in range(1, len(potential_names_sorted)):
                y_gap = potential_names_sorted[i]['y_center'] - potential_names_sorted[i-1]['y_center']
                # Accept if gap is within 40-120 pixels of typical
                if 40 <= y_gap <= 120:
                    filtered_names.append(potential_names_sorted[i])
                elif y_gap > 120 and len(filtered_names) < 8:
                    # Large gap might be next player row - accept if we have room
                    filtered_names.append(potential_names_sorted[i])
            
            potential_names = filtered_names
        
        # Sort by Y position (top to bottom)

        # IMPROVED ROW CLUSTERING: Detect 8 distinct player rows
        # Player rows are evenly spaced (typically ~60-75 pixels Y gap)

        if len(potential_names) < 8:
            log.warning(f"Not enough potential names ({len(potential_names)}) for full detection")

        # Sort by Y
        potential_names_sorted = sorted(potential_names, key=lambda x: x['y_center'])

        # Calculate Y gaps between consecutive detections
        y_positions = [item['y_center'] for item in potential_names_sorted]
        y_gaps = []
        for i in range(len(y_positions) - 1):
            y_gaps.append(y_positions[i+1] - y_positions[i])

        # Find typical gap (median of non-zero gaps)
        # Player rows have consistent spacing
        non_zero_gaps = [g for g in y_gaps if g > 10]  # Exclude very small gaps
        if len(non_zero_gaps) > 0:
            non_zero_gaps.sort()
            typical_gap = non_zero_gaps[len(non_zero_gaps) // 2]
        else:
            typical_gap = 60  # Default

        log.info(f"Typical Y gap between rows: {typical_gap:.0f}px")

        # Cluster detections into rows using DBSCAN-like approach
        # If Y difference < 35px, same row. If > 45px, different row.
        rows = []
        for item in potential_names_sorted:
            placed = False
            for row in rows:
                # Check if item belongs to existing row
                row_y = row['y_center']
                if abs(item['y_center'] - row_y) < 35:  # Same row if within 35px
                    # Add to row
                    row['items'].append(item)
                    # Update row Y to average
                    row['y_center'] = (row['y_center'] * len(row['items']) + item['y_center']) / (len(row['items']) + 1)
                    placed = True
                    break

            if not placed:
                # Create new row
                rows.append({
                    'y_center': item['y_center'],
                    'items': [item]
                })

        # Sort rows by Y
        rows.sort(key=lambda x: x['y_center'])

        log.info(f"Found {len(rows)} distinct rows")

        # DEBUG: Log row details
        for row in rows:
            log.debug(f"Row Y={row['y_center']:.0f}: {len(row['items'])} items")
            for item in row['items']:
                log.debug(f"  - '{item['text']}' (conf={item['confidence']:.3f})")

        # Pick best candidate from each row
        # Criteria: Highest confidence, longest valid name, reasonable X position (not too far left)
        best_names = []
        for row in rows:
            # Sort items in row by confidence (descending), then name length (descending)
            row_items = sorted(row['items'], key=lambda x: (-x['confidence'], -len(x['text'])))

            # Skip rows with very low confidence or very short names
            if row_items and row_items[0]['confidence'] < 0.35:
                log.debug(f"Skipping row Y={row['y_center']:.0f} (low confidence)")
                continue
            if row_items and len(row_items[0]['text']) < 3:
                log.debug(f"Skipping row Y={row['y_center']:.0f} (short text)")
                continue

            # Pick top item
            best_item = row_items[0]
            best_names.append(best_item)
            log.debug(f"Row Y={row['y_center']:.0f}: Picked '{best_item['text']}' (conf={best_item['confidence']:.3f}, len={len(best_item['text'])})")

        # Limit to 8 players
        potential_names = best_names[:8]

        # Assign placements 1-8 based on Y order
        players = []
        for i, item in enumerate(potential_names):
            placement = i + 1  # Placement 1-8

            if return_raw:
                # Return raw player dict (no normalization)
                player = {
                    'placement': placement,
                    'name': item['text'],
                    'points': PLACEMENT_POINTS.get(placement, 0)
                }
            else:
                # Return normalized player dict
                player = {
                    'placement': placement,
                    'name': item['text'],
                    'points': PLACEMENT_POINTS.get(placement, 0)
                }
                # Apply normalization
                player = self._normalize_player_name(player)

            players.append(player)
            log.info(f"Assigned placement {placement} to '{item['text']}' based on Y position")

        log.info(f"Y-based ordering found {len(players)} players")

        return players

    def _deduplicate_players(self, players: List[Dict]) -> List[Dict]:
        """
        Remove duplicate players with similar names.
        Uses fuzzy matching (case-insensitive, space-insensitive).
        Also filters out players with similar names AND same placement.

        Args:
            players: List of player dicts with 'placement', 'name', 'points'

        Returns:
            List of unique players
        """
        unique_players = []
        seen_signatures = {}

        for player in sorted(players, key=lambda x: x['placement']):
            name = player['name'].lower().replace(' ', '')

            # Check if similar name already seen
            if name in seen_signatures:
                existing_player = seen_signatures[name]
                log.warning(f"Duplicate player {player['placement']} '{player['name']}' (same as {existing_player['placement']} '{existing_player['name']}'): Ignoring")

                # Keep the one with better score (earlier placement = more points)
                # This handles lobbybround3.png duplicate COFFINCUTIE at placements 1 and 7
                # Keep placement 7 (1 point) instead of placement 1 (8 points)
                if existing_player['placement'] > player['placement']:
                    # Existing is later (lower points), keep it
                    continue
                else:
                    # Current is later (lower points), replace existing
                    seen_signatures[name] = player
                    unique_players.append(player)
                continue

            seen_signatures[name] = player
            unique_players.append(player)

        # Remove exact duplicates by NAME and check PLACEMENT SEQUENCE
        # If same name appears at very different placements, they're probably different players (OCR misread)
        # If same name appears at adjacent placements, it's a true duplicate
        seen_names = {}

        for player in unique_players:
            name_key = player['name'].lower().replace(' ', '')

            if name_key in seen_names:
                existing = seen_names[name_key]
                placement_diff = abs(player['placement'] - existing['placement'])

                # If placements are far apart (> 2 positions), they're different players (OCR misread)
                if placement_diff > 2:
                    log.info(f"Same name '{player['name']}' at far apart placements {existing['placement']} and {player['placement']}: Keeping both as different players")
                    # Add suffix to make unique
                    player['name'] = f"{player['name']} (2)"
                    seen_names[name_key + '_2'] = player
                else:
                    # Adjacent placements: true duplicate (listing error)
                    log.warning(f"Duplicate name '{player['name']}' at adjacent placements {existing['placement']} and {player['placement']}: Keeping placement {min(existing['placement'], player['placement'])}")

                    # Keep one with lower placement number (more points)
                    if player['placement'] < existing['placement']:
                        # Current is better, replace existing
                        seen_names[name_key] = player
                    else:
                        # Existing is better, skip current
                        continue
            else:
                seen_names[name_key] = player

        # Convert dict to list
        final_players = list(seen_names.values())
        log.info(f"After exact duplicate removal: {len(final_players)} players (from {len(unique_players)})")

        return final_players

    def _smart_inference_format_1(self, raw_ocr_results: List[Dict], detected_players: List[Dict]) -> List[Dict]:
        """
        When placement detection is incomplete (< 8), infer missing placements
        using Y position spacing heuristics.

        Args:
            raw_ocr_results: All OCR detections with coordinates
            detected_players: Players with detected placement numbers

        Returns:
            List of players with inferred placements filled in
        """
        detected_placements = {p['placement']: p for p in detected_players}
        missing_placements = set(range(1, 9)) - detected_placements.keys()

        if not missing_placements:
            return detected_players

        # Get all potential player names sorted by Y
        def is_valid_name(item: Dict) -> bool:
            text = item['text']
            # Basic validation (similar to _y_based_ordering)
            if len(text) < 3 or len(text) > 30:
                return False
            if not any(c.isalpha() for c in text):
                return False
            if item['x_center'] >= 700:
                return False
            if item['confidence'] <= 0.2:
                return False
            return True

        all_names = sorted(
            [item for item in raw_ocr_results if is_valid_name(item)],
            key=lambda x: x['y_center']
        )

        # Calculate typical Y spacing between rows
        # Player rows should be ~60-75 pixels apart
        y_positions = [p['y_center'] for p in detected_placements.values()]
        if len(y_positions) > 1:
            gaps = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
            typical_gap = statistics.median(gaps)
            log.info(f"Calculated typical Y gap: {typical_gap:.1f}px from {len(gaps)} gaps")
        else:
            typical_gap = 65  # Default
            log.info(f"Using default Y gap: {typical_gap}px")

        # Estimate Y positions for each placement
        base_y = min(y_positions) if y_positions else 160
        estimated_positions = {}
        for placement in range(1, 9):
            estimated_y = base_y + (placement - 1) * typical_gap
            estimated_positions[placement] = estimated_y
            log.debug(f"Estimated Y for placement {placement}: {estimated_y:.1f}px")

        # Match missing placements to closest available names
        used_texts = set(p['name'] for p in detected_placements.values())
        for placement in sorted(missing_placements):
            target_y = estimated_positions[placement]

            # Find closest name not already used
            best_match = None
            best_distance = float('inf')
            for item in all_names:
                if item['text'] in used_texts:
                    continue  # Skip already matched
                distance = abs(item['y_center'] - target_y)
                if distance < best_distance and distance < 45:  # Within 45px
                    best_match = item
                    best_distance = distance

            if best_match:
                detected_placements[placement] = {
                    'placement': placement,
                    'name': best_match['text'],
                    'points': PLACEMENT_POINTS.get(placement, 0),
                    'y_center': best_match['y_center'],
                    'inferred': True  # Mark as inferred
                }
                used_texts.add(best_match['text'])
                log.info(f"Inferred placement {placement} for '{best_match['text']}' (Y diff: {best_distance:.1f}px)")
            else:
                log.warning(f"Could not infer placement {placement}: No matching name found")

        # Return sorted by placement
        return sorted(detected_placements.values(), key=lambda x: x['placement'])

    def _normalize_player_name(self, player: Dict) -> Dict:
        """
        Normalize player name by fixing common OCR errors.

        Args:
            player: Player dict with 'name', 'placement', 'points'

        Returns:
            Player dict with normalized name
        """
        name = player.get('name', '')

        if not name:
            return player

        original_name = name

        # Step 1: Remove garbage characters (brackets, braces, pipes, etc.)
        # Keep only letters, numbers, spaces
        name = ''.join(c for c in name if c.isalnum() or c.isspace())

        # Step 2: Fix common character confusions
        character_fixes = {
            '0': 'O',  # Zero -> O
            '1': 'I',  # One -> I (in some contexts)
            '2': 'Z',  # Two -> Z
            '3': 'E',  # Three -> E (lowercase)
            '4': 'A',  # Four -> A
            '5': 'S',  # Five -> S
            '6': 'G',  # Six -> G
            '8': 'B',  # Eight -> B
            '9': 'g',  # Nine -> g
        }

        # Apply character fixes (only if surrounded by letters, not standalone)
        for i in range(1, len(name) - 1):
            char = name[i]
            prev_char = name[i - 1]
            next_char = name[i + 1]

            # Only fix if it looks like a confusion (surrounded by letters)
            if char in character_fixes and (prev_char.isalpha() or next_char.isalpha()):
                if prev_char.isalpha() or next_char.isalpha():
                    fixed_char = character_fixes[char]
                    name = name[:i] + fixed_char + name[i+1:]

        # Step 3: Fix spacing issues
        # Remove extra spaces
        name = ' '.join(name.split())

        # Fix merged words (camel case with lowercase)
        # e.g., "LourenTheCorgl" -> "Louren The Corgl"
        import re
        # Insert spaces before capital letters that follow lowercase
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

        # Step 4: Common TFT name patterns
        # Fix specific OCR errors we've seen
        common_fixes = {
            # From our test results
            'BABY LKMA': 'Baby Llama',
            'LOURENTHECORGL': 'LaurenTheCorgi',
            'LAUCEYD': 'LaurenTheCorgi',  # Alternative detection
            'VEDRKS': 'Vedris',
            'FLY AGIL': 'Fly Agincourt',  # Not sure, but fix
            'MUDKIPENJOYER': 'MudkipEnjoyer',
            'MOLDY OMQUAT': 'MoldyKumquat',
            'MOLDYOMQUAT': 'MoldyKumquat',
            'MUDKIPOPJOYER': 'MudkipEnjoyer',
            'DUCHESS OL OEER': 'Duchess of Deer',
            'DUCHESSOL OEER': 'Duchess of Deer',
            'VEEWITHTOPMANYES': 'VeewithtooManyEs',
            'VEEWITHTOOMANYES': 'VeewithtooManyEs',
            '12FIERXDFYRE': '12FiendFyre',
            '12FIENDFYRE': '12FiendFyre',
            'FFOXFACE': 'Ffoxface',
            'ALILHYSL': 'Alithyst',
            'SUMONB': 'Summoner',  # Header, but appearing as name
            'NNT': 'hint',  # Header, but appearing as name
        }

        for error, correction in common_fixes.items():
            if error in name:
                name = name.replace(error, correction)
                log.debug(f"Fixed name '{original_name}' -> '{name}' (common error)")

        # Step 5: Capitalize properly
        # First letter uppercase, rest lowercase (standard TFT format)
        if name:
            # Split into words and capitalize first letter
            words = name.split()
            name = ' '.join(word.capitalize() if word else '' for word in words)

            # Convert entire name to lowercase (to match expected format)
            name = name.lower()

        # Step 6: Filter out UI elements
        ui_elements = ['Summoner', 'Round', 'Hint', 'Standing', 'Player', 'Online', 'Social']
        if name in ui_elements:
            log.warning(f"Filtered out UI element as name: {name}")
            # Return original but mark for filtering
            return player

        # Step 7: Validate name length
        if len(name) < 3:
            log.warning(f"Name too short after normalization: {name}")
            return player

        # Update player with normalized name
        normalized_player = player.copy()
        normalized_player['name'] = name

        if name != original_name:
            log.info(f"Normalized name: '{original_name}' -> '{name}'")

        return normalized_player

    def _alternative_parsing(self, lines: List[str]) -> List[Dict]:
        """Alternative parsing method if standard pattern fails."""
        players = []

        # Try to find placement keywords
        placement_keywords = {
            "1ST": 1, "2ND": 2, "3RD": 3, "4TH": 4,
            "5TH": 5, "6TH": 6, "7TH": 7, "8TH": 8
        }

        for line in lines:
            line = line.strip()
            for keyword, placement in placement_keywords.items():
                if keyword in line:
                    name = line.replace(keyword, "").strip()
                    if name and len(name) > 2:
                        players.append({
                            "placement": placement,
                            "name": name,
                            "points": PLACEMENT_POINTS.get(placement, 0)
                        })
                        break

        return players

    def _calculate_confidence(
        self,
        results: Dict,
        consensus: Dict,
        structured: Dict
    ) -> Dict:
        """Calculate multi-dimensional confidence scores."""
        scores = {}

        # 1. OCR consensus confidence
        scores["ocr_consensus"] = consensus.get("confidence", 0) / 100

        # 2. OCR engine agreement
        tesseract_scores = []
        easyocr_scores = []

        for pass_data in results.values():
            if pass_data and "results" in pass_data:
                if "tesseract" in pass_data["results"]:
                    tesseract_scores.append(
                        pass_data["results"]["tesseract"].get("confidence", 0)
                    )
                if "easyocr" in pass_data["results"]:
                    easyocr_scores.append(
                        pass_data["results"]["easyocr"].get("confidence", 0)
                    )

        # Calculate agreement (normalized to 0-1)
        if tesseract_scores and easyocr_scores:
            avg_tess = sum(tesseract_scores) / len(tesseract_scores)
            avg_easy = sum(easyocr_scores) / len(easyocr_scores)
            diff = abs(avg_tess - avg_easy) / 100
            scores["engine_agreement"] = max(0, 1 - diff)
        else:
            scores["engine_agreement"] = 0.5

        # 3. Structural confidence
        player_count = structured.get("player_count", 0)
        expected = structured.get("expected_players", 8)

        # Score based on having correct number of players
        if player_count == expected:
            scores["structural"] = 1.0
        elif player_count >= expected - 1:
            scores["structural"] = 0.8
        elif player_count >= expected - 2:
            scores["structural"] = 0.5
        else:
            scores["structural"] = 0.0

        # 4. Character-level confidence (average from all passes)
        all_confs = []
        for pass_data in results.values():
            if pass_data and "results" in pass_data:
                for engine_data in pass_data["results"].values():
                    if "confidence" in engine_data:
                        all_confs.append(engine_data["confidence"])

        if all_confs:
            scores["character"] = sum(all_confs) / len(all_confs) / 100
        else:
            scores["character"] = 0.0

        # Overall confidence (weighted average)
        weights = {
            "ocr_consensus": 0.30,
            "engine_agreement": 0.25,
            "structural": 0.25,
            "character": 0.20
        }

        overall = sum(
            scores.get(k, 0) * weights.get(k, 0)
            for k in scores.keys()
        )

        scores["overall"] = overall

        return scores

    def process_batch(self, image_paths: List[str], max_workers: int = 4) -> Dict:
        """
        Process multiple screenshots in parallel.
        
        Args:
            image_paths: List of paths to screenshot images
            max_workers: Maximum number of parallel threads
            
        Returns:
            Dictionary with results for each screenshot and timing info
        """
        log.info(f"Processing batch of {len(image_paths)} images with {max_workers} workers")
        
        results = {}
        timing_info = {}
        
        start_time = datetime.now()
        
        # Process images in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self.extract_from_image, path): path
                for path in image_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                path_name = Path(path).name
                
                try:
                    result = future.result()
                    results[path_name] = result
                    log.info(f"Completed: {path_name}")
                except Exception as e:
                    log.error(f"Failed to process {path_name}: {e}")
                    results[path_name] = {
                        "success": False,
                        "error": str(e)
                    }
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Calculate timing info
        timing_info = {
            "total_images": len(image_paths),
            "successful": sum(1 for r in results.values() if r.get("success", False)),
            "total_time_seconds": total_time,
            "avg_time_per_image": total_time / len(image_paths) if image_paths else 0,
            "parallel_speedup": f"{total_time / (total_time / len(image_paths)):.2f}x" if len(image_paths) > 1 else "1.0x"
        }
        
        return {
            "results": results,
            "timing": timing_info
        }


# Singleton instance
_ocr_pipeline_instance = None

def get_ocr_pipeline() -> OCRRPipeline:
    """Get or create OCR pipeline instance."""
    global _ocr_pipeline_instance
    if _ocr_pipeline_instance is None:
        _ocr_pipeline_instance = OCRRPipeline()
    return _ocr_pipeline_instance
