from fastapi import APIRouter, HTTPException, status, Depends
from app.models import PlaylistRequest, SummaryResult
from app.services.youtube import YouTubeService
from app.services.llm import LLMService
from app.api.dependencies import get_youtube_service, get_llm_service
from loguru import logger
import time

router = APIRouter()

@router.post("/summarize", response_model=SummaryResult)
async def summarize_playlist(
    request: PlaylistRequest,
    yt_service: YouTubeService = Depends(get_youtube_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    logger.info(f"Incoming request for URL: {request.url}")
    try:
        # 1. Extract Playlist Info (Video IDs, Titles)
        logger.info(f"Extracting playlist info from: {request.url}")
        start_time = time.perf_counter()
        playlist = yt_service.extract_playlist_info(str(request.url))
        duration = time.perf_counter() - start_time
        logger.info(f"Playlist extraction completed in {duration:.2f}s")
        
        if not playlist.videos:
            logger.warning(f"No videos found for URL: {request.url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No videos found in the provided playlist URL."
            )
            
        logger.info(f"Found {len(playlist.videos)} videos.")

        # 2. Fetch Transcripts
        logger.info("Fetching transcripts...")
        start_time = time.perf_counter()
        playlist = await yt_service.fetch_transcripts(playlist)
        duration = time.perf_counter() - start_time
        logger.info(f"Transcript fetching completed in {duration:.2f}s")
        
        # Check if we actually got any usable text
        valid_videos = [v for v in playlist.videos if v.transcript]
        if not valid_videos:
             logger.warning("No valid transcripts found.")
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Could not retrieve transcripts for any videos in the playlist."
            )

        # 3. Generate Summary with Gemini
        logger.info("Generating summary with Gemini...")
        start_time = time.perf_counter()
        summary_result = await llm_service.generate_summary(playlist)
        duration = time.perf_counter() - start_time
        logger.info(f"Summary generation completed in {duration:.2f}s")

        # 4. Return Response
        logger.info("Request processed successfully (HTTP 200).")
        return summary_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing playlist summarization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while processing the playlist."
        )