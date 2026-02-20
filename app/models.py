"""
Pydantic Models — API Request/Response data structures.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Orientation(str, Enum):
    portrait = "portrait"    # 9:16
    landscape = "landscape"  # 16:9
    square = "square"        # 1:1


class VideoSize(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    downloading = "downloading"


# === Request Models ===

class GenerateRequest(BaseModel):
    """Video generation request"""
    prompt: str = Field(..., min_length=3, max_length=2000, description="Video description prompt")
    orientation: Orientation = Field(default=Orientation.landscape, description="Video orientation")
    size: VideoSize = Field(default=VideoSize.small, description="Video size")


# === Response Models ===

class GenerateResponse(BaseModel):
    """Response when video generation starts"""
    task_id: str
    status: str = "queued"
    message: str = "Video generation started"


class StatusResponse(BaseModel):
    """Video generation status"""
    task_id: str
    status: TaskStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    message: str = ""
    video_url: Optional[str] = None
    download_url: Optional[str] = None


class HealthResponse(BaseModel):
    """Server health check"""
    status: str = "ok"
    chrome_connected: bool = False
    session_valid: bool = False
