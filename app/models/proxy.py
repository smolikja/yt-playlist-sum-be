"""
Pydantic model for proxy configuration.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProxyConfig(BaseModel):
    """Configuration model for HTTP/HTTPS proxy settings."""

    http: Optional[str] = None
    https: Optional[str] = None

    model_config = ConfigDict(frozen=True)
