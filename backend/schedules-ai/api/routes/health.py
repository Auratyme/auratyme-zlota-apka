# === File: schedules-ai/api/routes/health.py ===

"""
API Router for Health Checks.

Provides basic endpoints to verify the operational status of the
schedules-ai API server. This is crucial for monitoring, load balancers,
and deployment systems.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Response Models ---

class HealthStatus(BaseModel):
    """Standard response model for the basic health check."""

    status: str = Field(
        default="OK",
        description="Indicates the overall health status.",
        examples=["OK"],
    )
    message: str = Field(
        default="schedules-ai API is running.",
        description="A human-readable message about the API status.",
        examples=["schedules-ai API is running."],
    )


class DependencyStatus(BaseModel):
    """Model for reporting the status of a single dependency."""
    name: str = Field(..., description="Name of the dependency.", examples=["Database", "LLM Service"])
    status: str = Field(..., description="Status of the dependency.", examples=["connected", "available", "unavailable", "error"])
    details: Optional[str] = Field(None, description="Optional details about the status or error.", examples=["Connection successful", "Timeout during connection attempt"])


class DetailedHealthStatus(HealthStatus):
    """Response model for a detailed health check, including dependencies."""
    dependencies: List[DependencyStatus] = Field(
        default=[],
        description="Status of critical external dependencies.",
    )


# --- API Endpoints ---

@router.get(
    "",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Basic API Health Check",
    description="Returns a simple status message indicating the API is operational. "
                "This endpoint should be fast and not check external dependencies.",
    tags=["Health"],
)
async def get_basic_health() -> HealthStatus:
    """
    Provides a basic health check.

    Confirms that the API server process is running and responding to requests.
    It does not typically check external dependencies like databases.
    """
    logger.debug("Basic health check endpoint '/health' called.")
    return HealthStatus()
