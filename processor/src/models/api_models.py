from pydantic import BaseModel
from typing import Optional, Literal

class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    service: Literal["ibkr-processor"] = "ibkr-processor"


class StatementRequest(BaseModel):
    csv_content: str
    subject: str
    filename: Optional[str] = None


class StatementResponse(BaseModel):
    status: str
    message: str
    error: Optional[str] = None