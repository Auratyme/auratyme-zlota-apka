# === File: schedules-ai/api/routes/v1/user.py ===

"""
API Router for User Management (Profile, Preferences) - Version 1.

Provides endpoints for retrieving user profile information and managing
user-specific preferences that influence schedule generation.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)
router = APIRouter()


# TODO: Implement user service dependency


# --- Request/Response Models ---

class UserPreferences(BaseModel):
    """Detailed structure for user preferences."""
    theme: Optional[str] = Field(default="light", description="UI theme preference.", examples=["dark", "light"])
    preferred_work_start_time: Optional[str] = Field(default="09:00", description="Preferred start time for work tasks (HH:MM).", examples=["08:30"])
    preferred_work_end_time: Optional[str] = Field(default="17:00", description="Preferred end time for work tasks (HH:MM).", examples=["17:30"])
    sleep_duration_goal_hours: Optional[float] = Field(default=8.0, ge=4, le=12, description="Target sleep duration in hours.", examples=[7.5])

    class Config:
        json_schema_extra = {
            "example": {
                "theme": "dark",
                "preferred_work_start_time": "08:45",
                "sleep_duration_goal_hours": 7.75,
            }
        }


class UserProfileResponse(BaseModel):
    """Response model for user profile data."""
    user_id: UUID = Field(..., description="Unique identifier of the user.")
    name: Optional[str] = Field(default=None, description="User's display name.", examples=["Jane Doe"])
    email: Optional[str] = Field(default=None, description="User's email address (consider privacy implications).", examples=["jane.doe@example.com"])
    age: Optional[int] = Field(default=None, ge=0, description="User's age.", examples=[32])
    avatar_url: Optional[HttpUrl] = Field(default=None, description="URL to the user's avatar image.")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="User-specific preferences.")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "age": 32,
                "avatar_url": "https://example.com/avatars/jane.png",
                "preferences": UserPreferences.Config.json_schema_extra["example"],
            }
        }


class UserPreferencesUpdateRequest(BaseModel):
    """Request model for updating user preferences."""
    preferences: UserPreferences = Field(..., description="The complete set of updated user preferences.")


# --- API Endpoints ---

@router.get(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    summary="Get User Profile and Preferences",
    description="Retrieves the profile details and configured preferences for a specific user. "
                "**Note:** This is currently a placeholder and returns mock data.",
    tags=["V1 - Users"],
)
async def get_user_profile(
    user_id: UUID,
) -> UserProfileResponse:
    """
    Retrieves the profile and preferences for a specific user by their ID.

    Args:
        user_id: The unique identifier of the user to retrieve.

    Returns:
        The user's profile and preference data.
    """
    logger.info(f"Received request to get profile for user_id: {user_id}")

    # TODO: Implement Database/Service Logic
    try:
        user_data = None
        if str(user_id) == "f47ac10b-58cc-4372-a567-0e02b2c3d479":
             user_data = UserProfileResponse.Config.json_schema_extra["example"]
             logger.warning(f"User profile endpoint returning mock data for user {user_id}.")

        if user_data:
            logger.info(f"Profile found for user_id: {user_id}")
            return UserProfileResponse(**user_data)
        else:
            logger.warning(f"User profile not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    except Exception:
        logger.exception(f"Error retrieving profile for user_id: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while retrieving the user profile.",
        )


@router.put(
    "/{user_id}/preferences",
    response_model=UserProfileResponse,
    summary="Update User Preferences",
    description="Updates the preferences for a specific user. Requires the complete "
                "set of preferences in the request body. "
                "**Note:** This is currently a placeholder and returns mock data.",
    tags=["V1 - Users"],
)
async def update_user_preferences(
    user_id: UUID,
    update_data: UserPreferencesUpdateRequest,
) -> UserProfileResponse:
    """
    Updates the preferences for a specific user.

    Args:
        user_id: The unique identifier of the user whose preferences are to be updated.
        update_data: The new preference values.

    Returns:
        The complete user profile including the updated preferences.
    """
    logger.info(
        f"Received request to update preferences for user_id: {user_id} "
        f"with data: {update_data.preferences.model_dump()}"
    )

    # TODO: Implement Database/Service Logic
    try:
        updated_profile_data = None
        if str(user_id) == "f47ac10b-58cc-4372-a567-0e02b2c3d479":
             mock_profile = UserProfileResponse.Config.json_schema_extra["example"].copy()
             mock_profile["preferences"] = update_data.preferences.model_dump()
             updated_profile_data = mock_profile
             logger.warning(f"User preferences endpoint returning mock updated data for user {user_id}.")

        if updated_profile_data:
            logger.info(f"Preferences updated successfully for user_id: {user_id}")
            return UserProfileResponse(**updated_profile_data)
        else:
            logger.warning(f"User not found during preference update attempt for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    except Exception:
        logger.exception(f"Error updating preferences for user_id: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while updating user preferences.",
        )

# TODO: Implement additional endpoints:
# - POST / - Create a new user
# - DELETE /{user_id} - Delete a user account
# - PUT /{user_id}/profile - Update core profile details
