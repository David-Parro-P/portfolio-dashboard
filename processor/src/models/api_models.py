from pydantic import BaseModel, Field
from typing import Optional


class HealthResponse(BaseModel):
    status: str = Field("healthy", const=True)
    service: str = Field("ibkr-processor", const=True)


class StatementRequest(BaseModel):
    csv_content: str
    subject: str
    filename: Optional[str] = None


class StatementResponse(BaseModel):
    status: str
    message: str
    error: Optional[str] = None
