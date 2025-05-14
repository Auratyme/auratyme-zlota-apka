# === File: schedules-ai/api/middleware/jwt_auth.py ===

"""
JWT Authentication Middleware for the API.

This module provides middleware for verifying JWT tokens in requests.
"""

import logging
import os
from typing import Optional, List

import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# --- JWT Configuration ---
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-for-development-only")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "auratyme-api")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "auratyme-auth")

# --- Public Paths ---
PUBLIC_PATHS: List[str] = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/v1/auth/generate-token",
]


# --- Authentication Classes ---

class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication."""

    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """Verify the JWT token in the request."""
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication credentials",
            )

        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme. Use Bearer token.",
            )

        if not self.verify_jwt(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token or expired token",
            )

        return credentials.credentials

    def verify_jwt(self, token: str) -> bool:
        """Verify the JWT token."""
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
            )
            return True if payload else False
        except jwt.PyJWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return False


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and verify JWT token if needed."""
        path = request.url.path
        if any(path.startswith(public_path) for public_path in PUBLIC_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
            )
            request.state.user = payload
        except jwt.PyJWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


# --- Helper Functions ---

def get_user_from_token(token: str) -> Optional[str]:
    """Get user ID from JWT token."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        return payload.get("sub")
    except jwt.PyJWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def create_jwt_token(user_id: str, username: str = None) -> str:
    """Create a JWT token for testing."""
    logger.debug(f"Attempting to create JWT token for user_id: {user_id}")
    logger.debug(f"Using JWT_SECRET: {'*' * len(JWT_SECRET) if JWT_SECRET else 'Not Set'}")
    logger.debug(f"Using JWT_ALGORITHM: {JWT_ALGORITHM}")
    logger.debug(f"Using JWT_AUDIENCE: {JWT_AUDIENCE}")
    logger.debug(f"Using JWT_ISSUER: {JWT_ISSUER}")
    try:
        payload = {
            "sub": user_id,
            "aud": JWT_AUDIENCE,
            "iss": JWT_ISSUER,
        }
        if username:
            payload["username"] = username
        logger.debug(f"Payload created: {payload}")

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug("jwt.encode successful.")

        if isinstance(token, bytes):
            logger.debug("Token is bytes, decoding to utf-8.")
            return token.decode('utf-8')
        return token
    except Exception as e:
        logger.exception(f"Error creating JWT token: {e}")
        raise
