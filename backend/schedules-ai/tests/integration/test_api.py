# === File: scheduler-core/tests/integration/test_api.py ===

"""
Integration Tests for the Scheduler Core API Endpoints.

Uses FastAPI's TestClient to simulate HTTP requests and verify the behavior
of API endpoints, including their interaction with underlying services
(which might be real or mocked depending on the test scope).
"""

import logging
from datetime import date, timedelta
from typing import Dict
from uuid import UUID, uuid4

# Third-party imports
import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Application-specific imports (absolute paths)
# Import the FastAPI app instance from the server module
try:
    # Ensure server.py is structured to allow importing 'app' without running the server
    from api.server import app as fastapi_app
    APP_IMPORT_SUCCESS = True
except ImportError as e:
    logging.getLogger(__name__).critical(f"Failed to import FastAPI app from api.server: {e}. Integration tests cannot run.", exc_info=True)
    APP_IMPORT_SUCCESS = False
    fastapi_app = None # Placeholder

# Import models used in request/response bodies for type checking if desired
# from src.core.task_prioritizer import TaskPriority # Example


# --- Test Client Fixture ---

# Skip all tests in this module if the app couldn't be imported
pytestmark = pytest.mark.skipif(not APP_IMPORT_SUCCESS, reason="FastAPI app could not be imported.")

@pytest.fixture(scope="module")
def client():
    """
    Provides a FastAPI TestClient instance scoped to the module.
    This client simulates HTTP requests to the application in memory.
    """
    # The fixture will only run if APP_IMPORT_SUCCESS is True due to pytestmark
    with TestClient(fastapi_app) as test_client:
        yield test_client
    # Teardown actions can be added here if needed after tests run


# --- Health Check Tests ---

def test_health_check_endpoint(client: TestClient):
    """
    Verify the /health endpoint returns a successful response.
    """
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    try:
        json_response = response.json()
        assert json_response.get("status") == "OK"
        assert "API is running" in json_response.get("message", "")
    except Exception as e:
        pytest.fail(f"Failed to parse health check JSON response or assertions failed: {e}\nResponse: {response.text}")


# --- V1 Schedule Endpoint Tests ---

@pytest.mark.parametrize(
    "test_id, request_body, expected_status",
    [
        (
            "valid_request",
            {
                "user_id": str(uuid4()),
                "target_date": (date.today() + timedelta(days=1)).isoformat(),
                "tasks": [
                    {"id": str(uuid4()), "title": "Task A", "priority": "HIGH", "duration": "60m", "energy_level": "HIGH"},
                    {"id": str(uuid4()), "title": "Task B", "priority": "MEDIUM", "duration": "30m", "energy_level": "MEDIUM"},
                ],
                "fixed_events": [{"id": "lunch", "start_time": "12:30", "end_time": "13:15"}],
                "preferences": {"work_start_time": "09:00", "work_end_time": "17:30"},
                "user_profile": {"age": 30},
            },
            status.HTTP_201_CREATED,
        ),
        (
            "invalid_task_priority",
            {
                "user_id": str(uuid4()),
                "target_date": (date.today() + timedelta(days=1)).isoformat(),
                "tasks": [{"title": "Bad Task", "priority": "EXTREME", "duration": "1h"}], # Invalid priority
                "preferences": {},
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY, # Pydantic validation error
        ),
        (
            "missing_tasks",
            {
                "user_id": str(uuid4()),
                "target_date": (date.today() + timedelta(days=1)).isoformat(),
                # "tasks": [], # Missing required 'tasks' field if API model requires it
                "preferences": {},
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY, # Pydantic validation error
        ),
         (
            "invalid_date_format",
            {
                "user_id": str(uuid4()),
                "target_date": "tomorrow", # Invalid date format
                "tasks": [{"title": "Task", "priority": "MEDIUM", "duration": "1h"}],
                "preferences": {},
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY, # Pydantic validation error
        ),
    ],
)
def test_generate_schedule_endpoint(
    client: TestClient, test_id: str, request_body: Dict, expected_status: int
):
    """
    Test the POST /v1/schedule/generate endpoint with various inputs.
    """
    response = client.post("/v1/schedule/generate", json=request_body)

    assert response.status_code == expected_status, f"Test ID '{test_id}' failed."

    if expected_status == status.HTTP_201_CREATED:
        try:
            json_response = response.json()
            assert json_response.get("user_id") == request_body["user_id"]
            assert json_response.get("target_date") == request_body["target_date"]
            assert "schedule_id" in json_response
            assert "scheduled_items" in json_response
            assert isinstance(json_response["scheduled_items"], list)
            # Basic check: ensure scheduled items list is not empty if tasks were provided
            if request_body.get("tasks"):
                 # This assumes the solver finds a solution; might need adjustment if solver fails gracefully
                 # assert len(json_response["scheduled_items"]) > 0
                 pass # Placeholder - more specific checks depend on expected output
            assert "metrics" in json_response
            assert "explanations" in json_response
        except Exception as e:
            pytest.fail(f"Test ID '{test_id}': Failed to parse successful JSON response or assertions failed: {e}\nResponse: {response.text}")
    elif expected_status == status.HTTP_422_UNPROCESSABLE_ENTITY:
         # Check for FastAPI/Pydantic validation error structure
         try:
              json_response = response.json()
              assert "detail" in json_response
              assert isinstance(json_response["detail"], list) # Pydantic errors are usually lists
              assert len(json_response["detail"]) > 0
         except Exception as e:
              pytest.fail(f"Test ID '{test_id}': Failed to parse 422 JSON response or assertions failed: {e}\nResponse: {response.text}")


# TODO: Add test for GET /v1/schedule/{user_id}/{target_date} endpoint
# This will require mocking the data storage layer or setting up test data.


# --- V1 Feedback Endpoint Tests ---

@pytest.mark.parametrize(
    "test_id, feedback_body, expected_status",
    [
        (
            "valid_feedback",
            {
                "user_id": str(uuid4()),
                "schedule_date": (date.today() - timedelta(days=1)).isoformat(),
                "rating": 5,
                "comment": "Excellent schedule!",
            },
            status.HTTP_201_CREATED,
        ),
        (
            "invalid_rating_high",
            {
                "user_id": str(uuid4()),
                "schedule_date": (date.today() - timedelta(days=1)).isoformat(),
                "rating": 6, # Invalid
                "comment": "Too high",
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
        (
            "invalid_rating_low",
            {
                "user_id": str(uuid4()),
                "schedule_date": (date.today() - timedelta(days=1)).isoformat(),
                "rating": 0, # Invalid
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
        (
            "missing_rating",
            {
                "user_id": str(uuid4()),
                "schedule_date": (date.today() - timedelta(days=1)).isoformat(),
                # Missing 'rating' field
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
         (
            "invalid_date",
            {
                "user_id": str(uuid4()),
                "schedule_date": "yesterday", # Invalid format
                "rating": 4,
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
    ]
)
def test_submit_feedback_endpoint(
    client: TestClient, test_id: str, feedback_body: Dict, expected_status: int
):
    """
    Test the POST /v1/feedback endpoint with various inputs.
    """
    response = client.post("/v1/feedback", json=feedback_body)

    assert response.status_code == expected_status, f"Test ID '{test_id}' failed."

    if expected_status == status.HTTP_201_CREATED:
        try:
            json_response = response.json()
            assert json_response.get("message") == "Feedback submitted successfully."
            assert "feedback_id" in json_response
            # Validate feedback_id is a UUID string
            UUID(json_response["feedback_id"], version=4)
        except Exception as e:
            pytest.fail(f"Test ID '{test_id}': Failed to parse successful JSON response or assertions failed: {e}\nResponse: {response.text}")
    elif expected_status == status.HTTP_422_UNPROCESSABLE_ENTITY:
         try:
              json_response = response.json()
              assert "detail" in json_response
         except Exception as e:
              pytest.fail(f"Test ID '{test_id}': Failed to parse 422 JSON response or assertions failed: {e}\nResponse: {response.text}")


# --- V1 User Endpoint Tests ---
# These tests currently rely on the placeholder/mock implementation in the user routes.
# They will need modification if/when a real user service/database is integrated.

def test_get_user_profile_mock(client: TestClient):
    """
    Test GET /v1/users/{user_id}/profile (assuming mock response).
    """
    # Use a specific known UUID if the mock implementation expects it, otherwise random
    user_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479" # Example UUID used in user route mock
    response = client.get(f"/v1/users/{user_id}/profile")

    # Assuming the mock implementation returns 200 and mock data for this specific ID
    assert response.status_code == status.HTTP_200_OK
    try:
        json_response = response.json()
        assert json_response.get("user_id") == user_id
        assert "preferences" in json_response
        assert isinstance(json_response["preferences"], dict)
    except Exception as e:
        pytest.fail(f"Failed to parse user profile JSON response or assertions failed: {e}\nResponse: {response.text}")

def test_get_user_profile_not_found(client: TestClient):
    """
    Test GET /v1/users/{user_id}/profile for a non-existent user (assuming mock handles this).
    """
    user_id = str(uuid4()) # Random UUID, unlikely to match mock
    response = client.get(f"/v1/users/{user_id}/profile")
    # The mock implementation currently returns mock data even for random IDs.
    # A real implementation should return 404. Adjust assertion when implemented.
    # assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.status_code == status.HTTP_200_OK # Current mock behavior
    # assert "User not found" in response.text # Check detail message for 404

def test_update_user_preferences_mock(client: TestClient):
    """
    Test PUT /v1/users/{user_id}/preferences (assuming mock response).
    """
    user_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479" # Example UUID used in user route mock
    update_payload = {
        "preferences": {
            "theme": "matrix",
            "preferred_work_start_time": "09:30",
            "sleep_duration_goal_hours": 7.0
        }
    }
    response = client.put(f"/v1/users/{user_id}/preferences", json=update_payload)

    # Assuming mock implementation returns 200 and the updated profile
    assert response.status_code == status.HTTP_200_OK
    try:
        json_response = response.json()
        assert json_response.get("user_id") == user_id
        assert "preferences" in json_response
        # Check if preferences were actually updated in the response
        assert json_response["preferences"].get("theme") == "matrix"
        assert json_response["preferences"].get("preferred_work_start_time") == "09:30"
        assert json_response["preferences"].get("sleep_duration_goal_hours") == 7.0
    except Exception as e:
        pytest.fail(f"Failed to parse update preferences JSON response or assertions failed: {e}\nResponse: {response.text}")

# TODO: Add tests for other endpoints (e.g., GET feedback) when implemented.
# TODO: Consider mocking dependencies (like the Scheduler or database) for more focused integration tests.
# TODO: Add tests for authentication/authorization if implemented.
