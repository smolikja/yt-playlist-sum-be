from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator

class PlaylistRequest(BaseModel):
    url: HttpUrl

    @field_validator('url')
    def validate_youtube_url(cls, v):
        url_str = str(v)
        if "youtube.com" not in url_str and "youtu.be" not in url_str:
            raise ValueError('URL must be a valid YouTube URL')
        return v

class SummaryContent(BaseModel):
    playlist_title: Optional[str]
    video_count: int
    summary_markdown: str

class SummaryResult(SummaryContent):
    conversation_id: str

class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    summary_snippet: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    use_transcripts: bool = False

class ChatResponse(BaseModel):
    response: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationDetailResponse(BaseModel):
    id: str
    title: Optional[str]
    summary: str
    created_at: datetime
    messages: list[MessageResponse]

    class Config:
        from_attributes = True
