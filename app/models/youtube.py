from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field, ConfigDict

# --- Internal Parsing Models (yt-dlp) ---

class YtDlpEntry(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    
    model_config = ConfigDict(extra='ignore')

class YtDlpResponse(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    entries: Optional[List[YtDlpEntry]] = None
    
    model_config = ConfigDict(extra='ignore')

# --- Core Data Models ---

class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float

class Video(BaseModel):
    id: str
    title: Optional[str] = None
    transcript: List[TranscriptSegment] = Field(default_factory=list)
    
    @property
    def full_text(self) -> str:
        """Concatenates all transcript segments into a single string."""
        return " ".join(seg.text.strip() for seg in self.transcript if seg.text)

class Playlist(BaseModel):
    id: Optional[str] = None
    url: HttpUrl
    title: Optional[str] = None
    videos: List[Video] = Field(default_factory=list)
