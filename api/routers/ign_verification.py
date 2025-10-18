"""
Router for IGN verification endpoints.
Provides REST API for League of Legends IGN verification.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from api.services.ign_verification import get_verification_service, IGNVerificationResult, IGNVerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ign-verification", tags=["ign-verification"])


class IGNVerificationRequest(BaseModel):
    """Request model for IGN verification."""
    ign: str = Field(..., description="In-game name in format: Name#Tag", min_length=1, max_length=32)
    region: str = Field(default="na", description="Riot server region", min_length=2, max_length=4)


class IGNVerificationResponse(BaseModel):
    """Response model for IGN verification."""
    is_valid: bool = Field(..., description="Whether the IGN is valid")
    message: str = Field(..., description="Human-readable verification message")
    riot_data: Optional[Dict[str, Any]] = Field(None, description="Riot API data if verification succeeded")
    summoner_id: Optional[str] = Field(None, description="Riot summoner ID")
    account_id: Optional[str] = Field(None, description="Riot account ID")
    puuid: Optional[str] = Field(None, description="Riot PUUID")
    rank: Optional[str] = Field(None, description="Player rank information")
    level: Optional[int] = Field(None, description="Summoner level")


class VerificationStatsResponse(BaseModel):
    """Response model for verification statistics."""
    total_cached: int = Field(..., description="Total number of cached verifications")
    valid_cached: int = Field(..., description="Number of valid cached verifications")
    expired_cached: int = Field(..., description="Number of expired cached verifications")
    recent_verifications: int = Field(..., description="Number of verifications in last 24 hours")


async def ensure_verification_service():
    """Dependency to ensure verification service is available."""
    service = await get_verification_service()
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="IGN verification service is not available"
        )
    return service


@router.post("/verify", response_model=IGNVerificationResponse)
async def verify_ign(
    request: IGNVerificationRequest,
    service: IGNVerificationService = Depends(ensure_verification_service)
):
    """
    Verify a League of Legends IGN using Riot Games API.
    
    Args:
        request: Verification request containing IGN and region
        service: IGN verification service
        
    Returns:
        Verification result with detailed information
    """
    try:
        logger.info(f"IGN verification request: {request.ign} (region: {request.region})")
        
        # Perform verification
        is_valid, message, riot_data = await service.verify_ign(request.ign, request.region)
        
        # If service returned additional data, extract it
        if riot_data:
            return IGNVerificationResponse(
                is_valid=is_valid,
                message=message,
                riot_data=riot_data,
                summoner_id=riot_data.get('summonerId'),
                account_id=riot_data.get('accountId'),
                puuid=riot_data.get('puuid'),
                level=riot_data.get('summonerLevel')
            )
        else:
            return IGNVerificationResponse(
                is_valid=is_valid,
                message=message
            )
            
    except Exception as e:
        logger.error(f"Error verifying IGN {request.ign}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )


@router.get("/verify", response_model=IGNVerificationResponse)
async def verify_ign_get(
    ign: str = Query(..., description="In-game name in format: Name#Tag"),
    region: str = Query(default="na", description="Riot server region"),
    service: IGNVerificationService = Depends(ensure_verification_service)
):
    """
    Verify a League of Legends IGN using GET request.
    
    Args:
        ign: In-game name to verify
        region: Riot server region
        service: IGN verification service
        
    Returns:
        Verification result
    """
    # Create request object and delegate to POST endpoint
    request = IGNVerificationRequest(ign=ign, region=region)
    return await verify_ign(request, service)


@router.get("/stats", response_model=VerificationStatsResponse)
async def get_verification_stats(
    service: IGNVerificationService = Depends(ensure_verification_service)
):
    """
    Get verification statistics.
    
    Args:
        service: IGN verification service
        
    Returns:
        Verification statistics
    """
    try:
        stats = await service.get_verification_stats()
        return VerificationStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting verification stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for IGN verification service.
    
    Returns:
        Health status
    """
    service = await get_verification_service()
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="IGN verification service is not available"
        )
    
    return {
        "status": "healthy",
        "service": "ign_verification",
        "message": "IGN verification service is running"
    }


@router.get("/regions")
async def get_supported_regions():
    """
    Get list of supported regions.
    
    Returns:
        List of supported regions
    """
    regions = {
        "na": "North America",
        "lan": "Latin America North", 
        "las": "Latin America South",
        "br": "Brazil",
        "euw": "Europe West",
        "eune": "Europe Nordic & East",
        "tr": "Turkey",
        "ru": "Russia",
        "kr": "Korea",
        "jp": "Japan",
        "oce": "Oceania"
    }
    
    return {
        "regions": regions,
        "default": "na"
    }
