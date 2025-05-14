# === File: schedules-ai/api/middleware/__init__.py ===

"""
Middleware package for the Scheduler Core API.

This package contains custom FastAPI middleware used for various purposes
such as authentication, logging, request/response processing, etc.
"""

from api.middleware.jwt_auth import JWTAuthMiddleware, JWTBearer, create_jwt_token

__all__ = ["JWTAuthMiddleware", "JWTBearer", "create_jwt_token"]
