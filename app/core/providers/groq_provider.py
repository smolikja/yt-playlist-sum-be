"""
Groq (Llama) implementation of LLMProvider.

This module provides a vendor-specific implementation for the Groq API
(fast Llama inference) while conforming to the LLMProvider interface.
"""
from typing import AsyncIterator, Optional

from groq import AsyncGroq
from loguru import logger

from app.core.providers.llm_provider import LLMProvider, LLMMessage, LLMResponse


class GroqProvider(LLMProvider):
    """
    Groq implementation of LLMProvider.
    
    Uses the Groq SDK for fast Llama model inference.
    
    Example:
        provider = GroqProvider(
            api_key="your-api-key",
            model_name="llama-4-scout-17b",
        )
        response = await provider.generate_text(messages)
    """
    
    def __init__(self, api_key: str, model_name: str = "llama-4-scout-17b"):
        """
        Initialize the Groq provider.
        
        Args:
            api_key: Groq API key.
            model_name: Model to use (e.g., "llama-4-scout-17b").
        """
        self.client = AsyncGroq(api_key=api_key)
        self.model_name = model_name
    
    async def generate_text(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate text completion using Groq."""
        # Convert to Groq message format (compatible with OpenAI format)
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        logger.debug(f"Sending request to Groq ({self.model_name})")
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=groq_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            logger.debug(f"Groq token usage: {usage}")
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=self.model_name,
            usage=usage,
        )
    
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream text completion from Groq."""
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=groq_messages,
            temperature=temperature,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
