from fastapi import APIRouter
from app.schemas.request import PlaylistRequest
from app.schemas.response import SummaryResponse

router = APIRouter()

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_playlist(request: PlaylistRequest):
    # Mock data for now
    return SummaryResponse(
        playlist_title="Mock Playlist Title",
        video_count=10,
        summary_markdown="## Mock Summary\n\nThis is a dummy summary of the playlist."
    )

