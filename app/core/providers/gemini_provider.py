"""
Google Gemini implementation of LLMProvider.

This module provides a vendor-specific implementation for the Gemini API
while conforming to the LLMProvider interface.
"""
from typing import AsyncIterator, Optional

import google.generativeai as genai
from loguru import logger

from app.core.providers.llm_provider import LLMProvider, LLMMessage, LLMResponse
from app.models.enums import LLMRole


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of LLMProvider.
    
    Uses the google-generativeai SDK for async text generation.
    
    Example:
        provider = GeminiProvider(
            api_key="your-api-key",
            model_name="gemini-2.5-flash",
        )
        response = await provider.generate_text(messages)
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the Gemini provider.
        
        Args:
            api_key: Google AI API key.
            model_name: Gemini model to use (e.g., "gemini-2.5-flash").
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self._model = genai.GenerativeModel(model_name)
    
    async def generate_text(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text completion using Gemini.
        
        Gemini uses a single prompt format, so messages are converted
        to a structured text prompt.
        """
        prompt = self._format_messages(messages)
        
        config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        logger.debug(f"Sending request to Gemini ({self.model_name})")
        response = await self._model.generate_content_async(
            prompt,
            generation_config=config,
        )
        
        usage = None
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
            logger.debug(f"Gemini token usage: {usage}")
        
        return LLMResponse(
            content=response.text,
            model=self.model_name,
            usage=usage,
        )
    
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream text completion from Gemini."""
        prompt = self._format_messages(messages)
        
        config = genai.GenerationConfig(temperature=temperature)
        
        response = await self._model.generate_content_async(
            prompt,
            generation_config=config,
            stream=True,
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    
    def _format_messages(self, messages: list[LLMMessage]) -> str:
        """
        Convert universal messages to Gemini prompt format.
        
        Since Gemini prefers a single prompt, we format messages
        with role labels for context.
        """
        parts = []
        for msg in messages:
            if msg.role == LLMRole.SYSTEM:
                parts.append(f"System Instructions: {msg.content}\n\n")
            elif msg.role == LLMRole.USER:
                parts.append(f"User: {msg.content}\n")
            elif msg.role == LLMRole.ASSISTANT:
                parts.append(f"Assistant: {msg.content}\n")
        return "".join(parts)
