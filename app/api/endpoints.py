from fastapi import APIRouter, HTTPException, status
from app.schemas.request import PlaylistRequest
from app.schemas.response import SummaryResponse
from app.services import youtube, processor, llm
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_playlist(request: PlaylistRequest):
    try:
        # 1. Extract Video IDs
        logger.info(f"Extracting video IDs from: {request.url}")
        video_ids = youtube.extract_video_ids(str(request.url))
        
        if not video_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No videos found in the provided playlist URL."
            )
            
        logger.info(f"Found {len(video_ids)} videos.")

        # 2. Fetch Transcripts
        logger.info("Fetching transcripts...")
        transcripts_data = await youtube.fetch_transcripts(video_ids)
        
        # Check if we actually got any usable text
        valid_transcripts = [t for t in transcripts_data if t.get("transcript")]
        if not valid_transcripts:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Could not retrieve transcripts for any videos in the playlist."
            )

        # 3. Process Data for LLM
        logger.info("Processing transcript context...")
        context_text = processor.prepare_transcript_context(transcripts_data)

        # 4. Generate Summary with Gemini
        logger.info("Generating summary with Gemini...")
        summary_md = await llm.generate_playlist_summary(context_text)

        # 5. Return Response
        return SummaryResponse(
            playlist_title="Summarized Playlist", # Note: yt-dlp 'extract_flat' might not give title easily without an extra call, keeping generic or could improve later
            video_count=len(video_ids),
            summary_markdown=summary_md
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing playlist summarization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while processing the playlist."
        )

