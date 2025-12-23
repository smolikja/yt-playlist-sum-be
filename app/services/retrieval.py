"""
RAG retrieval service for context-aware chat.

This module provides the RetrievalService class that handles query
transformation and similarity search for the RAG chat pipeline.
"""
from typing import Optional

from loguru import logger

from app.core.providers.llm_provider import LLMProvider, LLMMessage
from app.core.providers.embedding_provider import EmbeddingProvider
from app.core.providers.vector_store import VectorStore, SearchResult


class RetrievalService:
    """
    Service for RAG-based retrieval and query processing.
    
    Provides:
    1. Query transformation: Convert context-dependent questions to standalone
    2. Similarity search: Find relevant transcript chunks
    3. Context formatting: Prepare retrieved content for LLM prompt
    
    Example:
        service = RetrievalService(llm, embedding, vector_store)
        
        # Transform "What did he say about that?" → "What did John say about AI?"
        standalone = await service.transform_query(user_query, chat_history)
        
        # Retrieve relevant chunks
        results = await service.retrieve_context(standalone, namespace)
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        """
        Initialize the retrieval service.
        
        Args:
            llm_provider: LLM for query transformation.
            embedding_provider: Provider for query embedding.
            vector_store: Vector database for similarity search.
        """
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
    
    async def transform_query(
        self,
        user_query: str,
        chat_history: list[dict],
    ) -> str:
        """
        Transform a context-dependent query into a standalone question.
        
        This is crucial for RAG because similarity search needs a complete
        question, not one that depends on chat history context.
        
        Examples:
        - "What else?" → "What other topics were discussed in the video?"
        - "Tell me more about that" → "Tell me more about machine learning"
        
        Args:
            user_query: The user's latest question.
            chat_history: List of dicts with 'role' and 'content' keys.
            
        Returns:
            A standalone version of the query.
        """
        # If no history, the query is already standalone
        if not chat_history:
            return user_query
        
        # Format recent history
        history_text = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in chat_history[-5:]  # Last 5 messages for context
        ])
        
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "Given the conversation history and the user's latest question, "
                    "rewrite the question to be standalone and self-contained. "
                    "Do NOT answer the question, just reformulate it. "
                    "If the question references 'that', 'it', 'this', etc., replace "
                    "with the actual subject from history. "
                    "If the question is already standalone, return it unchanged."
                ),
            ),
            LLMMessage(
                role="user",
                content=f"Conversation History:\n{history_text}\n\nLatest Question: {user_query}",
            ),
        ]
        
        response = await self.llm_provider.generate_text(
            messages=messages,
            temperature=0.1,  # Very low for deterministic transformation
            max_tokens=256,
        )
        
        transformed = response.content.strip()
        
        if transformed != user_query:
            logger.debug(f"Query transformed: '{user_query}' → '{transformed}'")
        
        return transformed
    
    async def retrieve_context(
        self,
        query: str,
        namespace: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: The query string (preferably standalone).
            namespace: The playlist namespace to search within.
            top_k: Maximum number of results to return.
            
        Returns:
            List of SearchResult objects with chunks and scores.
        """
        logger.debug(f"Retrieving context for query: '{query[:50]}...'")
        
        # Generate query embedding
        query_embedding = await self.embedding_provider.embed_text(query)
        
        # Search vector store
        results = await self.vector_store.search_similarity(
            query_embedding=query_embedding,
            top_k=top_k,
            namespace=namespace,
        )
        
        logger.debug(f"Retrieved {len(results)} chunks")
        return results
    
    def format_context(self, results: list[SearchResult]) -> str:
        """
        Format retrieved chunks into a context string for the LLM prompt.
        
        Includes video title and timestamp for each chunk.
        
        Args:
            results: List of SearchResult objects.
            
        Returns:
            Formatted context string with timestamps.
        """
        if not results:
            return ""
        
        parts = []
        for r in results:
            meta = r.chunk.metadata
            video_title = meta.get("video_title", "Video")
            start_time = meta.get("start_time", 0)
            
            timestamp = self._format_timestamp(start_time)
            parts.append(f"[{video_title} @ {timestamp}]\n{r.chunk.content}")
        
        return "\n\n---\n\n".join(parts)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds to MM:SS or HH:MM:SS.
        
        Args:
            seconds: Time in seconds.
            
        Returns:
            Formatted timestamp string.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
