"""
In-memory caching utilities.
"""
from cachetools import TTLCache
from typing import Optional
import hashlib

# Cache up to 100 summaries for 1 hour (3600 seconds)
summary_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)


def get_cache_key(url: str) -> str:
    """Generate a cache key from a URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def get_cached_summary(url: str) -> Optional[dict]:
    """
    Retrieve a cached summary for the given URL.
    
    Args:
        url: The playlist URL to look up.
        
    Returns:
        The cached summary dict if found, None otherwise.
    """
    key = get_cache_key(url)
    return summary_cache.get(key)


def set_cached_summary(url: str, summary_data: dict) -> None:
    """
    Cache a summary for the given URL.
    
    Args:
        url: The playlist URL.
        summary_data: The summary data to cache.
    """
    key = get_cache_key(url)
    summary_cache[key] = summary_data
