"""
SentenceTransformer implementation of EmbeddingProvider.

This module provides a local embedding solution using sentence-transformers,
avoiding external API dependencies for embeddings.
"""
import asyncio
from typing import ClassVar

from loguru import logger

from app.core.providers.embedding_provider import EmbeddingProvider


class SentenceTransformerEmbedding(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.
    
    This provider runs embeddings locally on CPU/GPU, making it:
    - Free (no API costs)
    - Fast for batch operations
    - Privacy-preserving (data doesn't leave your server)
    
    Default model: all-MiniLM-L6-v2 (384 dimensions, 80MB)
    
    Example:
        provider = SentenceTransformerEmbedding()
        embeddings = await provider.embed_texts(["Hello", "World"])
    """
    
    # Cache loaded models to avoid re-loading
    _models: ClassVar[dict] = {}
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the SentenceTransformer provider.
        
        Args:
            model_name: HuggingFace model name. Common options:
                - "all-MiniLM-L6-v2" (384d, fast, good quality)
                - "all-mpnet-base-v2" (768d, slower, better quality)
                - "paraphrase-multilingual-MiniLM-L12-v2" (384d, multilingual)
        """
        self.model_name = model_name
        
        # Lazy load to avoid import overhead when not used
        if model_name not in self._models:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model: {model_name}")
            self._models[model_name] = SentenceTransformer(model_name)
        
        self._model = self._models[model_name]
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.debug(f"SentenceTransformer initialized: {model_name} ({self._dimension}d)")
    
    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension
    
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Uses asyncio.to_thread to run CPU-bound embedding
        in a thread pool, avoiding blocking the event loop.
        """
        if not texts:
            return []
        
        logger.debug(f"Embedding {len(texts)} texts with {self.model_name}")
        
        # Run CPU-bound embedding in thread pool
        embeddings = await asyncio.to_thread(
            self._model.encode,
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        
        return embeddings.tolist()
