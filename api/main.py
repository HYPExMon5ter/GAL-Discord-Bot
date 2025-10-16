"""
FastAPI Main Application for Guardian Angel League Live Graphics Dashboard

This module sets up the FastAPI application with master password authentication,
CORS middleware, and includes all API routers.
"""

from datetime import UTC, datetime, timedelta

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since we're not using credentials
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Guardian Angel League - Live Graphics Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }



# Import and include routers
from .routers import configuration, graphics, tournaments, users, websocket
from .middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

# Add custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Include API routers
app.include_router(tournaments.router, prefix="/api/v1/tournaments", tags=["tournaments"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(configuration.router, prefix="/api/v1/configuration", tags=["configuration"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(graphics.router, prefix="/api/v1", tags=["graphics"])

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
