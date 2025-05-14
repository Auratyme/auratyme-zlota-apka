# === File: schedules-ai/api/middleware/auth.py ===

"""
Authentication and Authorization Utilities for the Scheduler Core API.

This module provides dependency functions suitable for use with FastAPI's
`Depends` system to protect API endpoints. It includes examples for verifying
API keys and JWT tokens.
"""

import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

# --- Constants and Configuration ---
logger = logging.getLogger(__name__)

# --- Security Schemes ---
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_bearer_scheme = OAuth2PasswordBearer(tokenUrl="v1/users/token", auto_error=False)


# --- Dependency Functions for Route Protection ---


async def verify_api_key(
    api_key: Optional[str] = Depends(api_key_header_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify a static API key provided in the X-API-Key header.

    Args:
        api_key: The API key extracted from the request header.

    Returns:
        A dictionary containing information about the authenticated principal.
    """
    logger.debug("Attempting API key verification.")

    try:
        expected_key = "your-secret-api-key-loaded-from-env"  # Placeholder
        if not expected_key:
            logger.error("Server configuration error: Expected API key is not set.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API authentication configuration error.",
            )
    except Exception:
         logger.exception("Failed to load expected API key from configuration.")
         raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API authentication configuration error.",
            )

    if api_key is None:
        logger.warning("API key verification failed: Key missing from header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "Header"},
        )

    if not hmac.compare_digest(api_key.encode("utf-8"), expected_key.encode("utf-8")):
        logger.warning("API key verification failed: Invalid key provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Header"},
        )

    logger.info("API key verified successfully.")
    return {"authenticated_via": "api_key", "client_id": "trusted_service_account"}


async def verify_jwt_token(
    token: Optional[str] = Depends(oauth2_bearer_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify a JWT token provided in the Authorization header.

    Args:
        token: The JWT token extracted from the Authorization header.

    Returns:
        A dictionary containing the validated user information.
    """
    logger.debug("Attempting JWT token verification.")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        logger.warning("JWT verification failed: Token missing from Authorization header.")
        raise credentials_exception

    try:
        jwt_secret = "your-jwt-secret-key-loaded-from-env"
        jwt_algorithm = "HS256"

        if not jwt_secret:
             logger.error("Server configuration error: JWT secret key is not set.")
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT authentication configuration error.",
            )

        # TODO: Install python-jose library if needed
        from jose import jwt, JWTError

        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[jwt_algorithm]
        )

        username: Optional[str] = payload.get("sub")
        user_id: Optional[int] = payload.get("uid")
        roles: Optional[list[str]] = payload.get("roles", [])

        if username is None and user_id is None:
            logger.warning("JWT verification failed: Token missing required claims (sub or uid).")
            raise credentials_exception

        # TODO: Add database user validation if needed

        logger.info(f"JWT token verified successfully for user: {username or user_id}")

        return {
            "authenticated_via": "jwt",
            "username": username,
            "user_id": user_id,
            "roles": roles,
        }

    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception from e
    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token validation.",
        ) from e

# TODO: Use these authentication functions in routes as needed
