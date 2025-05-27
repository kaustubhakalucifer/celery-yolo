from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.app.database import JobStatus


class JobBase(BaseModel):
    image_name: str
    original_image_path: str


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    job_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_taken_ms: Optional[int] = None
    objects_found: Optional[str] = None  # This is going to be a JSON string
    processed_image_path: Optional[str] = None
    status: Optional[str] = None


class JobSchema(JobBase):
    id: int
    job_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_taken_ms: Optional[int] = None
    objects_found: Optional[str] = None  # JSON string for transport
    processed_image_path: Optional[str] = None
    status: JobStatus
    created_at: datetime

class Config:
    from_attributes = True