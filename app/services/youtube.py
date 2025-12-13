import asyncio
from typing import List, Optional, Union
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.services.proxy import ProxyService
from app.models import Playlist, Video, TranscriptSegment, YtDlpResponse
from app.models.sql import VideoModel
from app.repositories.video import VideoRepository

# Limit concurrent requests to avoid overwhelming proxies or YouTube
CONCURRENCY_LIMIT = 5

class YouTubeService:
    """
    Service for interacting with YouTube to extract playlist information and fetch video transcripts.
    
    This service handles:
    1. Extracting video metadata from a playlist URL using yt-dlp.
    2. Fetching transcripts for videos using youtube-transcript-api.
    3. Caching transcripts in the database to minimize external API calls.
    """
    def __init__(self, proxy_service: ProxyService, video_repository: VideoRepository):
        """
        Initializes the YouTubeService.

        Args:
            proxy_service (ProxyService): Service to manage proxy rotation.
            video_repository (VideoRepository): Repository for database access to cached videos.
        """
        self.proxy_service = proxy_service
        self.repo = video_repository

    def extract_playlist_info(self, playlist_url: str) -> Playlist:
        """
        Extracts video IDs and basic info from a YouTube playlist URL using yt-dlp.

        Args:
            playlist_url (str): The URL of the YouTube playlist.

        Returns:
            Playlist: A Playlist model containing the playlist title, URL, and a list of Video objects
                      (initially without transcripts).
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
                                title=entry.title,
                                description=entry.description
                            ))
                elif yt_data.id:
                    # Could be a single video URL provided instead of playlist
                    videos.append(Video(
                        id=yt_data.id,
                        title=yt_data.title,
                        description=getattr(yt_data, 'description', None)
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
        Fetches a single transcript from YouTube with retries and concurrency limiting.
        Prioritizes Manual subtitles (any lang) > Automatic captions (any lang).

        Args:
            video (Video): The Video object to fetch the transcript for.
            semaphore (asyncio.Semaphore): Semaphore to limit concurrent requests.

        Returns:
            Video: The updated Video object with the fetched transcript (if successful).
                   If fetching fails or no transcript is found, the video.transcript will be empty
                   and transcript_missing may be set to True.

        Raises:
            Exception: Retries on general exceptions up to the configured limit.
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
                    
                    # List all available transcripts
                    transcript_list = YouTubeTranscriptApi(proxy_config=proxy_conf).list(video.id)
                    
                    # Priority 1: Manual Subtitles (Any Language)
                    # iterate and find first manual
                    for t in transcript_list:
                        if not t.is_generated:
                            logger.info(f"Video {video.id}: Using Manual transcript in '{t.language}'")
                            return t.fetch(), t.language

                    # Priority 2: Automatic Captions (Any Language)
                    for t in transcript_list:
                        if t.is_generated:
                            logger.info(f"Video {video.id}: Using Automatic transcript in '{t.language}'")
                            return t.fetch(), t.language

                    return None, None

                raw_transcript, lang = await asyncio.to_thread(fetch_sync)
                
                if raw_transcript:
                    segments = [
                        TranscriptSegment(
                            text=item.text,
                            start=item.start,
                            duration=item.duration
                        ) for item in raw_transcript
                    ]
                    
                    video.transcript = segments
                    video.language = lang
                    logger.info(f"Successfully fetched transcript for {video.id}")
                else:
                    # Should be caught by NoTranscriptFound usually, but just in case
                    raise NoTranscriptFound(video.id)

                return video

            except (TranscriptsDisabled, NoTranscriptFound):
                logger.warning(f"No transcript found/disabled for video {video.id}. Falling back to description.")
                video.transcript_missing = True
                # Description should be already populated from extract_playlist_info
                return video 
            except Exception as e:
                logger.warning(f"Error fetching transcript for {video.id} (retrying): {e}")
                raise e # Trigger retry

    async def fetch_transcripts(self, playlist: Playlist) -> Playlist:
        """
        Fetches transcripts for all videos in the playlist.

        This method employs a caching strategy:
        1. Checks the database for existing transcripts for the video IDs.
        2. Identifies which videos are missing from the cache.
        3. Fetches missing transcripts concurrently from YouTube.
        4. Saves the newly fetched transcripts to the database.
        5. Returns the playlist with a combination of cached and fetched videos.

        Args:
            playlist (Playlist): The playlist containing videos to process.

        Returns:
            Playlist: The updated Playlist object with video transcripts populated where available.
        """
        all_video_ids = [v.id for v in playlist.videos]
        logger.info(f"Processing {len(all_video_ids)} videos for playlist {playlist.id or playlist.url}")

        # 1. Check DB for existing videos
        existing_sql_videos = await self.repo.get_existing_videos(all_video_ids)
        existing_map = {}
        for sql_vid in existing_sql_videos:
            try:
                # DB stores JSONB, so sql_vid.transcript is already a list of dicts
                transcript_data = sql_vid.transcript if sql_vid.transcript else []
                segments = [TranscriptSegment(**item) for item in transcript_data]
                
                existing_map[sql_vid.id] = Video(
                    id=sql_vid.id,
                    title=sql_vid.title,
                    transcript=segments,
                    language=sql_vid.language,
                    # If empty transcript in DB, it might be a previous failure or just empty.
                    # We flag it as missing if empty, so we might fallback to description (from original video obj)
                    transcript_missing=(len(segments) == 0)
                )
            except Exception as e:
                logger.error(f"Failed to parse transcript for video {sql_vid.id}: {e}")
                # Treat as missing if parsing fails
        
        logger.info(f"Found {len(existing_map)} videos in cache")

        # 2. Identify missing videos
        # We consider a video 'missing' only if it's not in the DB at all.
        # If it's in DB but has empty transcript, we respect the DB (it implies we tried and failed before).
        # To retry failed ones, we'd need a different logic (e.g. check created_at or status).
        missing_videos = [v for v in playlist.videos if v.id not in existing_map]
        
        # 3. Fetch missing videos
        final_fetched_videos: List[Video] = []
        fetched_videos_to_save: List[VideoModel] = []

        if missing_videos:
            logger.info(f"Fetching {len(missing_videos)} missing transcripts from YouTube")
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
            tasks = [self._fetch_single_transcript(vid, semaphore) for vid in missing_videos]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    logger.error(f"Failed to fetch transcript for {missing_videos[i].id} after retries: {res}")
                    # Keep the original video object (without transcript)
                    final_fetched_videos.append(missing_videos[i])
                elif isinstance(res, Video):
                    final_fetched_videos.append(res)
                    # We save to DB if we got a transcript OR if we confirmed it's missing (empty list)
                    # to avoid refetching next time.
                    try:
                        transcript_list = [seg.model_dump() for seg in res.transcript]
                        fetched_videos_to_save.append(VideoModel(
                            id=res.id,
                            title=res.title,
                            transcript=transcript_list,
                            language=res.language or 'en'
                        ))
                    except Exception as e:
                        logger.error(f"Failed to prepare transcript for DB save {res.id}: {e}")

            # 4. Save new videos to DB
            if fetched_videos_to_save:
                logger.info(f"Saving {len(fetched_videos_to_save)} new videos to database")
                await self.repo.save_videos(fetched_videos_to_save)
        
        # 5. Combine results and handle descriptions
        combined_videos = []
        fetched_map = {v.id: v for v in final_fetched_videos}
        
        for vid in playlist.videos:
            final_vid = None
            
            if vid.id in existing_map:
                final_vid = existing_map[vid.id]
            elif vid.id in fetched_map:
                final_vid = fetched_map[vid.id]
            else:
                final_vid = vid

            # Ensure description is populated (DB doesn't store it, so take from original 'vid')
            if not final_vid.description and vid.description:
                final_vid.description = vid.description
                
            combined_videos.append(final_vid)

        playlist.videos = combined_videos
        
        # Success count: transcript exists OR (transcript missing AND description exists)
        success_count = sum(1 for v in playlist.videos if v.transcript or (v.transcript_missing and v.description))
        logger.info(f"Finished processing. Usable Content: {success_count}/{len(playlist.videos)}")
        
        return playlist
