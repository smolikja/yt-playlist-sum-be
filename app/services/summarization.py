"""
Map-Reduce and Direct summarization service for transcript collections.

This module provides the SummarizationService class that uses an adaptive
approach to summarize videos. It dynamically selects the optimal strategy
based on content length:

1. Single Video: Specialized comprehensive prompt.
2. Direct Strategy (Batch): Sends all transcripts in one prompt if they fit context window.
3. Map-Reduce Strategy: Splits processing for massive collections. It processes chunks of 
   videos (batches) in parallel to optimize efficiency before combining them.
"""
from typing import Optional

from loguru import logger

from app.models import Playlist, Video, LLMRole
from app.core.providers.llm_provider import LLMProvider, LLMMessage
from app.core.prompts import SummarizationPrompts


class SummarizationService:
    """
    Adaptive summarization for video transcripts using optimized LLM strategies.
    
    Strategies:
    - **Single Video**: Direct comprehensive summarization.
    - **Direct (Batch)**: Optimized for modern large-context models (e.g., Gemini 1.5). 
      Sends all data in one request to minimize costs and maximize context awareness.
    - **Chunked Map-Reduce**: Fallback for massive datasets. Groups videos into chunks 
      (batches) that fit the context window, summarizes each chunk, then combines the results.
    
    Attributes:
        MAX_SINGLE_VIDEO_CHARS: Limit for a single video transcript (~500k tokens).
        MAX_BATCH_CONTEXT_CHARS: Limit for direct batch processing (~750k tokens).
        MAP_CHUNK_SIZE_CHARS: Limit for a single Map phase batch (~500k tokens).
    """
    
    # Approx. 500k tokens (assuming ~4 chars/token)
    MAX_SINGLE_VIDEO_CHARS = 2_000_000 
    
    # Approx. 750k tokens - leaves buffer for response in a 1M context window
    MAX_BATCH_CONTEXT_CHARS = 3_000_000 
    
    # Approx. 500k tokens - limit for one chunk in Map-Reduce phase
    MAP_CHUNK_SIZE_CHARS = 2_000_000

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the summarization service.
        
        Args:
            llm_provider: LLM provider for text generation.
        """
        self.llm_provider = llm_provider
    
    async def summarize_playlist(self, playlist: Playlist) -> str:
        """
        Generate summary using adaptive approach based on content volume.
        
        Args:
            playlist: The Playlist object with videos and transcripts.
            
        Returns:
            The final summary as markdown text.
        """
        valid_videos = [v for v in playlist.videos if v.transcript]
        
        if not valid_videos:
            return "No transcripts available for summarization."
        
        video_count = len(valid_videos)
        
        # Strategy 1: Single Video (Specialized Prompt)
        if video_count == 1:
            logger.info(f"Summarizing single video: {valid_videos[0].title or valid_videos[0].id}")
            return await self._summarize_single_video(valid_videos[0])

        # Calculate total characters to decide strategy
        total_chars = sum(len(v.full_text) for v in valid_videos)
        logger.info(f"Total transcript volume: {total_chars} chars across {video_count} videos")

        # Strategy 2: Direct Batch Processing (Optimized for Large Context)
        if total_chars < self.MAX_BATCH_CONTEXT_CHARS:
            logger.info("Using Direct Batch strategy (fits in context window)")
            return await self._summarize_playlist_direct(playlist, valid_videos)

        # Strategy 3: Chunked Map-Reduce (Fallback for Massive Data)
        logger.info("Using Chunked Map-Reduce strategy (exceeds batch limit)")
        return await self._summarize_playlist_map_reduce(playlist, valid_videos)

    async def _summarize_playlist_direct(self, playlist: Playlist, videos: list[Video]) -> str:
        """
        Summarize all videos in a single LLM call (Direct Strategy).
        """
        # Build a structured context string
        context_parts = []
        for video in videos:
            title = video.title or "Untitled"
            text = video.full_text
            
            # Individual video truncation safety
            if len(text) > self.MAX_SINGLE_VIDEO_CHARS:
                text = text[:self.MAX_SINGLE_VIDEO_CHARS] + "... (truncated)"
            
            context_parts.append(f"### Video: {title}\n{text}")
            
        full_context = "\n\n".join(context_parts)
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=SummarizationPrompts.DIRECT_BATCH,
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=(
                    f"Playlist Title: {playlist.title or 'Untitled Playlist'}\n"
                    f"Video Count: {len(videos)}\n\n"
                    f"--- BEGIN TRANSCRIPTS ---\n\n{full_context}\n\n--- END TRANSCRIPTS ---"
                ),
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.4, # Balanced for creativity and accuracy
        )
        
        return response.content

    async def _summarize_playlist_map_reduce(self, playlist: Playlist, videos: list[Video]) -> str:
        """
        Summarize videos using Chunked Map-Reduce.
        
        Phase 1 (Map): Group videos into chunks (batches) and summarize each chunk.
        Phase 2 (Reduce): Combine chunk summaries.
        """
        # Create chunks
        chunks = self._chunk_videos(videos)
        logger.info(f"Phase 1 (Map): Processing {len(chunks)} chunks for {len(videos)} videos")
        
        chunk_summaries = []
        
        # In a real async scenario, we could use asyncio.gather here for parallel processing.
        # For simplicity and to avoid rate limits, we process sequentially or semi-sequentially.
        for i, chunk_videos in enumerate(chunks, 1):
            chunk_label = f"Part {i}/{len(chunks)}"
            logger.debug(f"Map phase: Summarizing {chunk_label} ({len(chunk_videos)} videos)")
            
            summary = await self._summarize_batch(chunk_videos)
            
            chunk_summaries.append({
                "title": chunk_label,
                "summary": summary,
            })
        
        # Phase 2: REDUCE
        logger.info("Phase 2 (Reduce): Combining chunk summaries")
        return await self._reduce_summaries(
            playlist_title=playlist.title,
            video_summaries=chunk_summaries,
        )

    def _chunk_videos(self, videos: list[Video]) -> list[list[Video]]:
        """
        Group videos into chunks that fit within the map phase context limit.
        """
        chunks = []
        current_chunk = []
        current_chunk_size = 0
        
        for video in videos:
            video_len = len(video.full_text)
            
            # If adding this video exceeds limit and current chunk is not empty, start new chunk
            if current_chunk and (current_chunk_size + video_len > self.MAP_CHUNK_SIZE_CHARS):
                chunks.append(current_chunk)
                current_chunk = []
                current_chunk_size = 0
            
            current_chunk.append(video)
            current_chunk_size += video_len
            
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    async def _summarize_batch(self, videos: list[Video]) -> str:
        """
        Summarize a batch of videos (Map phase unit).
        """
        # Build context for this batch
        context_parts = []
        for video in videos:
            title = video.title or "Untitled"
            text = video.full_text
            # Safety truncate individual videos just in case
            if len(text) > self.MAX_SINGLE_VIDEO_CHARS:
                text = text[:self.MAX_SINGLE_VIDEO_CHARS] + "... (truncated)"
            context_parts.append(f"### Video: {title}\n{text}")
            
        batch_context = "\n\n".join(context_parts)
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=SummarizationPrompts.MAP_PHASE,
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=f"Videos Segment:\n\n{batch_context}",
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.3, 
        )
        
        return response.content

    async def _summarize_single_video(self, video: Video) -> str:
        """
        Generate a comprehensive summary for a single video.
        """
        transcript_text = video.full_text
        
        if len(transcript_text) > self.MAX_SINGLE_VIDEO_CHARS:
            logger.warning(f"Truncating transcript for video {video.id}")
            transcript_text = transcript_text[:self.MAX_SINGLE_VIDEO_CHARS] + "..."
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=SummarizationPrompts.SINGLE_VIDEO,
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=f"Video Title: {video.title or 'Untitled'}\n\nTranscript:\n{transcript_text}",
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.3,
        )
        
        return response.content
    
    async def _summarize_video(self, video: Video) -> str:
        """
        Summarize a single video transcript (for Map phase of Map-Reduce).
        """
        transcript_text = video.full_text
        
        if len(transcript_text) > self.MAX_SINGLE_VIDEO_CHARS:
            logger.warning(f"Truncating transcript for video {video.id}")
            transcript_text = transcript_text[:self.MAX_SINGLE_VIDEO_CHARS] + "..."
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=SummarizationPrompts.MAP_PHASE,
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=f"Video Title: {video.title or 'Untitled'}\n\nTranscript:\n{transcript_text}",
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.3,
        )
        
        return response.content
    
    async def _reduce_summaries(
        self,
        playlist_title: Optional[str],
        video_summaries: list[dict],
    ) -> str:
        """
        Combine summaries (from individual videos or batches) into a global summary.
        """
        summaries_text = "\n\n".join([
            f"### {vs['title']}\n{vs['summary']}"
            for vs in video_summaries
        ])
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=SummarizationPrompts.REDUCE_PHASE,
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=(
                    f"Playlist: {playlist_title or 'Untitled Playlist'}\n"
                    f"Number of Videos: {len(video_summaries)}\n\n"
                    f"Individual Video Summaries:\n\n{summaries_text}"
                ),
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.4,
        )
        
        return response.content
