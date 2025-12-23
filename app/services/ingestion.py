"""
Ingestion service for processing transcripts into the vector store.

This module provides the IngestionService class that handles the complete
pipeline of chunking, embedding, and storing transcript data.
"""
from typing import Optional

from loguru import logger

from app.models import Playlist
from app.services.chunking import TranscriptChunker
from app.core.providers.embedding_provider import EmbeddingProvider
from app.core.providers.vector_store import VectorStore, DocumentChunk


class IngestionService:
    """
    Service for ingesting transcripts into the vector store.
    
    Handles the complete pipeline:
    1. Chunk transcripts using TranscriptChunker
    2. Generate embeddings in batches
    3. Store in vector database with namespace grouping
    
    Example:
        service = IngestionService(chunker, embedding_provider, vector_store)
        count = await service.ingest_playlist(playlist, namespace="playlist_123")
    """
    
    BATCH_SIZE = 32  # Embedding batch size for efficiency
    
    def __init__(
        self,
        chunker: TranscriptChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        """
        Initialize the ingestion service.
        
        Args:
            chunker: TranscriptChunker for splitting transcripts.
            embedding_provider: Provider for generating embeddings.
            vector_store: Vector database for storage.
        """
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
    
    async def ingest_playlist(
        self,
        playlist: Playlist,
        namespace: Optional[str] = None,
    ) -> int:
        """
        Ingest all video transcripts from a playlist into vector store.
        
        Args:
            playlist: The Playlist object with videos and transcripts.
            namespace: Optional namespace (defaults to playlist URL).
            
        Returns:
            Count of chunks indexed.
        """
        namespace = namespace or str(playlist.url)
        all_chunks: list[DocumentChunk] = []
        
        # 1. Generate chunks from all videos
        logger.info(f"Chunking transcripts for playlist: {playlist.title or namespace}")
        
        for video in playlist.videos:
            if not video.transcript:
                logger.debug(f"Skipping video {video.id} - no transcript")
                continue
            
            chunks = list(self.chunker.chunk_transcript(
                video_id=video.id,
                video_title=video.title or "Untitled",
                segments=video.transcript,
                playlist_id=namespace,
            ))
            all_chunks.extend(chunks)
            logger.debug(f"Video {video.id}: {len(chunks)} chunks")
        
        if not all_chunks:
            logger.warning(f"No chunks generated for playlist {namespace}")
            return 0
        
        logger.info(f"Generated {len(all_chunks)} total chunks")
        
        # 2. Generate embeddings in batches
        logger.info(f"Generating embeddings (batch size: {self.BATCH_SIZE})")
        embedded_chunks = await self._embed_chunks(all_chunks)
        
        # 3. Store in vector database
        logger.info(f"Storing {len(embedded_chunks)} chunks in vector store")
        count = await self.vector_store.upsert_documents(embedded_chunks, namespace)
        
        logger.info(f"Successfully indexed {count} chunks for playlist")
        return count
    
    async def delete_playlist(self, namespace: str) -> int:
        """
        Delete all indexed chunks for a playlist.
        
        Args:
            namespace: The playlist namespace (URL or ID).
            
        Returns:
            Count of chunks deleted.
        """
        return await self.vector_store.delete_by_namespace(namespace)
    
    async def _embed_chunks(
        self, 
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        """
        Generate embeddings for chunks in batches.
        
        Args:
            chunks: List of DocumentChunk objects without embeddings.
            
        Returns:
            List of DocumentChunk objects with embeddings.
        """
        embedded = []
        
        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i:i + self.BATCH_SIZE]
            texts = [c.content for c in batch]
            
            embeddings = await self.embedding_provider.embed_texts(texts)
            
            for chunk, embedding in zip(batch, embeddings):
                # Create new DocumentChunk with embedding (frozen model)
                embedded.append(DocumentChunk(
                    id=chunk.id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=embedding,
                ))
            
            logger.debug(f"Embedded batch {i // self.BATCH_SIZE + 1}")
        
        return embedded
