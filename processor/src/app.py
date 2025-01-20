from flask import Flask, request, jsonify, g
from pathlib import Path
from processor import process_statement
from models.api_models import StatementRequest, StatementResponse, HealthResponse
from typing import Dict, Tuple, Any, Generator
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic_settings import BaseSettings

import tempfile
from contextlib import contextmanager
from datetime import datetime
from pydantic import ValidationError
import logging
import uuid
import signal
import atexit


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    SERVICE_NAME: str = "ibkr-processor"
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_DAY: str = "200 per day"
    RATE_LIMIT_HOUR: str = "50 per hour"

    class Config:
        env_file = ".env"


settings = Settings()
app = Flask(__name__)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DAY, settings.RATE_LIMIT_HOUR],
)

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s",
        level=getattr(logging, settings.LOG_LEVEL),
    )


def create_error_response(message: str, status_code: int) -> Tuple[Dict[str, Any], int]:
    """Create standardized error response"""
    return (
        jsonify(
            {
                "error": message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(g, "request_id", str(uuid.uuid4())),
            }
        ),
        status_code,
    )


@contextmanager
def temp_csv_file(content: str, date_str: str) -> Generator[Path, None, None]:
    """Create temporary CSV file and cleanup after use"""
    with tempfile.NamedTemporaryFile(
        suffix=f".{date_str}.csv", mode="w", encoding="utf-8", delete=False
    ) as tmp_file:
        try:
            tmp_file.write(content.replace("\ufeff", ""))
            tmp_file.flush()
            yield Path(tmp_file.name)
        finally:
            Path(tmp_file.name).unlink(missing_ok=True)


def check_dependencies() -> bool:
    """Check if all critical dependencies are healthy"""
    try:
        # Add checks for critical dependencies (database, external services, etc.)
        return True
    except Exception as e:
        logger.error(f"Dependency check failed: {str(e)}")
        return False


def parse_date_from_subject(subject: str) -> str:
    """Parse date from email subject"""
    try:
        date_str = subject.split(" ")[-1].strip()
        parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
        return parsed_date.strftime("%Y%m%d")

    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse date from subject: {subject}")
        raise ValueError(
            f"Invalid date format in subject. Expected MM/DD/YYYY, got: {subject}"
        ) from e


def handle_statement_processing(
    data: StatementRequest, result: Any
) -> Tuple[dict, int]:
    """Process statement and handle any errors"""
    request_id = getattr(g, "request_id", str(uuid.uuid4()))
    logger.info(f"Processing statement request {request_id}")
    try:
        return (
            StatementResponse(
                status="success",
                message="Statement processed successfully",
                data=result,
            ).model_dump(),
            200,
        )
    except ValueError as ve:
        logger.error(f"Validation error for request {request_id}: {str(ve)}")
        return (
            StatementResponse(
                status="error", message="Validation error", error=str(ve)
            ).model_dump(),
            400,
        )
    except Exception as e:
        logger.error(f"Unexpected error for request {request_id}: {str(e)}")
        return (
            StatementResponse(
                status="error", message="Internal server error", error=str(e)
            ).model_dump(),
            500,
        )


def validate_json_request(f):
    """Decorator to validate JSON requests"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return create_error_response("Content-Type must be application/json", 400)
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def before_request():
    """Set request ID for tracking"""
    g.request_id = str(uuid.uuid4())
    logger.info("Processing request")


@app.route("/health", methods=["GET"])
def health_check() -> Tuple[Dict[str, Any], int]:
    """
    Health check endpoint that returns service status

    Returns:
        Tuple[Dict[str, Any], int]: JSON response with health status and HTTP code
    """
    dependencies_healthy = check_dependencies()
    response = HealthResponse(
        status="healthy" if dependencies_healthy else "degraded",
        service=settings.SERVICE_NAME,
        timestamp=datetime.utcnow(),
        checks={"dependencies": "healthy" if dependencies_healthy else "failing"},
    )
    return jsonify(response.model_dump()), 200 if dependencies_healthy else 503


@app.route("/process-statement", methods=["POST"])
@validate_json_request
@limiter.limit(settings.RATE_LIMIT_HOUR)
def process_ib_statement():
    """Process IB statement from CSV content"""
    try:
        data = StatementRequest(**request.get_json())
        date_str = parse_date_from_subject(data.subject)

        with temp_csv_file(data.csv_content, date_str) as tmp_file_path:
            logger.info(f"Processing file: {tmp_file_path}")
            result = process_statement(tmp_file_path.as_posix())
            return handle_statement_processing(data, result)

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return create_error_response(str(e), 400)


def shutdown_handler(signum, frame):
    """Handle graceful shutdown"""
    logger.info("Received shutdown signal, cleaning up...")
    exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
atexit.register(lambda: logger.info("Application shutting down"))


if __name__ == "__main__":
    setup_logging()
    logger.info(f"Starting {settings.SERVICE_NAME} on {settings.HOST}:{settings.PORT}")
    app.run(host=settings.HOST, port=settings.PORT)
