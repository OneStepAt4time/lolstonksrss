"""
Structured logging configuration with structlog.

This module provides structured JSON logging with request ID tracing for the
LoL Stonks RSS application. It supports both JSON (production) and plain text
(development) output formats.

Features:
- JSON structured logs for production
- Request ID tracing via middleware
- Context-aware logging
- Module-level log level configuration
- Docker JSON driver compatibility
"""

import logging
import sys
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, cast

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# Context variable for request ID (context-local storage)
_request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def configure_structlog(
    json_logging: bool = True,
    log_level: str = "INFO",
) -> None:
    """
    Configure structlog for JSON or console output.

    This function must be called once at application startup to configure
    the structlog logging system. It sets up processors, formatters, and
    configures standard library logging to integrate with structlog.

    Args:
        json_logging: If True, output JSON logs. If False, use plain text.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        >>> configure_structlog(json_logging=True, log_level="INFO")
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started", extra={"version": "1.0.0"})
    """
    # Configure standard library logging to forward to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Shared processors for both JSON and console output
    shared_processors: list[Callable[[Any, str, dict[str, Any]], Any]] = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add the logger name
        structlog.stdlib.add_logger_name,
        # Perform %-style formatting
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Add timestamp in ISO 8601 format
        structlog.processors.TimeStamper(fmt="iso"),
        # If the "stack_info" key in the event dict is set to True,
        # remove it and render the current stack trace.
        structlog.processors.StackInfoRenderer(),
        # If the "exc_info" key in the event dict is either True or a
        # sys.exc_info() tuple, remove it and render the exception.
        structlog.processors.UnicodeDecoder(),
        # Add request ID if available in context
        _add_request_id_from_context,
        # Add call site info (module, function, line number)
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # Final processor chain
    processors = shared_processors + [
        # Format exceptions (if any)
        structlog.processors.format_exc_info,
    ]

    # Add renderer based on logging mode
    if json_logging:
        # JSON renderer for production (Docker-friendly)
        # Each log line is a complete JSON object
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console renderer for development (human-readable)
        # Uses colors and indentation for better readability
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_request_id_from_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add request ID from context variable to log event.

    This processor checks if a request ID has been set in the current context
    and adds it to the log event dictionary.

    Args:
        logger: The logger instance
        method_name: The logging method name (info, debug, etc.)
        event_dict: The event dictionary to modify

    Returns:
        The modified event dictionary with request_id added if available

    Example:
        >>> event_dict = {"event": "User logged in"}
        >>> _add_request_id_from_context(None, "info", event_dict)
        {'event': 'User logged in', 'request_id': 'abc-123-def'}
    """
    request_id = _request_id_ctx_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def get_logger(name: str) -> Any:
    """
    Get a structured logger with the specified name.

    This is the preferred way to get a logger in the application.
    The logger is bound with the module name for context.

    Args:
        name: The logger name, typically __name__ from the calling module

    Returns:
        A bound structlog instance with module context

    Example:
        >>> from src.utils.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing article", article_id="12345")
    """
    return cast(Any, structlog.get_logger(name))


def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Creates a UUID4-based request ID for tracing requests through the system.

    Returns:
        A unique request ID string (UUID without dashes)

    Example:
        >>> generate_request_id()
        'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
    """
    return uuid.uuid4().hex


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request ID tracking.

    This middleware:
    1. Extracts X-Request-ID from incoming headers if present
    2. Generates a new request ID if not present
    3. Binds the request ID to the current context for logging
    4. Returns the request ID in the response headers

    Usage:
        >>> app.add_middleware(RequestIdMiddleware)

    Example:
        >>> # Incoming request with X-Request-ID header
        >>> GET /feed.xml
        >>> X-Request-ID: abc-123
        >>>
        >>> # Logs will include: {"request_id": "abc-123", ...}
        >>> # Response will include: X-Request-ID: abc-123
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            header_name: The header name to use for request ID (default: X-Request-ID)
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process the request and add request ID tracking.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response with X-Request-ID header added

        Example:
            >>> # Incoming: GET /feed.xml (no X-Request-ID header)
            >>> # Generated: X-Request-ID: a1b2c3d4...
            >>> # Logs include: {"request_id": "a1b2c3d4...", ...}
            >>> # Response includes: X-Request-ID: a1b2c3d4...
        """
        # Extract request ID from headers or generate new one
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = generate_request_id()

        # Set request ID in context for logging
        _request_id_ctx_var.set(request_id)

        # Log the incoming request
        logger = get_logger(__name__)
        logger.info(
            "Incoming request",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        try:
            # Process the request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers[self.header_name] = request_id

            return response

        except Exception as e:
            # Log the exception
            logger.exception(
                "Request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error_type": type(e).__name__,
                },
            )
            # Return JSON error response
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "request_id": request_id},
            )

        finally:
            # Clean up context
            _request_id_ctx_var.set(None)


def get_request_id() -> str | None:
    """
    Get the current request ID from context.

    This function can be used to retrieve the current request ID
    from anywhere in the application, not just in log handlers.

    Returns:
        The current request ID, or None if not in a request context

    Example:
        >>> request_id = get_request_id()
        >>> if request_id:
        ...     print(f"Processing request: {request_id}")
    """
    return _request_id_ctx_var.get()


# Type aliases for convenience
BoundLogger = structlog.stdlib.BoundLogger
