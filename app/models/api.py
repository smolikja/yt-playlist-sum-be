"""
Pydantic models for API request/response schemas.
"""
from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from fastapi_users import schemas


class PlaylistRequest(BaseModel):
    """Request model for playlist summarization."""

    url: HttpUrl

    model_config = ConfigDict(extra="forbid")

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that the URL is a YouTube URL."""
        url_str = str(v)
        if "youtube.com" not in url_str and "youtu.be" not in url_str:
            raise ValueError("URL must be a valid YouTube URL")
        return v


class SummaryContent(BaseModel):
    """Content model for playlist summary."""

    playlist_title: Optional[str] = None
    video_count: int
    summary_markdown: str

    model_config = ConfigDict(frozen=True)


class SummaryResult(SummaryContent):
    """Result model for playlist summarization including conversation ID."""

    conversation_id: str

    model_config = ConfigDict(frozen=True)


class ConversationResponse(BaseModel):
    """Response model for conversation list items."""

    id: str
    title: Optional[str] = None
    summary_snippet: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ChatRequest(BaseModel):
    """Request model for chat messages."""

    conversation_id: str
    message: str = Field(..., min_length=1, max_length=10_000)
    use_rag: bool = True

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ChatResponse(BaseModel):
    """Response model for chat messages."""

    response: str

    model_config = ConfigDict(frozen=True)


class MessageResponse(BaseModel):
    """Response model for individual messages."""

    id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """Response model for conversation details including messages."""

    id: str
    title: Optional[str] = None
    playlist_url: Optional[str] = None
    summary: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = ConfigDict(from_attributes=True)


# FastAPI-Users schemas
class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    pass


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating users."""

    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating users."""

    pass


# =============================================================================
# JOB MODELS
# =============================================================================

class JobResponse(BaseModel):
    """Response model for job status."""

    id: uuid.UUID
    status: str
    playlist_url: str
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobClaimResponse(BaseModel):
    """Response when claiming a completed job."""

    conversation: ConversationDetailResponse

    model_config = ConfigDict(frozen=True)


class SummarizeResponse(BaseModel):
    """
    Union response for /summarize endpoint.
    
    For public users: mode="sync", summary is populated.
    For authenticated users: mode="async", job is populated.
    """

    mode: str  # "sync" or "async"
    job: Optional[JobResponse] = None
    summary: Optional[SummaryResult] = None

    model_config = ConfigDict(frozen=True)
