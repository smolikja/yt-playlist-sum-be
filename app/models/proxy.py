from typing import Optional
from pydantic import BaseModel

class ProxyConfig(BaseModel):
    http: Optional[str] = None
    https: Optional[str] = None
