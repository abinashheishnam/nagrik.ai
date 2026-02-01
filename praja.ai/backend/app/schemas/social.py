from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class SocialIntakeRequest(BaseModel):
    url: HttpUrl
    note: Optional[str] = Field(default=None, max_length=500)
    location_hint: Optional[str] = Field(default=None, max_length=255)
    user_id: Optional[int] = Field(default=None)


class SocialIntakeResponse(BaseModel):
    complaint_id: int
    social_source_id: int
    platform: str
    status: str