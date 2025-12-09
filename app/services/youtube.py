import asyncio
from typing import List, Optional, Union
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.services.proxy import ProxyService
from app.models import Playlist, Video, TranscriptSegment, YtDlpResponse

# Limit concurrent requests to avoid overwhelming proxies or YouTube
CONCURRENCY_LIMIT = 5

class YouTubeService:
    def __init__(self, proxy_service: ProxyService):
        self.proxy_service = proxy_service

    def extract_playlist_info(self, playlist_url: str) -> Playlist:
        """
        Extracts video IDs and basic info from a YouTube playlist URL using yt-dlp.
        Returns a Playlist model with a list of Video objects (initially without transcripts).
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
                
                # Parse raw dict into Pydantic model immediately for type safety
                yt_data = YtDlpResponse(**info_dict)
                
                videos: List[Video] = []
                
                if yt_data.entries:
                    for entry in yt_data.entries:
                        # YtDlpEntry ensures id is present
                        if entry.id:
                            videos.append(Video(
                                id=entry.id,
                                title=entry.title
                            ))
                elif yt_data.id:
                    # Could be a single video URL provided instead of playlist
                    videos.append(Video(
                        id=yt_data.id,
                        title=yt_data.title
                    ))
                
                return Playlist(
                    url=playlist_url,
                    title=yt_data.title,
                    videos=videos
                )

            except Exception as e:
                logger.error(f"Error extracting video IDs: {e}")
                return Playlist(url=playlist_url, videos=[])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _fetch_single_transcript(self, video: Video, semaphore: asyncio.Semaphore) -> Video:
        """
        Fetches a single transcript with retries and semaphore rate limiting.
        Updates the Video object with the transcript.
        """
        async with semaphore:
            try:
                # Offload blocking call to thread
                def fetch_sync():
                    proxies = self.proxy_service.get_proxies()
                    proxy_conf = None
                    if proxies:
                         proxy_conf = GenericProxyConfig(
                            http_url=proxies.http, 
                            https_url=proxies.https
                        )
                    
                    return YouTubeTranscriptApi(proxy_config=proxy_conf).fetch(video.id, languages=['en'])

                raw_transcript = await asyncio.to_thread(fetch_sync)
                
                segments = [
                    TranscriptSegment(
                        text=item.text,
                        start=item.start,
                        duration=item.duration
                    ) for item in raw_transcript
                ]
                
                video.transcript = segments
                logger.info(f"Successfully fetched transcript for {video.id}")
                return video

            except (TranscriptsDisabled, NoTranscriptFound):
                logger.warning(f"No transcript found/disabled for video {video.id}")
                return video # Return video with empty transcript
            except Exception as e:
                logger.warning(f"Error fetching transcript for {video.id} (retrying): {e}")
                raise e # Trigger retry

    async def fetch_transcripts(self, playlist: Playlist) -> Playlist:
        """
        Fetches transcripts for all videos in the playlist concurrently with retries.
        Returns the updated Playlist object.
        """
        logger.info(f"Starting concurrent transcript fetch for {len(playlist.videos)} videos")
        
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        # Pass self to the method
        tasks = [self._fetch_single_transcript(vid, semaphore) for vid in playlist.videos]
        
        # Run all tasks concurrently
        # return_exceptions=True allows us to see which ones failed (and were retried until failure)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        updated_videos = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Failed to fetch transcript for {playlist.videos[i].id} after retries: {res}")
                # We keep the video without transcript
                updated_videos.append(playlist.videos[i])
            elif isinstance(res, Video):
                updated_videos.append(res)
                
        playlist.videos = updated_videos
        success_count = sum(1 for v in playlist.videos if v.transcript)
        logger.info(f"Finished fetching transcripts. Success: {success_count}/{len(playlist.videos)}")
        
        return playlist