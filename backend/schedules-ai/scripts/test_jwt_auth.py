#!/usr/bin/env python3
"""
Script to test JWT authentication with the API.

This script generates a JWT token and tests the authenticated endpoints.
"""

import os
import sys
import json
import logging
import requests
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import the api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-for-development-only")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "auratyme-api")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "auratyme-auth")

# API Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
# For testing with nginx gateway, use:
# API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost/api/schedules-ai")


def create_jwt_token(user_id: str, username: str = None, expires_delta: timedelta = None) -> str:
    """Create a JWT token for testing."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=30)

    expires = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": user_id,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "aud": JWT_AUDIENCE,
        "iss": JWT_ISSUER,
    }
    if username:
        payload["username"] = username

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_authenticated_endpoints():
    """Test the authenticated endpoints."""
    # Generate a test user ID
    user_id = str(uuid4())

    # Create a JWT token
    try:
        token = create_jwt_token(user_id, username="test_user")
        logger.info(f"Created token for user {user_id}")
    except Exception as e:
        logger.exception(f"Error creating JWT token: {e}")
        return

    # Set up headers with the token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Test the authenticated endpoints
    endpoints = [
        "/v1/auth/schedules",
        "/v1/auth/latest-schedule",
    ]

    for endpoint in endpoints:
        url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Testing endpoint: {url}")

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                logger.info(f"Success! Status code: {response.status_code}")
                logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                logger.error(f"Error! Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.exception(f"Error testing endpoint {endpoint}: {e}")


def test_unauthenticated_access():
    """Test accessing authenticated endpoints without a token."""
    # Test the authenticated endpoints without a token
    endpoints = [
        "/v1/auth/schedules",
        "/v1/auth/latest-schedule",
    ]

    for endpoint in endpoints:
        url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Testing unauthenticated access to: {url}")

        try:
            response = requests.get(url)

            if response.status_code == 401 or response.status_code == 403:
                logger.info(f"Success! Unauthorized access blocked. Status code: {response.status_code}")
            else:
                logger.error(f"Error! Unauthorized access not blocked. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.exception(f"Error testing endpoint {endpoint}: {e}")


def test_public_endpoints():
    """Test the public endpoints."""
    # Test the public endpoints
    endpoints = [
        "/health",
        "/v1/apidog/schedules",
        "/v1/apidog/latest-schedule",
    ]

    for endpoint in endpoints:
        url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Testing public endpoint: {url}")

        try:
            response = requests.get(url)

            if response.status_code == 200:
                logger.info(f"Success! Status code: {response.status_code}")
                if endpoint != "/health":  # Skip logging health check response
                    logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                logger.error(f"Error! Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.exception(f"Error testing endpoint {endpoint}: {e}")


def main():
    """Run the tests."""
    logger.info("Starting JWT authentication tests...")

    # Test public endpoints
    logger.info("\n=== Testing Public Endpoints ===")
    test_public_endpoints()

    # Test unauthenticated access
    logger.info("\n=== Testing Unauthenticated Access ===")
    test_unauthenticated_access()

    # Test authenticated endpoints
    logger.info("\n=== Testing Authenticated Endpoints ===")
    test_authenticated_endpoints()

    logger.info("JWT authentication tests completed.")


if __name__ == "__main__":
    main()
