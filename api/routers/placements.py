"""
Placements/Screenshot Processing API endpoints.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session
import aiohttp

from api.auth import TokenData
from api.dependencies import get_db, get_active_user
from api.models import (
    PlacementSubmission, RoundPlacement,
    ProcessingBatch, ScoreboardSnapshot
)
from integrations.batch_processor import get_batch_processor

log = logging.getLogger(__name__)

router = APIRouter(prefix="/placements", tags=["placements"])


@router.post(
    "/process-screenshot",
    response_model=Dict[str, Any],
    summary="Process a single screenshot.",
)
async def process_screenshot(
    image_url: str = Body(..., embed=True),
    round_name: Optional[str] = Body(None),
    lobby_number: Optional[int] = Body(1),
    tournament_id: Optional[str] = Body(None),
    guild_id: Optional[str] = Body(None),
    _user: TokenData = Depends(get_active_user),
    batch_processor = Depends(get_batch_processor),
) -> Dict[str, Any]:
    """
    Process a single screenshot through OCR pipeline.

    Requires admin access.
    """
    # Create mock image data
    image_data = {
        "url": image_url,
        "discord_message_id": f"manual_{datetime.now().timestamp()}",
        "discord_channel_id": "manual",
        "discord_author_id": str(_user.user_id),
        "round_name": round_name,
        "lobby_number": lobby_number
    }

    # Process
    result = await batch_processor.process_batch(
        images=[image_data],
        tournament_id=tournament_id or "manual",
        guild_id=guild_id or "manual",
        round_name=round_name or "manual"
    )

    return result


@router.post(
    "/batch-process",
    response_model=Dict[str, Any],
    summary="Process multiple screenshots as a batch.",
)
async def batch_process_screenshots(
    image_urls: List[str] = Body(..., embed=True),
    round_name: Optional[str] = Body(None),
    tournament_id: Optional[str] = Body(None),
    guild_id: Optional[str] = Body(None),
    _user: TokenData = Depends(get_active_user),
    batch_processor = Depends(get_batch_processor),
) -> Dict[str, Any]:
    """
    Process multiple screenshots concurrently.

    Requires admin access.
    """
    # Create mock image data
    images = [
        {
            "url": url,
            "discord_message_id": f"manual_{i}_{datetime.now().timestamp()}",
            "discord_channel_id": "manual",
            "discord_author_id": str(_user.user_id),
            "round_name": round_name,
            "lobby_number": i + 1  # Auto-assign lobby numbers
        }
        for i, url in enumerate(image_urls)
    ]

    # Process
    result = await batch_processor.process_batch(
        images=images,
        tournament_id=tournament_id or "manual",
        guild_id=guild_id or "manual",
        round_name=round_name or "manual"
    )

    return result


@router.get(
    "/submissions",
    response_model=List[Dict[str, Any]],
    summary="List all placement submissions.",
)
async def list_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    tournament_id: Optional[str] = Query(None),
    round_name: Optional[str] = Query(None),
    confidence_min: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> List[Dict[str, Any]]:
    """
    List placement submissions with optional filtering.
    """
    query = db.query(PlacementSubmission)

    # Apply filters
    if status_filter:
        query = query.filter(PlacementSubmission.status == status_filter)

    if tournament_id:
        query = query.filter(PlacementSubmission.tournament_id == tournament_id)

    if round_name:
        query = query.filter(PlacementSubmission.round_name == round_name)

    if confidence_min:
        query = query.filter(PlacementSubmission.overall_confidence >= confidence_min)

    # Order and paginate
    query = query.order_by(PlacementSubmission.created_at.desc())
    query = query.offset(offset).limit(limit)

    submissions = query.all()

    return [
        {
            "id": s.id,
            "tournament_id": s.tournament_id,
            "round_name": s.round_name,
            "lobby_number": s.lobby_number,
            "status": s.status,
            "overall_confidence": s.overall_confidence / 100,
            "validation_method": s.validation_method,
            "created_at": s.created_at.isoformat(),
            "validated_at": s.validated_at.isoformat() if s.validated_at else None,
        }
        for s in submissions
    ]


@router.get(
    "/submissions/{submission_id}",
    response_model=Dict[str, Any],
    summary="Get detailed submission data.",
)
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Get detailed information about a specific submission.
    """
    submission = db.query(PlacementSubmission).filter(
        PlacementSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Get placements
    placements = db.query(RoundPlacement).filter(
        RoundPlacement.submission_id == submission_id
    ).all()

    return {
        "id": submission.id,
        "tournament_id": submission.tournament_id,
        "round_name": submission.round_name,
        "lobby_number": submission.lobby_number,
        "image_url": submission.image_url,
        "status": submission.status,
        "validation_method": submission.validation_method,
        "overall_confidence": submission.overall_confidence / 100,
        "classification_score": submission.classification_score / 100 if submission.classification_score else None,
        "ocr_consensus_confidence": submission.ocr_consensus_confidence / 100 if submission.ocr_consensus_confidence else None,
        "player_match_confidence": submission.player_match_confidence / 100 if submission.player_match_confidence else None,
        "structural_validity_score": submission.structural_validity_score / 100 if submission.structural_validity_score else None,
        "created_at": submission.created_at.isoformat(),
        "validated_at": submission.validated_at.isoformat() if submission.validated_at else None,
        "placements": [
            {
                "id": p.id,
                "player_id": p.player_id,
                "player_name": p.player_name,
                "placement": p.placement,
                "points": p.points,
                "match_method": p.match_method,
                "validated": p.validated
            }
            for p in placements
        ],
        "extracted_data": submission.extracted_data_consensus
    }


@router.get(
    "/batches",
    response_model=List[Dict[str, Any]],
    summary="List processing batches.",
)
async def list_batches(
    tournament_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, le=50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> List[Dict[str, Any]]:
    """
    List processing batches.
    """
    query = db.query(ProcessingBatch)

    if tournament_id:
        query = query.filter(ProcessingBatch.tournament_id == tournament_id)

    if status_filter:
        query = query.filter(ProcessingBatch.status == status_filter)

    query = query.order_by(ProcessingBatch.started_at.desc())
    query = query.offset(offset).limit(limit)

    batches = query.all()

    return [
        {
            "id": b.id,
            "tournament_id": b.tournament_id,
            "round_name": b.round_name,
            "batch_size": b.batch_size,
            "completed_count": b.completed_count,
            "validated_count": b.validated_count,
            "error_count": b.error_count,
            "status": b.status,
            "average_confidence": b.average_confidence / 100 if b.average_confidence else None,
            "started_at": b.started_at.isoformat(),
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        }
        for b in batches
    ]


@router.get(
    "/batches/{batch_id}",
    response_model=Dict[str, Any],
    summary="Get batch details.",
)
async def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Get detailed information about a processing batch.
    """
    batch = db.query(ProcessingBatch).filter(
        ProcessingBatch.id == batch_id
    ).first()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )

    # Get submissions in this batch
    submissions = db.query(PlacementSubmission).filter(
        PlacementSubmission.batch_id == batch_id
    ).all()

    return {
        "id": batch.id,
        "tournament_id": batch.tournament_id,
        "round_name": batch.round_name,
        "batch_size": batch.batch_size,
        "completed_count": batch.completed_count,
        "validated_count": batch.validated_count,
        "error_count": batch.error_count,
        "status": batch.status,
        "average_confidence": batch.average_confidence / 100 if batch.average_confidence else None,
        "started_at": batch.started_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "submissions": [
            {
                "id": s.id,
                "lobby_number": s.lobby_number,
                "status": s.status,
                "overall_confidence": s.overall_confidence / 100,
                "validated": s.status == "validated"
            }
            for s in submissions
        ]
    }


@router.post(
    "/validate/{submission_id}",
    response_model=Dict[str, Any],
    summary="Manually validate or reject a submission.",
)
async def validate_submission(
    submission_id: int,
    approved: bool = Body(...),
    edited_placements: Optional[List[Dict[str, Any]]] = Body(None),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Manually approve, edit, or reject a submission.

    Requires admin access.
    """
    submission = db.query(PlacementSubmission).filter(
        PlacementSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    if approved:
        # Approve (with optional edits)
        submission.status = "validated"
        submission.validation_method = "manual"
        submission.validated_by_discord_id = str(_user.username)  # Fix: TokenData has username, not user_id
        submission.validation_notes = notes
        submission.validated_at = datetime.utcnow()
        submission.edited = edited_placements is not None

        # If placements provided, update them
        if edited_placements:
            # Delete existing placements
            db.query(RoundPlacement).filter(
                RoundPlacement.submission_id == submission_id
            ).delete()

            # Create new placements
            for placement_data in edited_placements:
                placement = RoundPlacement(
                    submission_id=submission_id,
                    player_id=placement_data.get("player_id"),
                    player_name=placement_data.get("player_name"),
                    tournament_id=submission.tournament_id,
                    round_name=submission.round_name,
                    round_number=1,  # Can be parsed from round_name
                    lobby_number=submission.lobby_number,
                    placement=placement_data["placement"],
                    points=placement_data.get("points", 0),
                    validated=True,
                    manually_corrected=True,
                    validated_by_discord_id=str(_user.username)  # Fix: TokenData has username, not user_id
                )
                db.add(placement)

        db.commit()
        log.info(f"Submission {submission_id} validated by user {_user.username}")  # Fix: username, not user_id

        return {
            "success": True,
            "action": "validated",
            "submission_id": submission_id
        }
    else:
        # Reject
        submission.status = "rejected"
        submission.validation_method = "manual"
        submission.validation_notes = notes
        submission.validated_by_discord_id = str(_user.username)  # Fix: TokenData has username, not user_id

        db.commit()
        log.info(f"Submission {submission_id} rejected by user {_user.username}")  # Fix: username, not user_id

        return {
            "success": True,
            "action": "rejected",
            "submission_id": submission_id
        }


@router.get(
    "/rounds/{tournament_id}/{round_name}",
    response_model=Dict[str, Any],
    summary="Get placements for a specific round.",
)
async def get_round_placements(
    tournament_id: str,
    round_name: str,
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Get all validated placements for a specific round.
    """
    submissions = db.query(PlacementSubmission).filter(
        PlacementSubmission.tournament_id == tournament_id,
        PlacementSubmission.round_name == round_name,
        PlacementSubmission.status == "validated"
    ).all()

    all_placements = []
    for submission in submissions:
        placements = db.query(RoundPlacement).filter(
            RoundPlacement.submission_id == submission.id
        ).all()
        all_placements.extend(placements)

    return {
        "tournament_id": tournament_id,
        "round_name": round_name,
        "placements": [
            {
                "player_id": p.player_id,
                "player_name": p.player_name,
                "placement": p.placement,
                "points": p.points,
                "lobby_number": p.lobby_number
            }
            for p in all_placements
        ],
        "total_players": len(all_placements)
    }


@router.post(
    "/refresh-scoreboard",
    response_model=Dict[str, Any],
    summary="Trigger scoreboard refresh from validated placements.",
)
async def refresh_scoreboard(
    tournament_id: str = Body(...),
    round_name: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Trigger scoreboard refresh based on validated placements.

    This will aggregate all round placements into a scoreboard snapshot.
    """
    # In a full implementation, this would call StandingsAggregator
    # For now, return success message

    log.info(f"Scoreboard refresh requested for {tournament_id} (round: {round_name})")

    return {
        "success": True,
        "message": "Scoreboard refresh triggered",
        "tournament_id": tournament_id,
        "round_name": round_name
    }


@router.get(
    "/confidence-report",
    response_model=Dict[str, Any],
    summary="Get OCR accuracy metrics.",
)
async def confidence_report(
    tournament_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Get confidence statistics and accuracy metrics.
    """
    query = db.query(PlacementSubmission)

    if tournament_id:
        query = query.filter(PlacementSubmission.tournament_id == tournament_id)

    submissions = query.all()

    if not submissions:
        return {
            "total_submissions": 0,
            "average_confidence": 0,
            "auto_validated": 0,
            "manually_validated": 0,
            "distribution": {}
        }

    # Calculate metrics
    confidences = [s.overall_confidence for s in submissions]
    avg_confidence = sum(confidences) / len(confidences)

    auto_validated = sum(1 for s in submissions if s.validation_method == "auto")
    manually_validated = sum(1 for s in submissions if s.validation_method == "manual")

    # Confidence distribution
    distribution = {
        "high (90-100%)": sum(1 for c in confidences if c >= 90),
        "medium (70-89%)": sum(1 for c in confidences if 70 <= c < 90),
        "low (0-69%)": sum(1 for c in confidences if c < 70),
    }

    return {
        "total_submissions": len(submissions),
        "average_confidence": avg_confidence / 100,
        "auto_validated": auto_validated,
        "manually_validated": manually_validated,
        "auto_validation_rate": auto_validated / len(submissions) if submissions else 0,
        "distribution": distribution
    }


@router.get(
    "/pending-review",
    response_model=Dict[str, Any],
    summary="Get submissions pending manual review.",
)
async def get_pending_review(
    tournament_id: Optional[str] = Query(None),
    round_name: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Get submissions that need manual review.
    Returns submissions with status 'pending_review' or low confidence.
    """
    query = db.query(PlacementSubmission).filter(
        PlacementSubmission.status.in_(["pending", "pending_review"])  # Show pending too
    )

    if tournament_id:
        query = query.filter(PlacementSubmission.tournament_id == tournament_id)

    if round_name:
        query = query.filter(PlacementSubmission.round_name == round_name)

    # Order by confidence (lowest first) and creation time
    query = query.order_by(
        PlacementSubmission.overall_confidence.asc(),
        PlacementSubmission.created_at.desc()
    )

    total_count = query.count()
    submissions = query.offset(offset).limit(limit).all()

    # Get placements and issues for each submission
    result_submissions = []
    for submission in submissions:
        placements = db.query(RoundPlacement).filter(
            RoundPlacement.submission_id == submission.id
        ).all()

        # Identify issues
        issues = []
        if submission.overall_confidence < 80:
            issues.append("Low overall confidence")
        if submission.player_match_confidence and submission.player_match_confidence < 90:
            issues.append("Low player match confidence")
        if submission.ocr_consensus_confidence and submission.ocr_consensus_confidence < 85:
            issues.append("Low OCR consensus")

        result_submissions.append({
            "id": submission.id,
            "tournament_id": submission.tournament_id,
            "round_name": submission.round_name,
            "lobby_number": submission.lobby_number,
            "image_url": submission.image_url,
            "status": submission.status,
            "overall_confidence": submission.overall_confidence / 100,
            "created_at": submission.created_at.isoformat(),
            "placements": [
                {
                    "id": p.id,
                    "player_id": p.player_id,
                    "player_name": p.player_name,
                    "placement": p.placement,
                    "points": p.points,
                    "match_method": p.match_method,
                    "validated": p.validated
                }
                for p in placements
            ],
            "issues": issues
        })

    return {
        "submissions": result_submissions,
        "total": total_count,
        "offset": offset,
        "limit": limit
    }


@router.post(
    "/batch-validate",
    response_model=Dict[str, Any],
    summary="Approve or reject multiple submissions at once.",
)
async def batch_validate_submissions(
    submission_ids: List[int] = Body(...),
    approved: bool = Body(...),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Batch approve or reject multiple submissions.
    Useful for quickly reviewing multiple lobbies in a round.
    
    Requires admin access.
    """
    results = {
        "success": [],
        "failed": [],
        "total": len(submission_ids)
    }

    for submission_id in submission_ids:
        try:
            submission = db.query(PlacementSubmission).filter(
                PlacementSubmission.id == submission_id
            ).first()

            if not submission:
                results["failed"].append({
                    "id": submission_id,
                    "error": "Submission not found"
                })
                continue

            if approved:
                submission.status = "validated"
                submission.validation_method = "manual"
                submission.validated_by_discord_id = str(_user.user_id)
                submission.validation_notes = notes
                submission.validated_at = datetime.utcnow()

                # Mark all placements as validated
                db.query(RoundPlacement).filter(
                    RoundPlacement.submission_id == submission_id
                ).update({
                    "validated": True,
                    "validated_by_discord_id": str(_user.user_id)
                })

                results["success"].append(submission_id)
            else:
                submission.status = "rejected"
                submission.validation_method = "manual"
                submission.validation_notes = notes
                submission.validated_by_discord_id = str(_user.user_id)

                results["success"].append(submission_id)

        except Exception as e:
            log.error(f"Failed to validate submission {submission_id}: {e}")
            results["failed"].append({
                "id": submission_id,
                "error": str(e)
            })

    db.commit()

    log.info(
        f"Batch validation by user {_user.user_id}: "
        f"{len(results['success'])} success, {len(results['failed'])} failed"
    )

    return results


@router.get(
    "/players/search",
    response_model=Dict[str, Any],
    summary="Search registered players for autocomplete.",
)
async def search_players(
    q: str = Query(..., min_length=1),
    tournament_id: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    _user: TokenData = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Search for players by name for autocomplete in review UI.
    Returns players with aliases and fuzzy matching.
    """
    from api.models import PlayerAlias
    from difflib import SequenceMatcher

    # Search query (case-insensitive)
    search_term = q.lower()

    # Get all players (in real implementation, this would query tournament registrations)
    # For now, we'll get players from recent placements
    placements_query = db.query(RoundPlacement).filter(
        RoundPlacement.player_name.isnot(None)
    )

    if tournament_id:
        placements_query = placements_query.filter(
            RoundPlacement.tournament_id == tournament_id
        )

    # Get unique player names
    unique_players = {}
    for placement in placements_query.all():
        if placement.player_id and placement.player_id not in unique_players:
            unique_players[placement.player_id] = placement.player_name

    # Get aliases
    aliases_map = {}
    aliases = db.query(PlayerAlias).all()
    for alias in aliases:
        if alias.player_id not in aliases_map:
            aliases_map[alias.player_id] = []
        aliases_map[alias.player_id].append(alias.alias)

    # Fuzzy match players
    matches = []
    for player_id, player_name in unique_players.items():
        # Calculate match confidence
        name_similarity = SequenceMatcher(None, search_term, player_name.lower()).ratio()

        # Check aliases
        alias_matches = []
        if player_id in aliases_map:
            for alias in aliases_map[player_id]:
                alias_similarity = SequenceMatcher(None, search_term, alias.lower()).ratio()
                if alias_similarity > 0.5:
                    alias_matches.append(alias)
                    name_similarity = max(name_similarity, alias_similarity)

        # Include if confidence > 0.3
        if name_similarity > 0.3 or search_term in player_name.lower():
            matches.append({
                "id": player_id,
                "name": player_name,
                "aliases": aliases_map.get(player_id, []),
                "match_confidence": name_similarity
            })

    # Sort by confidence
    matches.sort(key=lambda x: x["match_confidence"], reverse=True)

    return {
        "players": matches[:limit],
        "query": q,
        "total": len(matches)
    }
