# === File: schedules-ai/api/routes/v1/feedback.py ===

"""
API Router for User Feedback Management (Version 1).

Provides endpoints for users to submit feedback regarding their generated
schedules, such as ratings and comments.
"""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from api.dependencies import get_user_input_collector
from feedback.collectors.user_input import UserFeedback, UserInputCollector

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Request/Response Models ---

class FeedbackSubmissionRequest(BaseModel):
    """Request payload for submitting user feedback about a specific schedule."""

    user_id: Annotated[UUID, Field(..., description="The unique identifier of the user submitting feedback.")]
    schedule_date: Annotated[date, Field(..., description="The date of the schedule for which feedback is being provided.")]
    rating: Annotated[int, Field(..., ge=1, le=5, description="User's rating of the schedule (1=Very Bad, 5=Very Good).", example=4)]
    comment: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=1000,
            strip_whitespace=True,
            description="Optional textual comment providing more details about the feedback.",
            example="Felt a bit rushed in the morning, but the afternoon was great!"
        )
    ]
    schedule_version_id: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Optional identifier for the specific version of the schedule being rated.",
            example="sched_v2.1_abc"
        )
    ]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "schedule_date": "2025-04-07",
                "rating": 5,
                "comment": "This schedule worked perfectly for my energy levels!",
                "schedule_version_id": "v3_final",
            }
        }


class FeedbackSubmissionResponse(BaseModel):
    """Response model confirming successful feedback submission."""

    message: Annotated[str, Field(default="Feedback submitted successfully.", description="Confirmation message.")]
    feedback_id: Annotated[UUID, Field(..., description="The unique identifier assigned to the submitted feedback record.")]

# --- API Endpoints ---

@router.post(
    "/",
    response_model=FeedbackSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit User Feedback for a Schedule",
    description="Allows a user to submit their rating and optional comments about a generated schedule "
                "for a specific date. This feedback is crucial for the system to learn and improve future schedule generation.",
    tags=["V1 - Feedback"]
)
async def submit_feedback(
    submission: FeedbackSubmissionRequest,
    collector: UserInputCollector = Depends(get_user_input_collector),
) -> FeedbackSubmissionResponse:
    """
    Receives and processes user feedback for a given schedule date.

    Args:
        submission: The feedback data submitted by the user.
        collector: Dependency-injected service responsible for storing and processing feedback.

    Raises:
        HTTPException: If the feedback data is invalid or cannot be processed.

    Returns:
        Confirmation of successful submission, including the ID of the stored feedback record.
    """
    logger.info(
        f"Received feedback submission request for user '{submission.user_id}' "
        f"regarding schedule date '{submission.schedule_date}' (Rating: {submission.rating})."
    )

    try:
        stored_feedback: Optional[UserFeedback] = await collector.collect_feedback(
            user_id=submission.user_id,
            schedule_date=submission.schedule_date,
            rating=submission.rating,
            comment=submission.comment,
            schedule_version_id=submission.schedule_version_id,
        )

        if stored_feedback and stored_feedback.feedback_id:
            logger.info(f"Feedback successfully stored with ID: {stored_feedback.feedback_id}")
            return FeedbackSubmissionResponse(feedback_id=stored_feedback.feedback_id)
        else:
            logger.warning(
                "Feedback collector processed the request but did not return a stored feedback object or ID. "
                f"User: {submission.user_id}, Date: {submission.schedule_date}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process feedback submission. Possible validation error or duplicate.",
            )

    except ValueError as ve:
        logger.warning(
            f"Invalid feedback submission data for user {submission.user_id}, date {submission.schedule_date}: {ve}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feedback data: {ve}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error processing feedback for user {submission.user_id}, date {submission.schedule_date}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing feedback.",
        )

# TODO: Implement additional endpoints:
# - GET /?user_id={user_id}&schedule_date={date} - Retrieve feedback for a specific user/date
# - GET /{feedback_id} - Retrieve a specific feedback record by ID
# - DELETE /{feedback_id} - Delete a feedback record (admin/user specific)
