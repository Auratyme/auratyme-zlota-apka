# === File: schedules-ai/api/routes/v1/auth.py ===

"""
API Router for Authentication related endpoints (Version 1).

Provides endpoints for generating JWT tokens for testing and other
auth-related functionalities.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Path
from pydantic import BaseModel

from api.middleware.jwt_auth import create_jwt_token as create_token_util


logger = logging.getLogger(__name__)
router = APIRouter()

# --- Response Model for Token ---
class TokenResponse(BaseModel):
    """Response model for JWT token."""
    access_token: str
    token_type: str = "bearer"
    user_id: str

# --- API Endpoints ---

@router.get(
    "/generate-token/{user_id}",
    response_model=TokenResponse,
    summary="Generate Test JWT Token",
    description="Generates a JWT token for the given user_id. Useful for testing purposes.",
    tags=["V1 - Auth"],
)
async def generate_test_token(
    user_id: str = Path(..., description="The User ID to include in the token's 'sub' claim.")
) -> TokenResponse:
    """
    Generates a JWT token for a given user_id.

    This endpoint is intended for development and testing.
    It uses the `create_jwt_token` utility which should be configured
    with the same JWT secret and parameters as the token verification middleware.

    Args:
        user_id (str): The user ID for whom the token is generated.

    Returns:
        TokenResponse: An object containing the access token and user_id.

    Raises:
        HTTPException (500): If token generation fails.
    """
    logger.info(f"Request to generate token for user_id: {user_id}")
    try:
        token = create_token_util(user_id=user_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token generation failed: create_token_util returned None or empty.",
            )
        logger.info(f"Token generated successfully for user_id: {user_id}")
        return TokenResponse(access_token=token, user_id=user_id)
    except Exception as e:
        logger.exception(f"Error generating token for user_id {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during token generation: {str(e)}",
        )
