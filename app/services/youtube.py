import asyncio
import random
import logging
from typing import List, Dict, Any
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

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

async def fetch_transcripts(video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches transcripts for a list of video IDs asynchronously (conceptually),
    but sequentially with delays to avoid IP blocking.
    """
    results = []
    
    for video_id in video_ids:
        try:
            # Offload the blocking API call to a separate thread to avoid blocking the asyncio event loop
            transcript = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript, video_id, languages=['en']
            )
            results.append({
                "video_id": video_id,
                "transcript": transcript
            })
            logger.info(f"Successfully fetched transcript for {video_id}")

        except (TranscriptsDisabled, NoTranscriptFound):
            logger.warning(f"No transcript found/disabled for video {video_id}")
        except Exception as e:
            logger.error(f"Error fetching transcript for {video_id}: {e}")
        
        # Anti-blocking strategy: Random delay between requests
        delay = random.uniform(0.5, 2.0)
        await asyncio.sleep(delay)

    return results
