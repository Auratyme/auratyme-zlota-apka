# === File: schedules-ai/api/routes/v1/auth_schedules.py ===

"""
Authenticated schedule endpoints for the API.

This module provides endpoints for retrieving schedules with JWT authentication.
"""

import json
import logging
import os
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.middleware.jwt_auth import JWTBearer
from api.routes.v1.apidog import (ScheduleResponse, get_schedule_file_path,
                                 list_available_schedules)

logger = logging.getLogger(__name__)

# --- Router Configuration ---
router = APIRouter(prefix="/v1/auth", tags=["V1 - Authenticated"])

jwt_bearer = JWTBearer()


# --- Response Models ---

class ScheduleListResponse(BaseModel):
    """Response model for listing schedules."""

    schedules: List[Dict[str, str]] = Field(..., description="List of available schedules")


# --- API Endpoints ---

@router.get(
    "/schedules",
    response_model=ScheduleListResponse,
    summary="List Available Schedules (Authenticated)",
    description="Returns a list of all available schedule IDs that can be retrieved. Requires authentication.",
)
async def list_schedules(_: str = Depends(jwt_bearer)) -> ScheduleListResponse:
    """
    Lists all available schedule IDs. Requires authentication.

    Args:
        _: JWT token from the authorization header (automatically validated)

    Returns:
        A list of dictionaries containing schedule_id.

    Raises:
        HTTPException: If an error occurs during retrieval.
    """
    logger.info("Received authenticated request to list all available schedules.")

    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import list_schedules_from_db
                db_schedules = await list_schedules_from_db()

                if db_schedules:
                    logger.info(f"Found {len(db_schedules)} schedules in database.")
                    return ScheduleListResponse(schedules=db_schedules)
            except Exception as db_error:
                logger.warning(f"Error accessing database: {db_error}")
        else:
            logger.info("Database connection disabled, using file-based schedules.")

        logger.info("Trying to get schedules from files.")
        file_schedules = list_available_schedules()
        return ScheduleListResponse(schedules=[{'schedule_id': s['schedule_id']} for s in file_schedules])
    except Exception as e:
        logger.exception("Error listing schedules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing schedules: {str(e)}",
        )


@router.get(
    "/schedule/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Get Schedule by ID (Authenticated)",
    description="Retrieves a generated schedule by its ID. Requires authentication.",
)
async def get_schedule(
    schedule_id: UUID,
    _: str = Depends(jwt_bearer),
) -> ScheduleResponse:
    """
    Retrieves a schedule by its ID. Requires authentication.

    Args:
        schedule_id: The unique identifier of the schedule
        _: JWT token from the authorization header (automatically validated)

    Returns:
        The requested schedule in APIdog format.

    Raises:
        HTTPException: If the schedule is not found or an error occurs during retrieval.
    """
    logger.info(f"Received authenticated request to get schedule with ID '{schedule_id}'.")

    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import get_schedule_from_db
                db_schedule_data = await get_schedule_from_db(schedule_id)

                if db_schedule_data:
                    logger.info(f"Found schedule {schedule_id} in database.")
                    return ScheduleResponse(**db_schedule_data)
            except Exception as db_error:
                logger.warning(f"Error accessing database: {db_error}")
        else:
            logger.info("Database connection disabled, using file-based schedules.")

        logger.info(f"Trying to get schedule {schedule_id} from file.")
        file_path = get_schedule_file_path(schedule_id)

        if not os.path.exists(file_path):
            logger.warning(f"Schedule file not found: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found.",
            )

        with open(file_path, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)

            if not disable_db:
                try:
                    from api.db import save_schedule_to_db
                    await save_schedule_to_db(schedule_id, None, None, schedule_data)
                except Exception as db_error:
                    logger.warning(f"Error saving schedule to database: {db_error}")

        return ScheduleResponse(**schedule_data)

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing schedule data: {str(e)}",
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.exception(f"Error retrieving schedule {schedule_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the schedule: {str(e)}",
        )


@router.get(
    "/latest-schedule",
    response_model=ScheduleResponse,
    summary="Get Latest Schedule (Authenticated)",
    description="Retrieves the most recently generated schedule. Requires authentication.",
)
async def get_latest_schedule(_: str = Depends(jwt_bearer)) -> ScheduleResponse:
    """
    Retrieves the most recently generated schedule. Requires authentication.

    Args:
        _: JWT token from the authorization header (automatically validated)

    Returns:
        The most recent schedule in APIdog format.

    Raises:
        HTTPException: If no schedules are found or an error occurs during retrieval.
    """
    logger.info("Received authenticated request to get the latest schedule.")

    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import get_latest_schedule_from_db
                db_schedule_data = await get_latest_schedule_from_db()

                if db_schedule_data:
                    logger.info("Found latest schedule in database.")
                    return ScheduleResponse(**db_schedule_data)
            except Exception as db_error:
                logger.warning(f"Error accessing database: {db_error}")
        else:
            logger.info("Database connection disabled, using file-based schedules.")

        logger.info("Trying to get latest schedule from files.")
        schedules = list_available_schedules()

        if not schedules:
            logger.warning("No schedules found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No schedules found.",
            )

        schedules.sort(key=lambda s: os.path.getmtime(s['file_path']), reverse=True)
        latest_schedule = schedules[0]

        with open(latest_schedule['file_path'], 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)

            if not disable_db:
                try:
                    from api.db import save_schedule_to_db
                    schedule_id = latest_schedule['schedule_id']
                    await save_schedule_to_db(schedule_id, None, None, schedule_data)
                except Exception as db_error:
                    logger.warning(f"Error saving schedule to database: {db_error}")

        return ScheduleResponse(**schedule_data)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.exception("Error retrieving latest schedule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the latest schedule: {str(e)}",
        )


# --- Development Endpoints ---

@router.get(
    "/generate-token/{user_id}",
    summary="Generate Test Token (Development Only)",
    description="Generates a test JWT token for the specified user ID. For development use only.",
)
async def generate_test_token(user_id: str) -> Dict[str, str]:
    """
    Generates a test JWT token for the specified user ID.

    Args:
        user_id: The user ID to include in the token

    Returns:
        A dictionary containing the generated token.

    Raises:
        HTTPException: If token generation fails or the endpoint is accessed in non-development mode.
    """
    try:
        if os.environ.get("APP_ENV", "development") != "development":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only available in development mode.",
            )

        from api.middleware.jwt_auth import create_jwt_token

        try:
            token = create_jwt_token(user_id)

            return {
                "token": token,
                "token_type": "bearer",
                "user_id": user_id,
            }
        except Exception as e:
            logger.exception(f"Error creating JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating JWT token: {str(e)}",
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.exception(f"Error in generate_test_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )
