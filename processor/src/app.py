from flask import Flask, request, jsonify
from pathlib import Path
from processor import process_statement
from pathlib import Path
from models.api_models import (
    StatementRequest,
    StatementResponse,
)

app = Flask(__name__)

from pathlib import Path


import tempfile
from contextlib import contextmanager
from datetime import datetime
from typing import Generator
from pydantic import ValidationError


@contextmanager
def temp_csv_file(content: str, date_str: str) -> Generator[Path, None, None]:
    with tempfile.NamedTemporaryFile(
        suffix=f".{date_str}.csv", mode="w", encoding="utf-8", delete=False
    ) as tmp_file:
        try:
            tmp_file.write(content.replace("\ufeff", ""))
            tmp_file.flush()
            yield Path(tmp_file.name)
        finally:
            Path(tmp_file.name).unlink(missing_ok=True)


@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    # TODO anadir a modelo e pydantic
    return jsonify({"status": "healthy", "service": "ibkr-processor"}), 200


import logging
import uuid
from typing import Tuple, Any

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


def parse_date_from_subject(subject: str) -> str:
    try:
        date_str = subject.split(" ")[-1].strip()
        parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
        return parsed_date.strftime("%Y%m%d")

    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse date from subject: {subject}")
        raise ValueError(
            f"Invalid date format in subject. Expected MM/DD/YYYY, got: {subject}"
        ) from e


def handle_statement_processing(data: StatementRequest) -> Tuple[dict, int]:
    request_id = str(uuid.uuid4())
    logger.info(f"Processing statement request {request_id}")
    try:
        # Your processing logic here
        return (
            StatementResponse(
                status="success", message="Statement processed successfully"
            ).dict(),
            200,
        )
    except ValueError as ve:
        logger.error(f"Validation error for request {request_id}: {str(ve)}")
        return (
            StatementResponse(
                status="error", message="Validation error", error=str(ve)
            ).dict(),
            400,
        )
    except Exception as e:
        logger.error(f"Unexpected error for request {request_id}: {str(e)}")
        return (
            StatementResponse(
                status="error", message="Internal server error", error=str(e)
            ).dict(),
            500,
        )


@app.route("/process-statement", methods=["POST"])
def process_ib_statement():
    """Process IB statement from CSV content"""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    try:
        data = StatementRequest(**request.get_json())
        date_str = parse_date_from_subject(data.subject)

        with temp_csv_file(data.csv_content, date_str) as tmp_file_path:
            logger.info(f"Processing file: {tmp_file_path}")
            processor = process_statement(tmp_file_path.as_posix())
            return handle_statement_processing(data)

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
