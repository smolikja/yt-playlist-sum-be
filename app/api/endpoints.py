from fastapi import APIRouter, HTTPException, status
from app.schemas.request import PlaylistRequest
from app.schemas.response import SummaryResponse
from app.services import youtube, processor, llm
from loguru import logger
import time

router = APIRouter()

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_playlist(request: PlaylistRequest):
    logger.info(f"Incoming request for URL: {request.url}")
    try:
        # 1. Extract Video IDs
        logger.info(f"Extracting video IDs from: {request.url}")
        start_time = time.perf_counter()
        video_ids = youtube.extract_video_ids(str(request.url))
        duration = time.perf_counter() - start_time
        logger.info(f"Video ID extraction completed in {duration:.2f}s")
        
        if not video_ids:
            logger.warning(f"No videos found for URL: {request.url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No videos found in the provided playlist URL."
            )
            
        logger.info(f"Found {len(video_ids)} videos.")

        # 2. Fetch Transcripts
        logger.info("Fetching transcripts...")
        start_time = time.perf_counter()
        transcripts_data = await youtube.fetch_transcripts(video_ids)
        duration = time.perf_counter() - start_time
        logger.info(f"Transcript fetching completed in {duration:.2f}s")
        
        # Check if we actually got any usable text
        valid_transcripts = [t for t in transcripts_data if t.get("transcript")]
        if not valid_transcripts:
             logger.warning("No valid transcripts found.")
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Could not retrieve transcripts for any videos in the playlist."
            )

        # 3. Process Data for LLM
        logger.info("Processing transcript context...")
        context_text = processor.prepare_transcript_context(transcripts_data)
        logger.info(f"Context size: {len(context_text)} characters")

        # 4. Generate Summary with Gemini
        logger.info("Generating summary with Gemini...")
        start_time = time.perf_counter()
        summary_md = await llm.generate_playlist_summary(context_text)
        duration = time.perf_counter() - start_time
        logger.info(f"Summary generation completed in {duration:.2f}s")

        # 5. Return Response
        logger.info("Request processed successfully (HTTP 200).")
        return SummaryResponse(
            playlist_title="Summarized Playlist", # Note: yt-dlp 'extract_flat' might not give title easily without an extra call, keeping generic or could improve later
            video_count=len(video_ids),
            summary_markdown=summary_md
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing playlist summarization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while processing the playlist."
        )

