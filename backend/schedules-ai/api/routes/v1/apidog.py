# === File: schedules-ai/api/routes/v1/apidog.py ===

"""
API Router for APIdog Integration (Version 1).

Provides endpoints to serve generated schedule JSON files to APIdog.
"""

import json
import logging
import os
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Response Models ---

class ScheduleTask(BaseModel):
    """Represents a single task in the schedule for APIdog."""
    start_time: str = Field(..., description="Start time of the task in HH:MM format.")
    end_time: str = Field(..., description="End time of the task in HH:MM format.")
    task: str = Field(..., description="Name of the task.")


class ScheduleResponse(BaseModel):
    """Response payload containing the schedule in APIdog format."""
    tasks: List[ScheduleTask] = Field(..., description="List of scheduled tasks.")


# --- Helper Functions ---

def get_schedule_file_path(schedule_id: UUID) -> str:
    """
    Constructs the file path for a schedule JSON file.

    Args:
        schedule_id: The unique identifier of the schedule.

    Returns:
        The file path to the schedule JSON file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base_dir, 'data', 'processed', f"schedule_{schedule_id}.json")


def list_available_schedules() -> List[Dict[str, str]]:
    """
    Lists all available schedule files in the processed data directory.

    Returns:
        A list of dictionaries containing schedule_id and file_path.
    """
    schedules = []
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    data_dir = os.path.join(base_dir, 'data', 'processed')

    if not os.path.exists(data_dir):
        return schedules

    for filename in os.listdir(data_dir):
        if filename.startswith('schedule_') and filename.endswith('.json'):
            schedule_id = filename.replace('schedule_', '').replace('.json', '')
            schedules.append({
                'schedule_id': schedule_id,
                'file_path': os.path.join(data_dir, filename)
            })

    return schedules


# --- API Endpoints ---

@router.get(
    "/schedules",
    response_model=List[Dict[str, str]],
    summary="List Available Schedules",
    description="Returns a list of all available schedule IDs that can be retrieved.",
    tags=["V1 - APIdog"],
)
async def list_schedules() -> List[Dict[str, str]]:
    """
    Lists all available schedule IDs.

    Returns:
        A list of dictionaries containing schedule_id.

    Raises:
        HTTPException: If an error occurs during retrieval.
    """
    logger.info("Received request to list all available schedules.")

    try:
        disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"

        if not disable_db:
            try:
                from api.db import list_schedules_from_db
                db_schedules = await list_schedules_from_db()

                if db_schedules:
                    logger.info(f"Found {len(db_schedules)} schedules in database.")
                    return db_schedules
            except Exception as db_error:
                logger.warning(f"Error accessing database: {db_error}")
        else:
            logger.info("Database connection disabled, using file-based schedules.")

        logger.info("Trying to get schedules from files.")
        file_schedules = list_available_schedules()
        return [{'schedule_id': s['schedule_id']} for s in file_schedules]
    except Exception as e:
        logger.exception("Error listing schedules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing schedules: {str(e)}",
        )


@router.get(
    "/schedule/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Get Schedule by ID",
    description="Retrieves a generated schedule by its ID in a format compatible with APIdog.",
    tags=["V1 - APIdog"],
)
async def get_schedule(schedule_id: UUID) -> ScheduleResponse:
    """
    Retrieves a schedule by its ID.

    Args:
        schedule_id: The unique identifier of the schedule.

    Raises:
        HTTPException: If the schedule is not found or an error occurs during retrieval.

    Returns:
        The requested schedule in APIdog format.
    """
    logger.info(f"Received request to get schedule with ID '{schedule_id}'.")

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
    summary="Get Latest Schedule",
    description="Retrieves the most recently generated schedule in a format compatible with APIdog.",
    tags=["V1 - APIdog"],
)
async def get_latest_schedule() -> ScheduleResponse:
    """
    Retrieves the most recently generated schedule.

    Raises:
        HTTPException: If no schedules are found or an error occurs during retrieval.

    Returns:
        The most recent schedule in APIdog format.
    """
    logger.info("Received request to get the latest schedule.")

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
