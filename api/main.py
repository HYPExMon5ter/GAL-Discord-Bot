"""
FastAPI Main Application for Guardian Angel League Live Graphics Dashboard

This module sets up the FastAPI application with master password authentication,
CORS middleware, and includes all API routers.
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin

import httpx
import logging
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add project root to Python path to ensure imports work correctly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

from .auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    TokenData,
    create_access_token,
    get_current_authenticated_user,
    get_current_user,
    verify_token,
)

# Initialize FastAPI app
app = FastAPI(
    title="Guardian Angel League - Live Graphics Dashboard API",
    description="REST API for the GAL Live Graphics Dashboard with master password authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware will be added after all other middleware to ensure proper order

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class LoginRequest(BaseModel):
    master_password: str

# Authentication endpoints
@app.post("/auth/login", response_model=Token)
async def login(login_request: LoginRequest):
    """
    Authenticate with master password and return JWT token
    """
    if login_request.master_password != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect master password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {
        "sub": "dashboard_user",
        "roles": ["Administrator"],
        "scopes": ["dashboard:full"],
        "read_only": False,
    }
    access_token = create_access_token(data=token_payload, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    }

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(verify_token)):
    """
    Refresh JWT token
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "roles": current_user.roles,
            "scopes": current_user.scopes,
            "read_only": current_user.read_only,
        },
        expires_delta=access_token_expires,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/auth/logout")
async def logout():
    """
    Logout endpoint (JWT tokens are stateless, client handles token removal)
    """
    return {"message": "Successfully logged out"}

@app.get("/auth/verify")
async def verify_auth(current_user: TokenData = Depends(verify_token)):
    """
    Verify if current token is valid
    """
    return {"valid": True, "username": current_user.username}

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """
    Initialize services on API startup
    """
    import os
    from api.services.ign_verification import initialize_verification_service
    
    logger.info("Starting up Guardian Angel League API...")
    
    # Initialize IGN verification service
    riot_api_key = os.getenv("RIOT_API_KEY")
    
    if riot_api_key:
        success = await initialize_verification_service(riot_api_key)
        if success:
            logger.info("✅ IGN verification service initialized")
        else:
            logger.warning("⚠️ Failed to initialize IGN verification service")
    else:
        logger.info("IGN verification service disabled (no RIOT_API_KEY)")
    
    logger.info("API startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on API shutdown
    """
    from api.services.ign_verification import get_verification_service
    
    logger.info("Shutting down Guardian Angel League API...")
    
    # Cleanup IGN verification service
    service = await get_verification_service()
    if service:
        await service.cleanup()
        logger.info("✅ IGN verification service cleaned up")
    
    logger.info("API shutdown completed")



# Import middleware and routers
from .routers import configuration, graphics, standings, tournaments, users, websocket, ign_verification
from .middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

# Add custom middleware first (they will execute in reverse order)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware last (so it executes first in the middleware chain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since we're not using credentials
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tournaments.router, prefix="/api/v1/tournaments", tags=["tournaments"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(configuration.router, prefix="/api/v1/configuration", tags=["configuration"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(graphics.router, prefix="/api/v1", tags=["graphics"])
app.include_router(standings.router, prefix="/api/v1", tags=["scoreboard"])
app.include_router(ign_verification.router, prefix="/api/v1", tags=["ign-verification"])

# Reverse proxy for Next.js frontend
# All non-API routes will be proxied to Next.js running on port 8080
API_PATHS = {
    "/api/", "/auth/", "/health", "/docs", "/redoc", "/openapi.json"
}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_to_frontend(request: Request, path: str):
    """
    Proxy non-API requests to Next.js frontend
    """
    # Check if this is an API route that should not be proxied
    if any(path.startswith(api_path.rstrip('/')) for api_path in API_PATHS):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API endpoint not found: /{path}"
        )
    
    # Build the target URL for Next.js
    target_url = f"http://localhost:8080/{path}"
    
    # Handle query parameters
    if request.query_params:
        target_url += f"?{request.url.query}"
    
    # Get request body if present
    body = await request.body()
    
    # Create headers for the proxied request
    headers = dict(request.headers)
    # Remove host header as it will conflict
    headers.pop("host", None)
    
    async with httpx.AsyncClient() as client:
        try:
            # Proxy the request to Next.js
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None
            )
            
            # Return the response from Next.js
            # Filter out headers that cause encoding issues
            excluded_headers = {'content-encoding', 'content-length', 'transfer-encoding'}
            filtered_headers = {
                k: v for k, v in response.headers.items() 
                if k.lower() not in excluded_headers
            }
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=filtered_headers
            )
        except httpx.RequestError as e:
            logger.error(f"Error proxying request to Next.js: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Frontend service unavailable"
            )

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
