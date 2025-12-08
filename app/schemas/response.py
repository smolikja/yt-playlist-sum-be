from pydantic import BaseModel

class SummaryResponse(BaseModel):
    playlist_title: str
    video_count: int
    summary_markdown: str
