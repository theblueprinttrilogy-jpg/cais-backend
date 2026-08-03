"""
app/api/auth.py

Authentication module for CAIS Code Compliance backend.
Provides login endpoint and JWT token generation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from jwt import PyJWTError

logger = logging.getLogger(__name__)

# JWT configuration (use environment variables in production)
SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory user store for development
# In production, use a proper database and hashed passwords
DEV_USERS = {
    "admin": "admin123",
    "testuser": "testpass",
}

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    """Request model for login endpoint."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    token_type: str = "bearer"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with the given data and expiration.

    :param data: Dictionary to encode as payload.
    :param expires_delta: Optional timedelta for expiration.
    :return: Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Authenticate a user and return a JWT access token.

    For development, credentials are validated against a static dictionary.
    """
    logger.info(f"Login attempt for user: {request.username}")

    # Validate credentials against in-memory store
    if request.username not in DEV_USERS or DEV_USERS[request.username] != request.password:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token with username in payload
    access_token = create_access_token(data={"sub": request.username})
    logger.info(f"User {request.username} logged in successfully.")
    return TokenResponse(access_token=access_token)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to extract and validate the current user from the JWT token.
    Raises HTTP 401 if token is invalid or missing.

    :param credentials: HTTP Authorization credentials.
    :return: Username from token payload.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Optionally check if user exists in DB
        if username not in DEV_USERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except PyJWTError as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
