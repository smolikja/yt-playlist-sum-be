import asyncio
from typing import List, Dict, Any, Optional
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.services.proxy import ProxyService

# Limit concurrent requests to avoid overwhelming proxies or YouTube
CONCURRENCY_LIMIT = 5

def extract_video_ids(playlist_url: str) -> List[str]:
    """
    Extracts video IDs from a YouTube playlist URL using yt-dlp.
    Uses 'extract_flat=True' for performance.
    """
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(playlist_url, download=False)
            
            if 'entries' not in info_dict:
                # Could be a single video URL provided instead of playlist
                if 'id' in info_dict:
                    return [info_dict['id']]
                return []

            video_ids = []
            for entry in info_dict['entries']:
                if entry and 'id' in entry:
                    video_ids.append(entry['id'])
            
            return video_ids
        except Exception as e:
            logger.error(f"Error extracting video IDs: {e}")
            return []

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def _fetch_single_transcript(video_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
    """
    Fetches a single transcript with retries and semaphore rate limiting.
    """
    async with semaphore:
        try:
            # Offload blocking call to thread
            def fetch_sync():
                proxies = ProxyService.get_proxies()
                if proxies:
                    proxy_conf = GenericProxyConfig(
                        http_url=proxies.get("http"), 
                        https_url=proxies.get("https")
                    )
                else:
                    proxy_conf = None
                
                return YouTubeTranscriptApi(proxy_config=proxy_conf).fetch(video_id, languages=['en'])

            transcript = await asyncio.to_thread(fetch_sync)
            logger.info(f"Successfully fetched transcript for {video_id}")
            return {
                "video_id": video_id,
                "transcript": transcript
            }
        except (TranscriptsDisabled, NoTranscriptFound):
            logger.warning(f"No transcript found/disabled for video {video_id}")
            return None # Do not retry these expected errors
        except Exception as e:
            logger.warning(f"Error fetching transcript for {video_id} (retrying): {e}")
            raise e # Trigger retry

async def fetch_transcripts(video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches transcripts for a list of video IDs concurrently with retries.
    """
    logger.info(f"Starting concurrent transcript fetch for {len(video_ids)} videos")
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [_fetch_single_transcript(vid, semaphore) for vid in video_ids]
    
    # Run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = []
    for vid, res in zip(video_ids, results):
        if isinstance(res, Exception):
            logger.error(f"Failed to fetch transcript for {vid} after retries: {res}")
        elif res:
            valid_results.append(res)
            
    logger.info(f"Finished fetching transcripts. Success: {len(valid_results)}/{len(video_ids)}")
    return valid_results
