"""
Chunking strategies for YouTube transcripts.

This module provides the TranscriptChunker class that splits video transcripts
into smaller chunks while preserving timestamp metadata for precise citation.
"""
from typing import Generator

from app.models import TranscriptSegment
from app.core.providers.vector_store import DocumentChunk
from app.core.constants import RAGConfig


class TranscriptChunker:
    """
    Chunking strategy for YouTube transcripts with timestamp preservation.
    
    Uses a recursive character splitter approach where:
    - Each chunk targets ~chunk_size characters
    - Chunks overlap by chunk_overlap characters for context continuity
    - Timestamps are preserved from the first and last segments in each chunk
    
    Example:
        chunker = TranscriptChunker(chunk_size=1000, chunk_overlap=200)
        chunks = list(chunker.chunk_transcript(
            video_id="abc123",
            video_title="My Video",
            segments=transcript_segments,
            playlist_id="playlist_456",
        ))
    """
    
    def __init__(
        self,
        chunk_size: int = RAGConfig.CHUNK_SIZE,      # ~250 tokens
        chunk_overlap: int = RAGConfig.CHUNK_OVERLAP,    # ~50 tokens overlap
        min_chunk_size: int = RAGConfig.MIN_CHUNK_SIZE,
    ):
        """
        Initialize the chunker with size parameters.
        
        Args:
            chunk_size: Target characters per chunk (default 1000).
            chunk_overlap: Overlap between consecutive chunks (default 200).
            min_chunk_size: Minimum chunk size to yield (default 100).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_transcript(
        self,
        video_id: str,
        video_title: str,
        segments: list[TranscriptSegment],
        playlist_id: str,
    ) -> Generator[DocumentChunk, None, None]:
        """
        Split transcript segments into chunks while preserving timestamps.
        
        Each chunk contains:
        - content: The text
        - metadata:
          - video_id: The YouTube video ID
          - video_title: Title for display
          - playlist_id: Namespace for the playlist
          - start_time: Timestamp of first segment (seconds)
          - end_time: Timestamp of last segment (seconds)
          - chunk_index: Sequential index within the video
          
        Args:
            video_id: YouTube video ID.
            video_title: Title of the video.
            segments: List of TranscriptSegment objects.
            playlist_id: The playlist ID for namespace grouping.
            
        Yields:
            DocumentChunk objects for each chunk.
        """
        if not segments:
            return
        
        current_text = ""
        current_start = segments[0].start
        current_end = segments[0].start
        chunk_index = 0
        
        for segment in segments:
            segment_text = segment.text.strip()
            if not segment_text:
                continue
            
            potential_text = f"{current_text} {segment_text}".strip()
            
            # If adding this segment would exceed chunk_size and we have enough text
            if len(potential_text) > self.chunk_size and len(current_text) >= self.min_chunk_size:
                # Yield current chunk
                yield DocumentChunk(
                    id=f"{video_id}_{chunk_index}",
                    content=current_text,
                    metadata={
                        "video_id": video_id,
                        "video_title": video_title,
                        "playlist_id": playlist_id,
                        "start_time": current_start,
                        "end_time": current_end,
                        "chunk_index": chunk_index,
                    }
                )
                
                chunk_index += 1
                
                # Start new chunk with overlap from previous text
                overlap_text = self._get_overlap(current_text)
                current_text = f"{overlap_text} {segment_text}".strip()
                current_start = segment.start
            else:
                current_text = potential_text
            
            # Update end time to include this segment
            current_end = segment.start + segment.duration
        
        # Yield final chunk if it meets minimum size
        if len(current_text) >= self.min_chunk_size:
            yield DocumentChunk(
                id=f"{video_id}_{chunk_index}",
                content=current_text,
                metadata={
                    "video_id": video_id,
                    "video_title": video_title,
                    "playlist_id": playlist_id,
                    "start_time": current_start,
                    "end_time": current_end,
                    "chunk_index": chunk_index,
                }
            )
    
    def _get_overlap(self, text: str) -> str:
        """
        Get the last chunk_overlap characters from text for continuity.
        
        Args:
            text: The text to extract overlap from.
            
        Returns:
            The trailing overlap portion of the text.
        """
        if len(text) <= self.chunk_overlap:
            return text
        return text[-self.chunk_overlap:]
