"""
Pydantic models for YouTube data structures.
"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# --- Internal Parsing Models (yt-dlp) ---


class YtDlpEntry(BaseModel):
    """Model for individual video entries from yt-dlp response."""

    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class YtDlpResponse(BaseModel):
    """Model for yt-dlp playlist/video response."""

    id: Optional[str] = None
    title: Optional[str] = None
    entries: Optional[List[YtDlpEntry]] = None

    model_config = ConfigDict(extra="ignore")


# --- Core Data Models ---


class TranscriptSegment(BaseModel):
    """Model for a single transcript segment."""

    text: str
    start: float
    duration: float

    model_config = ConfigDict(frozen=True)


class Video(BaseModel):
    """Model for a YouTube video with optional transcript."""

    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    transcript: List[TranscriptSegment] = Field(default_factory=list)
    status: "VideoStatus" = Field(default_factory=lambda: VideoStatus.SUCCESS)
    status_detail: Optional[str] = None  # Detailed error message if failed
    language: Optional[str] = None

    @property
    def is_usable(self) -> bool:
        """Check if video has usable content for summarization."""
        from app.models.enums import VideoStatus
        if self.status == VideoStatus.SUCCESS:
            return True
        if self.status == VideoStatus.FALLBACK_DESCRIPTION:
            return bool(self.description and len(self.description) > 50)
        return False

    @property
    def transcript_missing(self) -> bool:
        """Backward compatibility - True if no transcript available."""
        from app.models.enums import VideoStatus
        return self.status != VideoStatus.SUCCESS

    @property
    def full_text(self) -> str:
        """Concatenate all transcript segments into a single string."""
        if self.transcript:
            return " ".join(seg.text.strip() for seg in self.transcript if seg.text)
        return self.description or ""


# Import for forward reference
from app.models.enums import VideoStatus


class Playlist(BaseModel):
    """Model for a YouTube playlist with videos."""

    id: Optional[str] = None
    url: HttpUrl
    title: Optional[str] = None
    videos: List[Video] = Field(default_factory=list)
