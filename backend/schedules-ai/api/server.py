# === File: schedules-ai/api/server.py ===

"""
Main FastAPI application server for the Auratyme schedules-ai.

Initializes the FastAPI application, configures middleware (CORS, logging),
includes API routers for different versions and functionalities (health, v1),
and manages the dependency injection of core services required by the API endpoints.
It also defines application startup and shutdown logic using FastAPI's lifespan manager.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health
from api.routes.v1 import feedback as feedback_v1
from api.routes.v1 import schedule as schedule_v1
from api.routes.v1 import user as user_v1
from api.routes.v1 import apidog as apidog_v1
from api.routes.v1 import auth as auth_v1

# --- Logging Configuration ---
# Basic configuration. For production, consider using dictConfig with a YAML/JSON file.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Configuration Loading (Placeholder) ---
# TODO: Replace this placeholder with a robust configuration loading mechanism,
#       preferably using Pydantic's BaseSettings to load from environment
#       variables and/or .env files.
def load_app_config() -> Dict[str, Any]:
    """
    Loads application configuration (placeholder implementation).

    In a real application, this would load settings from environment variables,
    configuration files (e.g., YAML), or a configuration service.

    Returns:
        Dict[str, Any]: A dictionary containing application configuration.
    """
    logger.info("Loading application configuration (using placeholder defaults)...")
    return {
        "app_name": "Auratyme Schedules API",
        "cors_origins": [
            "http://localhost",
            "http://localhost:8080",
            "http://localhost:3000",
        ],
        "llm": {
            "provider": "openrouter",
            "model_name": "mistralai/mixtral-8x7b-instruct",
            "site_url": "https://auratyme.com",
            "site_name": "Auratyme",
        },
        "solver": {
            "time_limit": 20.0,
        },
        "rag": {},
        "device_adapter": {},
        "sleep": {},
        "chronotype": {},
        "prioritizer_weights": {},
        "wearables": {},
        "analytics": {},
        "adaptive": {},
        "feedback_storage": {},
        "feedback_nlp": {},
        "scheduler": {},
    }


app_config = load_app_config()


# --- Dependency Provider Functions ---
# These functions are now imported from api.dependencies to avoid circular imports
import api.dependencies


# --- FastAPI Application Lifecycle (Startup/Shutdown) ---


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown events.

    Use this context manager to initialize resources like database connections,
    machine learning models, or background task schedulers on startup,
    and clean them up gracefully on shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control is yielded back to FastAPI to run the application.
    """
    # --- Startup ---
    logger.info(f"Starting up {app_config.get('app_name', 'Scheduler Core API')}...")
    disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"
    if disable_db:
        logger.info("Database connection disabled by environment variable.")
    else:
        from api.db import init_db_pool, create_tables, close_db_pool
        try:
            await init_db_pool()
            await create_tables()
            logger.info("Database connection established and tables created.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("API will run without database support.")

    logger.info("Application startup complete.")

    yield

    # --- Shutdown ---
    logger.info(f"Shutting down {app_config.get('app_name', 'Scheduler Core API')}...")
    disable_db = os.environ.get("DISABLE_DB", "false").lower() == "true"
    if not disable_db:
        try:
            from api.db import close_db_pool
            await close_db_pool()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    logger.info("Application shutdown complete.")


# --- FastAPI App Initialization ---

app = FastAPI(
    title=app_config.get("app_name", "EffectiveDayAI Scheduler Core API"),
    description="API for generating personalized schedules, managing user data, and processing feedback.",
    version="0.1.0",  # Consider reading from pyproject.toml or config
    lifespan=lifespan,
)

# --- Middleware Configuration ---

if os.environ.get("ENABLE_JWT_AUTH", "false").lower() == "true":
    from api.middleware.jwt_auth import JWTAuthMiddleware
    app.add_middleware(JWTAuthMiddleware)
    logger.info("JWT authentication middleware enabled.")
else:
    logger.info("JWT authentication middleware disabled.")

origins = app_config.get("cors_origins", [])
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS middleware enabled for origins: {origins}")
else:
    logger.warning("CORS middleware not enabled (no origins configured).")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Logs incoming request details and outgoing response status."""
    logger.info(f"Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code} for {request.method} {request.url.path}")
        return response
    except Exception as e:
        logger.error(
            f"Unhandled exception during request: {request.method} {request.url.path}",
            exc_info=True,
        )
        raise e


# --- API Routers ---

app.include_router(health.router, prefix="/health", tags=["Health"])

api_v1_prefix = "/v1"
app.include_router(
    user_v1.router, prefix=f"{api_v1_prefix}/users", tags=["V1 - Users"]
)
app.include_router(
    schedule_v1.router, prefix=f"{api_v1_prefix}/schedule", tags=["V1 - Schedule"]
)
app.include_router(
    feedback_v1.router, prefix=f"{api_v1_prefix}/feedback", tags=["V1 - Feedback"]
)
app.include_router(
    apidog_v1.router, prefix=f"{api_v1_prefix}/apidog", tags=["V1 - APIdog"]
)
app.include_router(
    auth_v1.router, prefix=f"{api_v1_prefix}/auth", tags=["V1 - Auth"]
)

logger.info("API routers included (Health, V1 Users, V1 Schedule, V1 Feedback, V1 APIdog, V1 Auth).")


# --- Root Endpoint ---
@app.get("/", summary="API Root", tags=["Root"], include_in_schema=True)
async def read_root() -> Dict[str, str]:
    """
    Provides basic information about the API.

    Useful as a quick check to see if the API is running.
    """
    return {
        "message": f"Welcome to the {app.title}",
        "version": app.version,
        "docs_url": app.docs_url or "/docs",
    }


# --- Development Server Execution ---

if __name__ == "__main__":
    import uvicorn

    logger.warning(
        "Running server directly via __main__. "
        "Recommended: `uvicorn schedules_ai.api.server:app --reload --host 0.0.0.0 --port 8000`"
    )
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
