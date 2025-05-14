# === File: schedules-ai/api/middleware/logging.py ===

"""
Detailed HTTP Request/Response Logging Middleware for FastAPI.

Provides a middleware class that logs detailed information about incoming
requests and outgoing responses, including processing time, client details,
and filtered headers.
"""

import logging
import time
from typing import Set, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# --- Constants ---
DEFAULT_HEADERS_TO_IGNORE: Set[str] = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "x-api-key",
}

logger = logging.getLogger(__name__)


# --- Middleware Class ---

class DetailedLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to log detailed request and response information."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        headers_to_ignore: Optional[Set[str]] = None,
    ) -> None:
        super().__init__(app)
        self.headers_to_ignore = (
            headers_to_ignore
            if headers_to_ignore is not None
            else DEFAULT_HEADERS_TO_IGNORE
        )
        self.headers_to_ignore = {h.lower() for h in self.headers_to_ignore}
        logger.info(
            f"DetailedLoggingMiddleware initialized. Ignoring headers: {self.headers_to_ignore}"
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Processes a single request/response cycle, adding logging."""
        start_time = time.perf_counter()

        # --- Log Request Details ---
        client_host = request.client.host if request.client else "unknown"
        filtered_headers = {
            h: v
            for h, v in request.headers.items()
            if h.lower() not in self.headers_to_ignore
        }

        request_log_details = {
            "client_host": client_host,
            "method": request.method,
            "url_path": request.url.path,
            "query_params": str(request.query_params),
            "headers": filtered_headers,
        }

        logger.info("Incoming request", extra={"request": request_log_details})

        # --- Process Request ---
        response: Optional[Response] = None
        status_code: int = 500
        process_time_ms: float = -1.0

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            process_time_ms = round(process_time * 1000, 2)
            status_code = response.status_code

        except Exception as e:
            process_time = time.perf_counter() - start_time
            process_time_ms = round(process_time * 1000, 2)
            logger.error(
                f"Unhandled exception during request processing: {type(e).__name__}",
                exc_info=True,
                extra={
                    "request": request_log_details,
                    "processing_time_ms": process_time_ms,
                },
            )
            raise e
        finally:
            # --- Log Response Details ---
            response_log_details = {
                "status_code": status_code,
                "processing_time_ms": process_time_ms,
            }
            full_log_extra = {
                "request": request_log_details,
                "response": response_log_details,
            }
            log_level = logging.INFO if 200 <= status_code < 400 else logging.WARNING if 400 <= status_code < 500 else logging.ERROR
            logger.log(log_level, "Request processing complete", extra=full_log_extra)

        # TODO: Consider implementing request/response body logging if needed

        if response is None:
             logger.error("Middleware finished without a response object after an error.")
             return Response(status_code=500, content="Internal Server Error")

        return response


# TODO: Add this middleware to the FastAPI application in server.py if needed
