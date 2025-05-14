# === File: schedules-ai/api/routes/v1/schedule.py ===

"""
API Router for Schedule Generation and Retrieval (Version 1).

Provides endpoints to generate new personalized schedules based on user input
and retrieve previously generated schedules.
"""

import logging
from datetime import date, time, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

from api.dependencies import get_scheduler
from src.core.scheduler import (
    GeneratedSchedule,
    ScheduleInputData,
    Scheduler,
)
from src.core.task_prioritizer import Task as InternalTask

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Request Models ---

class TaskInput(BaseModel):
    """Structure for defining a task in the schedule generation request."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), description="Unique identifier for the task (optional, will be generated if missing).")
    name: str = Field(..., description="Descriptive name of the task.", examples=["Write project report"])
    duration_minutes: int = Field(..., gt=0, description="Estimated duration of the task in minutes.", examples=[90])
    priority: int = Field(default=3, ge=1, le=5, description="Priority level (1=Lowest, 5=Highest).", examples=[4])
    deadline: Optional[date] = Field(default=None, description="Optional deadline date for the task.")
    preferred_start_time: Optional[time] = Field(default=None, description="Optional preferred start time.")
    preferred_end_time: Optional[time] = Field(default=None, description="Optional preferred end time.")
    energy_level_required: Optional[int] = Field(default=None, ge=1, le=5, description="Estimated energy level required (1-5).")
    context: Optional[str] = Field(default=None, description="Context required (e.g., 'at_computer', 'calls').", examples=["at_computer"])

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Analyze user feedback data",
                "duration_minutes": 120,
                "priority": 5,
                "deadline": "2025-04-10",
                "energy_level_required": 4,
                "context": "at_computer",
            }
        }


class FixedEventInput(BaseModel):
    """Structure for defining a fixed event in the schedule generation request."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), description="Unique identifier for the event.")
    name: str = Field(..., description="Name of the fixed event.", examples=["Team Meeting"])
    start_time: time = Field(..., description="Start time of the fixed event.")
    end_time: time = Field(..., description="End time of the fixed event.")

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, end_time, values):
        if 'start_time' in values and end_time <= values['start_time']:
            raise ValueError('Fixed event end_time must be after start_time')
        return end_time

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Doctor's Appointment",
                "start_time": "14:00:00",
                "end_time": "15:00:00",
            }
        }


class ScheduleGenerationRequest(BaseModel):
    """Request payload for generating a new personalized schedule."""

    user_id: UUID = Field(..., description="Unique identifier of the user for whom the schedule is generated.")
    target_date: date = Field(..., description="The target date for which the schedule should be generated.")
    tasks: List[TaskInput] = Field(..., description="List of tasks to be scheduled.")
    fixed_events: List[FixedEventInput] = Field(
        default_factory=list, description="List of fixed events (appointments, meetings) already scheduled for the target date."
    )
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User-specific preferences influencing schedule generation (e.g., work start/end times, break frequency, chronotype settings).",
        examples=[{"preferred_work_start": "09:00", "preferred_work_end": "17:00", "break_duration_minutes": 15}],
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional user profile information (e.g., age, MEQ score, typical sleep patterns) relevant for scheduling.",
        examples=[{"age": 35, "chronotype_preference": "moderate_evening"}],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "target_date": "2025-04-08",
                "tasks": [
                    TaskInput.Config.json_schema_extra["example"],
                    {
                        "name": "Prepare presentation slides",
                        "duration_minutes": 60,
                        "priority": 4,
                    },
                ],
                "fixed_events": [FixedEventInput.Config.json_schema_extra["example"]],
                "preferences": {"preferred_work_start": "09:00", "preferred_work_end": "17:30"},
                "user_profile": {"chronotype_preference": "early_bird"},
            }
        }


# --- Response Models ---

class ScheduledItem(BaseModel):
    """Represents a single item (task, break, fixed event) in the generated schedule."""
    id: str = Field(..., description="Unique identifier of the scheduled item (can be task ID, event ID, or generated break ID).")
    type: str = Field(..., description="Type of the item.", examples=["task", "break", "fixed_event"])
    name: str = Field(..., description="Name of the item.", examples=["Write project report", "Lunch Break", "Team Meeting"])
    start_time: time = Field(..., description="Scheduled start time.")
    end_time: time = Field(..., description="Scheduled end time.")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details specific to the item type (e.g., original task priority, break type).")


class ScheduleGenerationResponse(BaseModel):
    """Response payload containing the generated schedule and related information."""

    schedule_id: UUID = Field(default_factory=uuid4, description="Unique identifier for this generated schedule instance.")
    user_id: UUID = Field(..., description="Identifier of the user for whom the schedule was generated.")
    target_date: date = Field(..., description="The date for which the schedule applies.")
    scheduled_items: List[ScheduledItem] = Field(..., description="The ordered list of scheduled tasks, breaks, and fixed events.")
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Calculated metrics about the generated schedule (e.g., total work time, break time, goal completion estimate).",
        examples=[{"total_scheduled_task_minutes": 240, "estimated_completion_rate": 0.9}],
    )
    explanations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Explanations for scheduling decisions (e.g., why a task was placed at a specific time, warnings about conflicts).",
        examples=[{"task_placement_reasoning": "High-priority task scheduled during peak energy time."}],
    )


# --- API Endpoints ---

@router.post(
    "/generate",
    response_model=ScheduleGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Personalized Schedule",
    description="Generates a personalized and optimized schedule for the specified user and date, "
    "considering tasks, fixed events, user preferences, and profile information. "
    "Returns the ordered list of scheduled items along with metrics and explanations.",
    tags=["V1 - Schedule"],
)
async def generate_schedule(
    request_data: ScheduleGenerationRequest,
    scheduler: Scheduler = Depends(get_scheduler),
) -> ScheduleGenerationResponse:
    """
    Handles the request to generate a personalized schedule.

    Args:
        request_data (ScheduleGenerationRequest): The input data containing tasks,
                                                  events, preferences, etc.
        scheduler (Scheduler): Dependency-injected scheduler service instance.

    Raises:
        HTTPException (400 Bad Request): If the input data format is invalid
                                         (beyond Pydantic validation).
        HTTPException (422 Unprocessable Entity): If Pydantic validation fails.
        HTTPException (500 Internal Server Error): If an unexpected error occurs
                                                   during schedule generation.

    Returns:
        ScheduleGenerationResponse: The generated schedule details.
    """
    logger.info(
        f"Received schedule generation request for user '{request_data.user_id}', "
        f"target date '{request_data.target_date}' with {len(request_data.tasks)} tasks "
        f"and {len(request_data.fixed_events)} fixed events."
    )

    # --- Input Data Preparation ---
    try:
        internal_tasks = [
            InternalTask(
                id=t.id,
                name=t.name,
                duration=timedelta(minutes=t.duration_minutes),
                priority=t.priority,
                deadline=t.deadline,
            )
            for t in request_data.tasks
        ]
        internal_fixed_events = [
             fe.model_dump()
             for fe in request_data.fixed_events
        ]

    except Exception as e:
        logger.error(
            f"Error converting request data to internal format for user {request_data.user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format for tasks or fixed events.",
        )

    input_data = ScheduleInputData(
        user_id=request_data.user_id,
        target_date=request_data.target_date,
        tasks=internal_tasks,
        fixed_events_input=internal_fixed_events,
        preferences=request_data.preferences,
        user_profile=request_data.user_profile,
    )

    # --- Call Scheduler Service ---
    try:
        logger.debug(f"Calling scheduler service for user {request_data.user_id}...")
        generated_schedule: GeneratedSchedule = await scheduler.generate_schedule(input_data)
        logger.info(f"Schedule generated successfully for user {request_data.user_id}.")

        # --- Format Response ---
        response_items = [
            ScheduledItem(
                id=item.get("id", str(uuid4())),
                type=item.get("type", "unknown"),
                name=item.get("name", "Unnamed Item"),
                start_time=item.get("start_time"),
                end_time=item.get("end_time"),
                details=item.get("details"),
            )
            for item in generated_schedule.scheduled_items
            if item.get("start_time") and item.get("end_time")
        ]

        response = ScheduleGenerationResponse(
            schedule_id=generated_schedule.schedule_id,
            user_id=generated_schedule.user_id,
            target_date=generated_schedule.target_date,
            scheduled_items=response_items,
            metrics=generated_schedule.metrics,
            explanations=generated_schedule.explanations,
        )
        return response

    # --- Error Handling ---
    except Exception as e:
        logger.exception(
            f"Unexpected error during schedule generation for user {request_data.user_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during schedule generation.",
        )


@router.get(
    "/{user_id}/{target_date}",
    response_model=ScheduleGenerationResponse,
    summary="Get Existing Schedule by User and Date",
    description="Retrieves a previously generated schedule for a specific user and date. "
                "**Note:** This is currently a placeholder and returns mock data.",
    tags=["V1 - Schedule"],
)
async def get_schedule(user_id: UUID, target_date: date) -> ScheduleGenerationResponse:
    """
    Retrieves a previously generated schedule.

    **(Placeholder Implementation)** - Needs integration with data storage.

    Args:
        user_id (UUID): The identifier of the user.
        target_date (date): The target date of the schedule.

    Raises:
        HTTPException (404 Not Found): If no schedule is found for the given user/date.
        HTTPException (500 Internal Server Error): If an error occurs during retrieval.

    Returns:
        ScheduleGenerationResponse: The requested schedule details.
    """
    logger.info(f"Received request to get schedule for user '{user_id}', date '{target_date}'.")

    # --- TODO: Implement Database/Storage Logic ---
    # Replace this mock implementation with actual database query
    # schedule_record = await db.schedules.find_one({"user_id": user_id, "target_date": target_date})
    schedule_record = None # Simulate not found for now, or create mock below

    if schedule_record:
        logger.info(f"Schedule found for user '{user_id}', date '{target_date}'.")
        pass 
    else:
        # --- Mock Response (Remove when DB logic is added) ---
        logger.warning(f"No schedule found for user '{user_id}', date '{target_date}'. Returning mock data (placeholder).")
        mock_items = [
            ScheduledItem(id="task_1", type="task", name="Mock Task 1", start_time=time(9, 0), end_time=time(10, 30)),
            ScheduledItem(id="break_1", type="break", name="Coffee Break", start_time=time(10, 30), end_time=time(10, 45)),
            ScheduledItem(id="task_2", type="task", name="Mock Task 2", start_time=time(10, 45), end_time=time(12, 0)),
        ]
        mock_schedule = ScheduleGenerationResponse(
            user_id=user_id,
            target_date=target_date,
            scheduled_items=mock_items,
            metrics={"status": "mock", "efficiency": 0.8},
            explanations={"reasoning": "This is mock data from a placeholder endpoint."},
        )
        return mock_schedule
