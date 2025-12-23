"""
Map-Reduce summarization service for transcript collections.

This module provides the SummarizationService class that uses an adaptive
approach to summarize videos: directly for single videos, or Map-Reduce
for multiple videos.
"""
from typing import Optional

from loguru import logger

from app.models import Playlist, Video, LLMRole
from app.core.providers.llm_provider import LLMProvider, LLMMessage


class SummarizationService:
    """
    Adaptive summarization for video transcripts.
    
    For single videos: Direct summarization (no Map-Reduce overhead)
    For playlists: Map-Reduce approach
    
    Map-Reduce phases:
    - Phase 1 (Map): Summarizes each video independently
    - Phase 2 (Reduce): Combines video summaries into a coherent global summary
    
    Example:
        service = SummarizationService(llm_provider)
        summary = await service.summarize_playlist(playlist)
    """
    
    MAX_TRANSCRIPT_CHARS = 16000  # ~4000 tokens safety limit per video
    
    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the summarization service.
        
        Args:
            llm_provider: LLM provider for text generation.
        """
        self.llm_provider = llm_provider
    
    async def summarize_playlist(self, playlist: Playlist) -> str:
        """
        Generate summary using adaptive approach based on video count.
        
        Single video: Direct summarization (faster, no overhead)
        Multiple videos: Map-Reduce approach
        
        Args:
            playlist: The Playlist object with videos and transcripts.
            
        Returns:
            The final summary as markdown text.
        """
        valid_videos = [v for v in playlist.videos if v.transcript]
        
        if not valid_videos:
            return "No transcripts available for summarization."
        
        video_count = len(valid_videos)
        is_single_video = video_count == 1
        
        if is_single_video:
            # Direct summarization for single video (skip Map-Reduce overhead)
            logger.info(f"Summarizing single video: {valid_videos[0].title or valid_videos[0].id}")
            return await self._summarize_single_video(valid_videos[0])
        
        # Map-Reduce for multiple videos
        # Phase 1: MAP - Summarize each video independently
        video_label = "video" if video_count == 1 else "videos"
        logger.info(f"Phase 1 (Map): Summarizing {video_count} {video_label}")
        video_summaries = []
        
        for i, video in enumerate(valid_videos, 1):
            logger.debug(f"Summarizing video {i}/{video_count}: {video.id}")
            summary = await self._summarize_video(video)
            video_summaries.append({
                "video_id": video.id,
                "title": video.title or "Untitled",
                "summary": summary,
            })
        
        logger.info(f"Phase 1 complete: {len(video_summaries)} video summaries generated")
        
        # Phase 2: REDUCE - Combine summaries into global view
        logger.info("Phase 2 (Reduce): Combining video summaries")
        final_summary = await self._reduce_summaries(
            playlist_title=playlist.title,
            video_summaries=video_summaries,
        )
        
        logger.info("Phase 2 complete: Global summary generated")
        return final_summary
    
    async def _summarize_single_video(self, video: Video) -> str:
        """
        Generate a comprehensive summary for a single video.
        
        Uses a specialized prompt for standalone video summarization
        (not part of a playlist context).
        
        Args:
            video: The Video object with transcript.
            
        Returns:
            Detailed summary with structure appropriate for single video.
        """
        transcript_text = video.full_text
        
        # Truncate if too long
        if len(transcript_text) > self.MAX_TRANSCRIPT_CHARS:
            logger.warning(f"Truncating transcript for video {video.id}")
            transcript_text = transcript_text[:self.MAX_TRANSCRIPT_CHARS] + "..."
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "You are an expert content summarizer. "
                    "Analyze this video transcript and provide a comprehensive summary. "
                    "Structure your response with:\n"
                    "1. Executive Summary (2-3 sentences)\n"
                    "2. Key Topics Covered\n"
                    "3. Main Points and Insights\n"
                    "4. Conclusions or Takeaways\n\n"
                    "The transcript may be in any language, but output in ENGLISH. "
                    "Use markdown formatting with headers and bullet points."
                ),
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
        Summarize a single video transcript (for Map phase).
        
        Args:
            video: The Video object with transcript.
            
        Returns:
            Summary text for the video.
        """
        transcript_text = video.full_text
        
        # Truncate if too long (safety measure)
        if len(transcript_text) > self.MAX_TRANSCRIPT_CHARS:
            logger.warning(f"Truncating transcript for video {video.id}")
            transcript_text = transcript_text[:self.MAX_TRANSCRIPT_CHARS] + "..."
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "You are an expert content summarizer. "
                    "Analyze the video transcript and provide a concise summary "
                    "capturing the main topics, key points, and conclusions. "
                    "The transcript may be in any language, but output in ENGLISH. "
                    "Use clear, structured prose. Keep the summary under 300 words."
                ),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=f"Video Title: {video.title or 'Untitled'}\n\nTranscript:\n{transcript_text}",
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.3,  # Lower for factual summarization
        )
        
        return response.content
    
    async def _reduce_summaries(
        self,
        playlist_title: Optional[str],
        video_summaries: list[dict],
    ) -> str:
        """
        Combine individual video summaries into a global summary.
        
        Args:
            playlist_title: Title of the playlist.
            video_summaries: List of dicts with video_id, title, summary.
            
        Returns:
            Combined global summary as markdown.
        """
        # Format video summaries for the prompt
        summaries_text = "\n\n".join([
            f"### {vs['title']}\n{vs['summary']}"
            for vs in video_summaries
        ])
        
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "You are synthesizing multiple video summaries into a cohesive "
                    "global summary of the entire playlist. "
                    "Identify overarching themes, common topics, and key takeaways. "
                    "Present the summary in well-structured English with clear sections. "
                    "Use markdown formatting with headers and bullet points. "
                    "Include an executive summary at the top."
                ),
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
            temperature=0.4,  # Slightly higher for creative synthesis
        )
        
        return response.content
