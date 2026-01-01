"""
Batch Processor - Concurrent processing of multiple screenshots.

Handles batch queue, parallel execution, and progress tracking.
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging
import requests
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from api.models import (
    Base, ProcessingBatch, PlacementSubmission,
    RoundPlacement
)
from api.dependencies import get_db, engine
from api.models import utc_now

from integrations.screenshot_classifier import get_classifier
from integrations.cloud_vision_ocr import get_cloud_vision_ocr  # Use Google Cloud Vision (100% accurate!)
from integrations.player_matcher import get_player_matcher
from integrations.placement_validator import get_validator

from config import _FULL_CFG

log = logging.getLogger(__name__)


class BatchProcessor:
    """Processes screenshots in batches with parallel execution."""

    def __init__(self):
        settings = _FULL_CFG.get("standings_screenshots", {})

        self.batch_window = settings.get("batch_window_seconds", 30)
        self.max_concurrent = settings.get("max_concurrent_processing", 4)
        self.auto_validate_threshold = settings.get("auto_validate_threshold", 0.98)

        log.info(
            f"BatchProcessor initialized (window: {self.batch_window}s, "
            f"max_concurrent: {self.max_concurrent})"
        )

    def _download_image(self, url: str) -> Optional[Path]:
        """
        Download image from Discord URL to temporary file.

        Args:
            url: Discord CDN URL

        Returns:
            Path to downloaded file, or None if download failed
        """
        try:
            # Create temp directory if needed
            temp_dir = Path(tempfile.gettempdir()) / "tft_screenshots"
            temp_dir.mkdir(exist_ok=True)

            # Generate unique filename
            filename = f"tft_{uuid.uuid4().hex}.png"
            temp_path = temp_dir / filename

            # Download image
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Write to temp file
            temp_path.write_bytes(response.content)

            log.debug(f"Downloaded image: {url} -> {temp_path}")
            return temp_path

        except Exception as e:
            log.error(f"Failed to download image {url}: {e}")
            return None

    async def process_batch(
        self,
        images: List[Dict],
        tournament_id: str,
        guild_id: str,
        round_name: str
    ) -> Dict:
        """
        Process a batch of screenshots.

        Args:
            images: List of image data dicts
                [{
                    "url": str,
                    "discord_message_id": str,
                    "discord_channel_id": str,
                    "discord_author_id": str,
                    "round_name": str (optional),
                    "lobby_number": int (optional)
                }]
            tournament_id: Tournament identifier
            guild_id: Discord guild ID
            round_name: Round name (optional)

        Returns:
            Batch processing result
        """
        if not images:
            return {"success": False, "error": "No images to process"}

        try:
            # Create batch record
            batch_result = await self._create_batch(
                guild_id, tournament_id, round_name, images
            )

            batch_id = batch_result["batch_id"]

            log.info(f"Processing batch {batch_id} with {len(images)} images")

            # Process images in parallel
            tasks = [
                self._process_single_image(
                    img, batch_id, guild_id, tournament_id, round_name
                )
                for img in images
            ]

            # Limit concurrent processing
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def limited_task(task):
                async with semaphore:
                    return await task

            limited_tasks = [limited_task(t) for t in tasks]
            results = await asyncio.gather(*limited_tasks, return_exceptions=True)

            # Process results
            completed = 0
            validated = 0
            errors = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    log.error(f"Image {i} processing error: {result}")
                    errors += 1
                else:
                    if result.get("success", False):
                        completed += 1
                        if result.get("validated", False):
                            validated += 1
                    else:
                        errors += 1

            # Update batch record
            await self._update_batch(
                batch_id, completed, validated, errors
            )

            # Cross-lobby validation if multiple lobbies
            if completed > 1:
                await self._cross_lobby_validate(batch_id)

            # Calculate batch average confidence
            avg_confidence = await self._calculate_batch_confidence(batch_id)

            log.info(
                f"Batch {batch_id} complete: {completed} processed, "
                f"{validated} validated, {errors} errors, "
                f"avg confidence: {avg_confidence:.3f}"
            )

            return {
                "success": True,
                "batch_id": batch_id,
                "total_images": len(images),
                "completed": completed,
                "validated": validated,
                "errors": errors,
                "average_confidence": avg_confidence,
                "results": results
            }

        except Exception as e:
            log.error(f"Batch processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_batch(
        self,
        guild_id: str,
        tournament_id: str,
        round_name: str,
        images: List[Dict]
    ) -> Dict:
        """Create batch record in database."""
        db = next(get_db())

        try:
            batch = ProcessingBatch(
                guild_id=guild_id,
                tournament_id=tournament_id,
                round_name=round_name,
                batch_size=len(images),
                status="processing"
            )

            db.add(batch)
            db.commit()
            db.refresh(batch)

            log.info(f"Created batch record: {batch.id}")

            return {"batch_id": batch.id}

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    async def _update_batch(
        self,
        batch_id: int,
        completed: int,
        validated: int,
        errors: int
    ):
        """Update batch progress."""
        db = next(get_db())

        try:
            batch = db.query(ProcessingBatch).filter(
                ProcessingBatch.id == batch_id
            ).first()

            if batch:
                batch.completed_count = completed
                batch.validated_count = validated
                batch.error_count = errors

                if completed >= batch.batch_size:
                    batch.status = "completed"
                    batch.completed_at = datetime.utcnow()

                db.commit()

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    async def _process_single_image(
        self,
        image_data: Dict,
        batch_id: int,
        guild_id: str,
        tournament_id: str,
        round_name: str
    ) -> Dict:
        """Process a single screenshot through the pipeline."""
        temp_path = None
        try:
            # Step 0: Download image from Discord URL
            temp_path = self._download_image(image_data["url"])
            if temp_path is None:
                log.error(
                    f"Failed to download image for processing: {image_data['discord_message_id']}"
                )
                return {
                    "success": False,
                    "reason": "download_failed",
                    "message_id": image_data["discord_message_id"]
                }

            # Step 1: Classify screenshot (with channel name for trusted bypass)
            classifier = get_classifier()
            channel_name = image_data.get("channel_name")
            is_standings, classification_confidence, _ = classifier.classify(
                str(temp_path), channel_name=channel_name
            )

            if not is_standings:
                log.info(
                    f"Image rejected (not TFT standings): {image_data['discord_message_id']}"
                )
                return {
                    "success": False,
                    "reason": "not_standings",
                    "message_id": image_data["discord_message_id"]
                }

            # Step 2: OCR extraction (using Google Cloud Vision - 100% accurate!)
            ocr_client = get_cloud_vision_ocr()
            ocr_result = ocr_client.extract_from_image(
                str(temp_path)
            )

            if not ocr_result.get("success", False):
                return {
                    "success": False,
                    "reason": "ocr_failed",
                    "message_id": image_data["discord_message_id"],
                    "error": ocr_result.get("error")
                }

            # Get overall confidence from Cloud Vision result
            overall_confidence = ocr_result.get("confidence", 0.0)

            # Convert OCR results to JSON-serializable format
            serializable_ocr_result = {
                "success": ocr_result.get("success"),
                "structured_data": ocr_result.get("structured_data", {}),
                "confidence": overall_confidence,  # Cloud Vision provides confidence directly
                "raw_results": ocr_result.get("raw_results", []),
                "engine": "google_cloud_vision"
            }

            # Step 3: Create submission record
            submission_id = await self._create_submission(
                batch_id,
                guild_id,
                tournament_id,
                round_name,
                image_data,
                classification_confidence,
                serializable_ocr_result
            )

            # Step 4: Match players to roster
            player_matcher = get_player_matcher()
            structured_data = ocr_result["structured_data"]

            matched_players = player_matcher.match_players(
                structured_data.get("players", [])
            )

            # Step 5: Validate placement data
            validator = get_validator()

            # Single lobby validation
            lobby_number = image_data.get("lobby_number")
            single_validation = validator.validate_single_lobby(
                structured_data.get("players", []),
                lobby_number
            )

            # Player match validation
            match_validation = validator.validate_player_match_confidence(
                matched_players
            )

            # Step 6: Calculate overall confidence
            # With Google Cloud Vision (100% accurate), weight OCR confidence higher
            overall_confidence = (
                classification_confidence * 0.30 +
                serializable_ocr_result.get("confidence", 0.0) * 0.50 +  # Google Cloud Vision
                match_validation["score"] * 0.20
            )

            # Step 7: Auto-validate if high confidence (99%+)
            validated = False
            validation_method = None

            # Auto-validate if confidence >= 99%
            if overall_confidence >= 0.99:
                if (single_validation["valid"] and
                    match_validation["valid"]):

                    validated = True
                    validation_method = "auto"

                    log.info(
                        f"Auto-validated submission {submission_id} "
                        f"(confidence: {overall_confidence:.3f})"
                    )

            # ALWAYS create placement records (even if not auto-validated)
            # This allows manual review when confidence is low
            if matched_players:
                await self._create_placements(
                    submission_id,
                    tournament_id,
                    round_name,
                    lobby_number,
                    matched_players
                )
                log.info(f"Created placement records for submission {submission_id} (confidence: {overall_confidence:.3f}, validated: {validated})")
            else:
                log.warning(f"No players matched for submission {submission_id} - no placements created")

            # Step 8: Update submission record
            await self._update_submission(
                submission_id,
                overall_confidence,
                validated,
                validation_method,
                single_validation,
                match_validation,
                ocr_result
            )

            return {
                "success": True,
                "submission_id": submission_id,
                "validated": validated,
                "validation_method": validation_method,
                "confidence": overall_confidence,
                "message_id": image_data["discord_message_id"],
                "issues": (
                    single_validation.get("issues", []) +
                    match_validation.get("issues", [])
                )
            }

        except Exception as e:
            log.error(f"Image processing error: {e}", exc_info=True)
            return {
                "success": False,
                "reason": "processing_error",
                "message_id": image_data.get("discord_message_id"),
                "error": str(e)
            }
        finally:
            # Clean up temporary file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    log.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    log.warning(f"Failed to delete temp file {temp_path}: {e}")

    async def _create_submission(
        self,
        batch_id: int,
        guild_id: str,
        tournament_id: str,
        round_name: str,
        image_data: Dict,
        classification_confidence: float,
        ocr_result: Dict
    ) -> int:
        """Create placement submission record."""
        db = next(get_db())

        try:
            # Check if submission already exists (prevent duplicate processing)
            message_id = image_data["discord_message_id"]
            existing = db.query(PlacementSubmission).filter(
                PlacementSubmission.discord_message_id == message_id
            ).first()
            
            if existing:
                log.warning(f"Submission already exists for message_id: {message_id}")
                # Update the existing submission with new OCR results
                scores = ocr_result.get("scores", {})
                existing.ocr_consensus_confidence = int(
                    scores.get("ocr_consensus", 0) * 100
                )
                existing.ocr_character_confidence = int(
                    scores.get("character", 0) * 100
                )
                existing.extracted_data_consensus = ocr_result.get("structured_data", {})
                existing.status = "pending"
                existing.error_message = None
                existing.updated_at = utc_now()
                
                db.commit()
                log.info(f"Updated existing submission: {existing.id}")
                return existing.id
            
            # Create new submission
            scores = ocr_result.get("scores", {})
            
            submission = PlacementSubmission(
                guild_id=guild_id,
                tournament_id=tournament_id,
                round_name=round_name,
                lobby_number=image_data.get("lobby_number", 1),
                discord_message_id=message_id,
                discord_channel_id=image_data["discord_channel_id"],
                discord_author_id=image_data.get("discord_author_id"),
                image_url=image_data["url"],
                classification_score=int(classification_confidence * 100),
                ocr_consensus_confidence=int(
                    scores.get("ocr_consensus", 0) * 100
                ),
                ocr_character_confidence=int(
                    scores.get("character", 0) * 100
                ),
                extracted_data_tesseract={},  # Empty for PaddleOCR
                extracted_data_consensus=ocr_result.get("structured_data", {}),
                overall_confidence=50,  # Temporary, updated later
                status="pending",
                batch_id=batch_id
            )

            db.add(submission)
            db.commit()
            db.refresh(submission)

            log.info(f"Created submission: {submission.id}")

            return submission.id

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    async def _update_submission(
        self,
        submission_id: int,
        overall_confidence: float,
        validated: bool,
        validation_method: Optional[str],
        single_validation: Dict,
        match_validation: Dict,
        ocr_result: Dict
    ):
        """Update submission with final results."""
        db = next(get_db())

        try:
            submission = db.query(PlacementSubmission).filter(
                PlacementSubmission.id == submission_id
            ).first()

            if submission:
                submission.overall_confidence = int(overall_confidence * 100)
                submission.status = "validated" if validated else "pending"
                submission.validation_method = validation_method
                submission.player_match_confidence = int(
                    match_validation["score"] * 100
                )
                submission.structural_validity_score = int(
                    single_validation["score"] * 100
                )
                submission.validated_at = datetime.utcnow() if validated else None

                db.commit()

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    async def _create_placements(
        self,
        submission_id: int,
        tournament_id: str,
        round_name: str,
        lobby_number: int,
        matched_players: List[Dict]
    ):
        """Create validated placement records."""
        db = next(get_db())

        try:
            for player_data in matched_players:
                match_result = player_data.get("match_result", {})
                placement = player_data.get("placement")
                points = player_data.get("points", 0)

                if not placement:
                    continue

                placement_record = RoundPlacement(
                    submission_id=submission_id,
                    player_id=match_result.get("player_id", player_data.get("name")),  # Fallback to player name if unmatched
                    player_name=match_result.get("matched_name", player_data.get("name")),
                    discord_id=match_result.get("player_id"),  # Use None if unmatched
                    tournament_id=tournament_id,
                    round_name=round_name,
                    round_number=self._parse_round_number(round_name),
                    lobby_number=lobby_number,
                    placement=placement,
                    points=points,
                    extraction_confidence=0,  # Can add if needed
                    player_match_confidence=int(
                        match_result.get("confidence", 0) * 100
                    ),
                    match_method=match_result.get("match_method"),
                    validated=True
                )

                db.add(placement_record)

            db.commit()
            log.info(f"Created placements for submission {submission_id}")

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def _parse_round_number(self, round_name: str) -> int:
        """Extract round number from round name."""
        # Try to find number in string
        import re
        match = re.search(r'\d+', round_name)
        if match:
            return int(match.group())
        return 1

    async def _cross_lobby_validate(self, batch_id: int):
        """Validate data across all lobbies in batch."""
        db = next(get_db())

        try:
            submissions = db.query(PlacementSubmission).filter(
                PlacementSubmission.batch_id == batch_id
            ).all()

            if len(submissions) <= 1:
                return

            # Collect player data from all submissions
            all_lobbies = []

            for submission in submissions:
                placements = db.query(RoundPlacement).filter(
                    RoundPlacement.submission_id == submission.id
                ).all()

                players = [
                    {
                        "name": p.player_name,
                        "placement": p.placement,
                        "lobby_number": p.lobby_number
                    }
                    for p in placements
                ]

                all_lobbies.append({
                    "lobby_number": submission.lobby_number,
                    "players": players
                })

            # Run cross-lobby validation
            validator = get_validator()
            result = validator.validate_cross_lobby(all_lobbies)

            log.info(
                f"Cross-lobby validation for batch {batch_id}: "
                f"{'PASS' if result['valid'] else 'FAIL'}"
            )

            # Flag issues in submissions
            if not result["valid"] and result.get("issues"):
                for issue in result["issues"]:
                    log.warning(f"Cross-lobby issue: {issue}")

        except Exception as e:
            log.error(f"Cross-lobby validation error: {e}")
        finally:
            db.close()

    async def _calculate_batch_confidence(self, batch_id: int) -> float:
        """Calculate average confidence across batch."""
        db = next(get_db())

        try:
            submissions = db.query(PlacementSubmission).filter(
                PlacementSubmission.batch_id == batch_id
            ).all()

            if not submissions:
                return 0.0

            confidences = [s.overall_confidence for s in submissions]
            avg = sum(confidences) / len(confidences)

            return avg / 100  # Convert back to 0-1 range

        except Exception as e:
            log.error(f"Error calculating batch confidence: {e}")
            return 0.0
        finally:
            db.close()


# Singleton instance
_batch_processor_instance = None

def get_batch_processor() -> BatchProcessor:
    """Get or create batch processor instance."""
    global _batch_processor_instance
    if _batch_processor_instance is None:
        _batch_processor_instance = BatchProcessor()
    return _batch_processor_instance
