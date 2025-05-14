# === File: schedules-ai/api/routes/v1/user_schedules.py ===

"""
User schedules endpoints for the API.

This module provides endpoints for managing user schedules with JWT authentication.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.middleware.jwt_auth import JWTBearer, get_user_from_token

logger = logging.getLogger(__name__)

# --- Router Configuration ---
router = APIRouter(prefix="/v1/user-schedules", tags=["V1 - User Schedules"])
jwt_bearer = JWTBearer()


# --- Models ---

class Schedule(BaseModel):
    """Schedule model."""

    id: str = Field(..., description="The unique identifier of the schedule")
    name: str = Field(..., description="The name of the schedule")
    description: Optional[str] = Field(None, description="The description of the schedule")
    userId: str = Field(..., description="The ID of the user who owns the schedule")
    createdAt: str = Field(..., description="The creation timestamp of the schedule")
    updatedAt: str = Field(..., description="The last update timestamp of the schedule")


class CreateScheduleDto(BaseModel):
    """Data transfer object for creating a schedule."""

    name: str = Field(..., description="The name of the schedule")
    description: Optional[str] = Field(None, description="The description of the schedule")


class UpdateScheduleDto(BaseModel):
    """Data transfer object for updating a schedule."""

    name: Optional[str] = Field(None, description="The name of the schedule")
    description: Optional[str] = Field(None, description="The description of the schedule")


class DeleteScheduleOptions(BaseModel):
    """Options for deleting a schedule."""

    forceDelete: Optional[Dict[str, bool]] = Field(None, description="Force delete options")


class DeleteScheduleDto(BaseModel):
    """Data transfer object for deleting a schedule."""

    options: Optional[DeleteScheduleOptions] = Field(None, description="Delete options")


# --- Helper Functions ---

async def save_schedule(schedule: Schedule) -> bool:
    """
    Save a schedule to the database or file system.

    Args:
        schedule: The schedule to save.

    Returns:
        True if the schedule was saved successfully, False otherwise.
    """
    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import save_schedule_to_db
                await save_schedule_to_db(
                    schedule.id,
                    schedule.userId,
                    None,
                    schedule.model_dump()
                )
                return True
            except Exception as db_error:
                logger.warning(f"Error saving schedule to database: {db_error}")

        logger.info(f"Saving schedule {schedule.id} to file.")

        os.makedirs("data/user_schedules", exist_ok=True)

        file_path = f"data/user_schedules/schedule_{schedule.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schedule.model_dump(), f, indent=2)

        return True
    except Exception as e:
        logger.exception(f"Error saving schedule: {e}")
        return False


async def get_schedule_by_id(schedule_id: str, user_id: str) -> Optional[Schedule]:
    """
    Get a schedule by ID and user ID.

    Args:
        schedule_id: The ID of the schedule.
        user_id: The ID of the user.

    Returns:
        The schedule, or None if not found.
    """
    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import get_schedule_from_db
                db_schedule_data = await get_schedule_from_db(schedule_id)

                if db_schedule_data and db_schedule_data.get('userId') == user_id:
                    return Schedule(**db_schedule_data)
            except Exception as db_error:
                logger.warning(f"Error getting schedule from database: {db_error}")

        file_path = f"data/user_schedules/schedule_{schedule_id}.json"

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                schedule_data = json.load(f)

                if schedule_data.get('userId') == user_id:
                    return Schedule(**schedule_data)

        return None
    except Exception as e:
        logger.exception(f"Error getting schedule: {e}")
        return None


async def list_schedules_by_user_id(
    user_id: str,
    limit: int = 10,
    page: int = 0,
    sort_by: str = "desc",
    order_by: str = "createdAt"
) -> List[Schedule]:
    """
    List schedules by user ID.

    Args:
        user_id: The ID of the user.
        limit: The maximum number of schedules to return.
        page: The page number.
        sort_by: The sort direction (asc or desc).
        order_by: The field to sort by.

    Returns:
        A list of schedules.
    """
    try:
        schedules = []

        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import list_schedules_from_db_by_user_id
                db_schedules = await list_schedules_from_db_by_user_id(user_id)

                if db_schedules:
                    schedules = [Schedule(**s) for s in db_schedules]
            except Exception as db_error:
                logger.warning(f"Error listing schedules from database: {db_error}")

        if not schedules:
            os.makedirs("data/user_schedules", exist_ok=True)

            for file_name in os.listdir("data/user_schedules"):
                if file_name.startswith("schedule_") and file_name.endswith(".json"):
                    file_path = f"data/user_schedules/{file_name}"
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            schedule_data = json.load(f)

                            if schedule_data.get('userId') == user_id:
                                schedules.append(Schedule(**schedule_data))
                    except Exception as e:
                        logger.warning(f"Error reading schedule file {file_path}: {e}")

        if order_by in ["createdAt", "updatedAt", "name"]:
            reverse = sort_by.lower() == "desc"
            schedules.sort(key=lambda s: getattr(s, order_by), reverse=reverse)

        start = page * limit
        end = start + limit

        return schedules[start:end]
    except Exception as e:
        logger.exception(f"Error listing schedules: {e}")
        return []


async def delete_schedule(schedule_id: str, user_id: str) -> bool:
    """
    Delete a schedule by ID and user ID.

    Args:
        schedule_id: The ID of the schedule.
        user_id: The ID of the user.

    Returns:
        True if the schedule was deleted successfully, False otherwise.
    """
    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import delete_schedule_from_db
                success = await delete_schedule_from_db(schedule_id, user_id)

                if success:
                    return True
            except Exception as db_error:
                logger.warning(f"Error deleting schedule from database: {db_error}")

        file_path = f"data/user_schedules/schedule_{schedule_id}.json"

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)

                    if schedule_data.get('userId') != user_id:
                        return False
            except Exception as e:
                logger.warning(f"Error reading schedule file {file_path}: {e}")
                return False

            os.remove(file_path)
            return True

        return False
    except Exception as e:
        logger.exception(f"Error deleting schedule: {e}")
        return False


# --- API Endpoints ---

@router.get(
    "",
    response_model=List[Schedule],
    summary="List User Schedules",
    description="Returns a list of schedules for the authenticated user.",
)
async def find_many(
    token: str = Depends(jwt_bearer),
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(0, ge=0),
    sort_by: str = Query("desc", regex="^(asc|desc)$"),
    order_by: str = Query("createdAt", regex="^(createdAt|updatedAt|name)$"),
) -> List[Schedule]:
    """
    Lists schedules for the authenticated user.

    Args:
        token: JWT token from the authorization header
        limit: Maximum number of schedules to return
        page: Page number
        sort_by: Sort direction (asc or desc)
        order_by: Field to sort by

    Returns:
        A list of schedules.

    Raises:
        HTTPException: If authentication fails or an error occurs.
    """
    logger.info("Received request to list user schedules.")

    try:
        user_id = get_user_from_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            )

        schedules = await list_schedules_by_user_id(
            user_id,
            limit=limit,
            page=page,
            sort_by=sort_by,
            order_by=order_by
        )

        return schedules or []
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listing schedules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing schedules: {str(e)}",
        )


@router.get(
    "/{schedule_id}",
    response_model=Schedule,
    summary="Get Schedule by ID",
    description="Retrieves a schedule by its ID for the authenticated user.",
)
async def find_one(
    schedule_id: UUID,
    token: str = Depends(jwt_bearer),
) -> Schedule:
    """
    Retrieves a schedule by its ID for the authenticated user.

    Args:
        schedule_id: The unique identifier of the schedule
        token: JWT token from the authorization header

    Returns:
        The requested schedule.

    Raises:
        HTTPException: If authentication fails, schedule not found, or an error occurs.
    """
    logger.info(f"Received request to get schedule with ID '{schedule_id}'.")

    try:
        user_id = get_user_from_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            )

        schedule = await get_schedule_by_id(str(schedule_id), user_id)

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found.",
            )

        return schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving schedule {schedule_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the schedule: {str(e)}",
        )


@router.post(
    "",
    response_model=Schedule,
    summary="Create Schedule",
    description="Creates a new schedule for the authenticated user.",
    status_code=status.HTTP_201_CREATED,
)
async def create(
    create_dto: CreateScheduleDto,
    token: str = Depends(jwt_bearer),
) -> Schedule:
    """
    Creates a new schedule for the authenticated user.

    Args:
        create_dto: The schedule data
        token: JWT token from the authorization header

    Returns:
        The created schedule.

    Raises:
        HTTPException: If authentication fails or an error occurs.
    """
    logger.info("Received request to create a new schedule.")

    try:
        user_id = get_user_from_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            )

        now = datetime.now().isoformat()
        schedule = Schedule(
            id=str(uuid4()),
            name=create_dto.name,
            description=create_dto.description,
            userId=user_id,
            createdAt=now,
            updatedAt=now,
        )

        success = await save_schedule(schedule)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save schedule.",
            )

        return schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating schedule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the schedule: {str(e)}",
        )


@router.patch(
    "/{schedule_id}",
    response_model=None,
    summary="Update Schedule",
    description="Updates a schedule by its ID for the authenticated user.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_one(
    schedule_id: UUID,
    update_dto: UpdateScheduleDto,
    token: str = Depends(jwt_bearer),
) -> None:
    """
    Updates a schedule by its ID for the authenticated user.

    Args:
        schedule_id: The unique identifier of the schedule
        update_dto: The schedule data to update
        token: JWT token from the authorization header

    Raises:
        HTTPException: If authentication fails, schedule not found, or an error occurs.
    """
    logger.info(f"Received request to update schedule with ID '{schedule_id}'.")

    try:
        user_id = get_user_from_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            )

        schedule = await get_schedule_by_id(str(schedule_id), user_id)

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found.",
            )

        if update_dto.name is not None:
            schedule.name = update_dto.name

        if update_dto.description is not None:
            schedule.description = update_dto.description

        schedule.updatedAt = datetime.now().isoformat()

        success = await save_schedule(schedule)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save schedule.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating schedule {schedule_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the schedule: {str(e)}",
        )


@router.delete(
    "/{schedule_id}",
    response_model=None,
    summary="Delete Schedule",
    description="Deletes a schedule by its ID for the authenticated user.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_one(
    schedule_id: UUID,
    token: str = Depends(jwt_bearer),
) -> None:
    """
    Deletes a schedule by its ID for the authenticated user.

    Args:
        schedule_id: The unique identifier of the schedule
        token: JWT token from the authorization header

    Raises:
        HTTPException: If authentication fails, schedule not found, or an error occurs.
    """
    logger.info(f"Received request to delete schedule with ID '{schedule_id}'.")

    try:
        user_id = get_user_from_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            )

        success = await delete_schedule(str(schedule_id), user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting schedule {schedule_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the schedule: {str(e)}",
        )
