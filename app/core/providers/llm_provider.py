"""
Abstract base class for LLM providers.

This module defines a vendor-neutral interface for interacting with
Large Language Models. Concrete implementations (Gemini, Groq, OpenAI)
must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import LLMRole


class LLMMessage(BaseModel):
    """Vendor-neutral message format for LLM conversations."""
    
    role: LLMRole
    content: str
    
    model_config = ConfigDict(frozen=True)


class LLMResponse(BaseModel):
    """Standardized response from an LLM provider."""
    
    content: str
    model: str
    usage: Optional[dict[str, int]] = None
    
    model_config = ConfigDict(frozen=True)


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers.
    
    Implementations must provide:
    - generate_text: For standard completions
    - generate_stream: For streaming responses (optional, can raise NotImplementedError)
    
    Example:
        provider = GeminiProvider(api_key="...", model_name="gemini-2.5-flash")
        response = await provider.generate_text([
            LLMMessage(role=LLMRole.SYSTEM, content="You are helpful."),
            LLMMessage(role=LLMRole.USER, content="Hello!"),
        ])
        print(response.content)
    """
    
    @abstractmethod
    async def generate_text(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text completion from messages.
        
        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens to generate (None for model default).
            
        Returns:
            LLMResponse containing generated content and metadata.
        """
        ...
    
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Stream text completion token by token.
        
        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature (0.0-1.0).
            
        Yields:
            Individual tokens as they are generated.
            
        Note:
            Default implementation raises NotImplementedError.
            Override in subclasses that support streaming.
        """
        raise NotImplementedError("Streaming not supported by this provider")
        # Yield is needed to make this an async generator
        yield ""  # type: ignore
