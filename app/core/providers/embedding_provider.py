"""
Abstract base class for embedding providers.

This module defines a vendor-neutral interface for generating
text embeddings. Concrete implementations (SentenceTransformer, OpenAI)
must implement this interface.
"""
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.
    
    Implementations must provide:
    - dimension: The embedding vector dimension
    - embed_texts: Batch embedding generation
    
    Example:
        provider = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")
        embeddings = await provider.embed_texts(["Hello world", "Goodbye"])
        print(len(embeddings[0]))  # 384
    """
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Return the embedding dimension.
        
        This is used for vector store column configuration.
        Common dimensions:
        - all-MiniLM-L6-v2: 384
        - text-embedding-3-small: 1536
        """
        ...
    
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors (same order as input).
        """
        ...
    
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        This is a convenience method that calls embed_texts
        with a single-item list.
        
        Args:
            text: The text string to embed.
            
        Returns:
            Embedding vector as a list of floats.
        """
        result = await self.embed_texts([text])
        return result[0]
