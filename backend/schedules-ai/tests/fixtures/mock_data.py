# === File: scheduler-core/tests/fixtures/mock_data.py ===

"""
Mock Data Fixtures for Testing.

This module provides reusable mock data objects and generators for use
in unit and integration tests across the scheduler-core application.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

# Attempt to import core models to create realistic mock data
try:
    from src.core.task_prioritizer import Task, TaskPriority, EnergyLevel
    # Import other necessary models
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logging.getLogger(__name__).warning("Could not import core models for mock_data. Mock data might be less realistic.")
    # Define dummy classes if needed
    from enum import Enum
    class TaskPriority(Enum): MEDIUM = 3
    class EnergyLevel(Enum): MEDIUM = 2
    class Chronotype(Enum): INTERMEDIATE = "intermediate"
    class Task: pass # type: ignore
    class ChronotypeProfile: pass # type: ignore
    class SleepMetrics: pass # type: ignore


logger = logging.getLogger(__name__)

# --- Example Mock Data Functions/Constants ---

def create_mock_task(
    title: str = "Mock Task",
    priority: TaskPriority = TaskPriority.MEDIUM,
    energy: EnergyLevel = EnergyLevel.MEDIUM,
    duration_minutes: int = 60,
    **kwargs: Any
) -> Task:
    """Creates a mock Task object with default or specified values."""
    if not MODELS_AVAILABLE:
         logger.warning("Cannot create realistic mock Task, core models not imported.")
         return {"title": title, "priority": priority, "duration": duration_minutes, **kwargs} # Return dict as fallback

    # Use the actual Task class if available
    task_data = {
        "title": title,
        "priority": priority,
        "energy_level": energy,
        "duration": timedelta(minutes=duration_minutes),
        **kwargs # Allow overriding other fields like id, deadline, etc.
    }
    # Ensure required fields for Task are present if using the real class
    # task_data.setdefault('id', uuid4()) # Example if ID is needed but not default_factory

    try:
        return Task(**task_data) # type: ignore
    except Exception as e:
         logger.error(f"Failed to create mock Task object: {e}")
         # Fallback to dictionary representation
         return {"title": title, "priority": priority.name, "duration_minutes": duration_minutes, **kwargs}


def get_mock_user_profile(user_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Returns a dictionary representing a mock user profile."""
    return {
        "user_id": user_id or uuid4(),
        "name": "Mock User",
        "age": 30,
        "meq_score": 55, # Intermediate
        # Add other relevant profile fields
    }

def get_mock_preferences() -> Dict[str, Any]:
    """Returns a dictionary representing mock user preferences."""
    return {
        "work_start_time": "09:00",
        "work_end_time": "17:30",
        "sleep_need_scale": 50.0,
        "chronotype_scale": 50.0,
        "break_frequency_minutes": 90,
        "break_duration_minutes": 10,
    }

# Add more functions or constants for other mock data types as needed
# e.g., mock_fixed_events, mock_sleep_metrics, mock_chronotype_profile

logger.info("Mock data fixtures module loaded.")

# Example of using the mock data function
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    mock_task1 = create_mock_task(title="Test High Prio", priority=TaskPriority.HIGH)
    mock_task2 = create_mock_task(duration_minutes=90, tags=["testing"])
    mock_profile = get_mock_user_profile()
    mock_prefs = get_mock_preferences()

    print("--- Example Mock Data ---")
    print(f"Task 1: {mock_task1}")
    print(f"Task 2: {mock_task2}")
    print(f"Profile: {mock_profile}")
    print(f"Preferences: {mock_prefs}")
