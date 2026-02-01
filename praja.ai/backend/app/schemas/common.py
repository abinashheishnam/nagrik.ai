from pydantic import BaseModel, Field


class StatusUpdateIn(BaseModel):
    status: str = Field(..., min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=2000)
