"""
Extractive summarization service using TextRank algorithm.

This module provides the ExtractiveSummarizer class that extracts key sentences
from transcripts without using LLM - reducing token usage for subsequent
LLM-based summarization.

Multi-language support:
- Uses pycountry for ISO 639-1 code mapping
- NLTK tokenizers for 18 supported languages
- Falls back to regex-based sentence splitting for unsupported languages
"""
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional

import pycountry
from loguru import logger

from app.models import Video
from app.core.constants import ExtractiveSummaryConfig


# NLTK punkt tokenizer supported languages (lowercase)
# These are all the languages that NLTK ships with pre-trained sentence tokenizers
NLTK_SUPPORTED_LANGUAGES: frozenset[str] = frozenset({
    "czech", "danish", "dutch", "english", "estonian", "finnish",
    "french", "german", "greek", "italian", "norwegian", "polish",
    "portuguese", "russian", "slovene", "spanish", "swedish", "turkish",
})


@lru_cache(maxsize=256)
def iso_to_nltk_language(iso_code: str) -> Optional[str]:
    """
    Convert ISO 639-1/639-2 language code to NLTK language name.
    
    Uses pycountry for standardized ISO code lookup.
    Handles language variants like 'pt-BR', 'en-US', etc.
    
    Args:
        iso_code: ISO 639-1 (e.g., 'en') or 639-2 (e.g., 'eng') code,
                  optionally with region suffix (e.g., 'pt-BR').
    
    Returns:
        NLTK language name if supported, None otherwise.
    
    Examples:
        >>> iso_to_nltk_language('en')
        'english'
        >>> iso_to_nltk_language('pt-BR')
        'portuguese'
        >>> iso_to_nltk_language('ja')  # Not supported by NLTK
        None
    """
    if not iso_code:
        return None
    
    # Handle regional variants (e.g., 'pt-BR' → 'pt')
    base_code = iso_code.split("-")[0].split("_")[0].lower().strip()
    
    if not base_code:
        return None
    
    try:
        # Try ISO 639-1 (2-letter code) first
        lang = pycountry.languages.get(alpha_2=base_code)
        
        # Fallback to ISO 639-2 (3-letter code)
        if lang is None:
            lang = pycountry.languages.get(alpha_3=base_code)
        
        if lang is None:
            return None
        
        # Get the language name in lowercase
        lang_name = lang.name.lower()
        
        # Check if NLTK supports this language
        if lang_name in NLTK_SUPPORTED_LANGUAGES:
            return lang_name
        
        # Handle special cases where pycountry name differs from NLTK name
        # e.g., pycountry: "Greek, Modern (1453-)" → NLTK: "greek"
        for nltk_lang in NLTK_SUPPORTED_LANGUAGES:
            if nltk_lang in lang_name or lang_name.startswith(nltk_lang):
                return nltk_lang
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to resolve language code '{iso_code}': {e}")
        return None


class TextCompressor(ABC):
    """Abstract base class for text compression strategies."""
    
    @abstractmethod
    def compress(self, text: str, target_ratio: float) -> str:
        """
        Compress text to target ratio of original length.
        
        Args:
            text: Input text to compress.
            target_ratio: Target compression ratio (0.0-1.0).
            
        Returns:
            Compressed text.
        """
        pass


class ExtractiveSummarizer(TextCompressor):
    """
    Extractive summarization using TextRank algorithm.
    
    Supports multiple languages through pycountry ISO code resolution
    and NLTK tokenizer selection. Falls back to regex-based
    tokenization for unsupported languages.
    
    Example:
        summarizer = ExtractiveSummarizer(
            sentences_per_video=50,
            fallback_sentence_count=30,
        )
        
        # Extract key sentences from English text
        result = summarizer.extract_key_sentences(
            text="Long transcript...",
            language="en",
            sentence_count=20,
        )
        
        # Works with regional variants too
        result = summarizer.extract_key_sentences(
            text="Texto em português...",
            language="pt-BR",  # Resolves to 'portuguese'
            sentence_count=20,
        )
        
        # Compress multiple video transcripts
        compressed = summarizer.compress_transcripts(videos, target_ratio=0.2)
    """
    
    def __init__(
        self,
        sentences_per_video: int = ExtractiveSummaryConfig.SENTENCES_PER_VIDEO,
        fallback_sentence_count: int = ExtractiveSummaryConfig.FALLBACK_SENTENCE_COUNT,
    ):
        """
        Initialize the extractive summarizer.
        
        Args:
            sentences_per_video: Maximum sentences to extract per video.
            fallback_sentence_count: Sentence count when language not supported.
        """
        self.sentences_per_video = sentences_per_video
        self.fallback_sentence_count = fallback_sentence_count
        
        # Lazy-load heavy dependencies
        self._summarizer = None
        self._tokenizers: dict[str, object] = {}
    
    def _get_summarizer(self):
        """Lazy initialization of TextRank summarizer."""
        if self._summarizer is None:
            from sumy.summarizers.text_rank import TextRankSummarizer
            self._summarizer = TextRankSummarizer()
        return self._summarizer
    
    def _get_tokenizer(self, language: str):
        """
        Get NLTK tokenizer for the specified language.
        
        Args:
            language: ISO 639-1/639-2 code or language variant (e.g., 'en', 'pt-BR').
            
        Returns:
            NLTK Tokenizer instance or None if not supported.
        """
        nltk_lang = iso_to_nltk_language(language)
        if not nltk_lang:
            return None
        
        if nltk_lang not in self._tokenizers:
            try:
                from sumy.nlp.tokenizers import Tokenizer
                # Ensure NLTK data is downloaded
                self._ensure_nltk_data()
                self._tokenizers[nltk_lang] = Tokenizer(nltk_lang)
                logger.debug(f"Loaded NLTK tokenizer for '{nltk_lang}' (from '{language}')")
            except Exception as e:
                logger.warning(f"Failed to load tokenizer for {nltk_lang}: {e}")
                return None
        
        return self._tokenizers.get(nltk_lang)
    
    def _ensure_nltk_data(self) -> None:
        """Download required NLTK data if not present."""
        import nltk
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            logger.info("Downloading NLTK punkt_tab tokenizer data...")
            nltk.download("punkt_tab", quiet=True)
    
    def _fallback_tokenize(self, text: str) -> list[str]:
        """
        Fallback sentence tokenization using regex.
        
        Works for any language by splitting on common sentence endings.
        
        Args:
            text: Input text.
            
        Returns:
            List of sentences.
        """
        import re
        # Split on common sentence-ending punctuation followed by space/newline
        # Handles: . ! ? and their combinations with quotes/brackets
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_key_sentences(
        self,
        text: str,
        language: Optional[str] = None,
        sentence_count: Optional[int] = None,
    ) -> str:
        """
        Extract the most important sentences using TextRank algorithm.
        
        Args:
            text: Input text to summarize.
            language: ISO 639-1 language code (e.g., 'en', 'cs').
            sentence_count: Number of sentences to extract.
            
        Returns:
            Extracted key sentences as a single string.
        """
        if not text or len(text) < ExtractiveSummaryConfig.MIN_TEXT_LENGTH:
            return text
        
        count = sentence_count or self.sentences_per_video
        tokenizer = self._get_tokenizer(language or "en")
        
        if tokenizer:
            return self._extract_with_sumy(text, tokenizer, count)
        else:
            logger.debug(f"Language '{language}' not supported, using fallback")
            return self._extract_with_fallback(text, count)
    
    def _extract_with_sumy(self, text: str, tokenizer, sentence_count: int) -> str:
        """
        Extract sentences using sumy library with proper tokenizer.
        
        Args:
            text: Input text.
            tokenizer: NLTK Tokenizer instance.
            sentence_count: Number of sentences to extract.
            
        Returns:
            Extracted sentences as string.
        """
        from sumy.parsers.plaintext import PlaintextParser
        
        parser = PlaintextParser.from_string(text, tokenizer)
        summarizer = self._get_summarizer()
        
        # Ensure we don't request more sentences than available
        doc_sentence_count = len(list(parser.document.sentences))
        actual_count = min(sentence_count, doc_sentence_count)
        
        if actual_count == 0:
            return text
        
        sentences = summarizer(parser.document, actual_count)
        return " ".join(str(s) for s in sentences)
    
    def _extract_with_fallback(self, text: str, sentence_count: int) -> str:
        """
        Extract sentences using fallback regex tokenization + simple scoring.
        
        For unsupported languages, we use a simple approach:
        - Split by sentence-ending punctuation
        - Score by length + position (longer sentences near start/end are important)
        - Return top N sentences in original order
        
        Args:
            text: Input text.
            sentence_count: Number of sentences to extract.
            
        Returns:
            Extracted sentences as string.
        """
        sentences = self._fallback_tokenize(text)
        
        if len(sentences) <= sentence_count:
            return text
        
        # Score sentences: prefer longer ones and those at start/end
        scored = []
        total = len(sentences)
        for i, sentence in enumerate(sentences):
            # Position score: higher at start and end
            position_score = 1.0 - (abs(i - total / 2) / (total / 2)) * 0.3
            # Length score: prefer medium-length sentences (not too short, not too long)
            length_score = min(len(sentence) / 200, 1.0)
            score = position_score * 0.4 + length_score * 0.6
            scored.append((i, sentence, score))
        
        # Sort by score, take top N
        scored.sort(key=lambda x: x[2], reverse=True)
        top_indices = sorted([s[0] for s in scored[:sentence_count]])
        
        # Return in original order
        return " ".join(sentences[i] for i in top_indices)
    
    def compress(self, text: str, target_ratio: float = 0.2) -> str:
        """
        Compress text to approximately target_ratio of original.
        
        Implements TextCompressor interface.
        
        Args:
            text: Input text.
            target_ratio: Target compression ratio (0.0-1.0).
            
        Returns:
            Compressed text.
        """
        if not text or len(text) < ExtractiveSummaryConfig.MIN_TEXT_LENGTH:
            return text
        
        # Estimate sentence count based on target ratio
        sentences = self._fallback_tokenize(text)
        target_count = max(1, int(len(sentences) * target_ratio))
        
        return self.extract_key_sentences(text, sentence_count=target_count)
    
    def compress_transcripts(
        self,
        videos: list[Video],
        target_ratio: float = ExtractiveSummaryConfig.COMPRESSION_RATIO,
    ) -> list[Video]:
        """
        Compress transcripts for multiple videos.
        
        Creates new Video instances with compressed text in description.
        Clears transcript so that full_text returns the compressed version.
        Original transcript is NOT preserved (use before RAG indexing if needed).
        
        Args:
            videos: List of Video objects with transcripts.
            target_ratio: Target compression ratio per video.
            
        Returns:
            List of Video objects with compressed content.
        """
        compressed_videos = []
        
        for video in videos:
            if not video.transcript:
                compressed_videos.append(video)
                continue
            
            original_text = video.full_text
            original_len = len(original_text)
            
            if original_len < ExtractiveSummaryConfig.MIN_TEXT_LENGTH:
                compressed_videos.append(video)
                continue
            
            # Extract key sentences with language-aware tokenization
            compressed_text = self.extract_key_sentences(
                text=original_text,
                language=video.language,
                sentence_count=int(
                    len(self._fallback_tokenize(original_text)) * target_ratio
                ),
            )
            
            compression_achieved = len(compressed_text) / original_len
            logger.debug(
                f"Video {video.id}: {original_len} → {len(compressed_text)} chars "
                f"({compression_achieved:.1%})"
            )
            
            # Create new Video with compressed text
            # Clear transcript so full_text returns the compressed description
            compressed_videos.append(
                Video(
                    id=video.id,
                    title=video.title,
                    description=compressed_text,
                    transcript=[],  # Empty list to make full_text use description
                    transcript_missing=video.transcript_missing,
                    language=video.language,
                )
            )
        
        return compressed_videos
