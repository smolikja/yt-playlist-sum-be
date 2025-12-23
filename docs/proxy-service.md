# Proxy Service

The Proxy Service manages rotating residential proxies for YouTube requests via DataImpulse.

## Purpose

YouTube may rate-limit or block direct API requests, especially at scale. The proxy service:

- Routes requests through rotating residential IPs
- Generates unique session IDs for IP rotation
- Falls back to direct connection when not configured

## Architecture

```mermaid
sequenceDiagram
    participant YT as YouTubeService
    participant PS as ProxyService
    participant DI as DataImpulse
    participant YOUTUBE as YouTube

    YT->>PS: get_proxies()
    PS->>PS: Generate session ID
    PS-->>YT: ProxyConfig
    YT->>DI: Request via proxy
    DI->>YOUTUBE: Forwarded request
    YOUTUBE-->>DI: Response
    DI-->>YT: Response
```

## Usage

```python
from app.services.proxy import ProxyService

# Initialize with credentials
proxy_service = ProxyService(
    host="gw.dataimpulse.com",
    port=823,
    login="your_login",
    password="your_password"
)

# Get proxy config with rotating IP
config = proxy_service.get_proxies()
if config:
    print(config.http)  # http://login__session-uuid:pass@host:port
```

## IP Rotation

Each call to `get_proxies()` generates a unique session ID:

```python
# DataImpulse format: login__session-{uuid}
login_with_session = f"{self.login}__session-{session_id}"
```

This ensures a new IP address is assigned for every request, preventing rate limiting.

## Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `DATAIMPULSE_HOST` | Proxy gateway hostname | `gw.dataimpulse.com` |
| `DATAIMPULSE_PORT` | Proxy port | `823` |
| `DATAIMPULSE_LOGIN` | Account username | `abc123` |
| `DATAIMPULSE_PASSWORD` | Account password | `secret` |

## Fallback Behavior

When proxy credentials are incomplete, the service falls back to direct connection:

```python
if not (self.host and self.port and self.login and self.password):
    logger.info("Proxy settings not fully configured. Using direct connection.")
    return None
```

## ProxyConfig Model

```python
class ProxyConfig(BaseModel):
    http: str   # HTTP proxy URL
    https: str  # HTTPS proxy URL
```

## Integration with YouTubeService

The YouTubeService uses the proxy for yt-dlp requests:

```python
class YouTubeService:
    def __init__(self, proxy_service: ProxyService, ...):
        self.proxy_service = proxy_service
    
    def _extract_playlist_info_sync(self, playlist_url: str):
        proxy_config = self.proxy_service.get_proxies()
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
        }
        if proxy_config:
            ydl_opts["proxy"] = proxy_config.http
        # ...
```

## Provider: DataImpulse

The service is configured for [DataImpulse](https://dataimpulse.com/) residential proxies.

Features:
- Rotating residential IPs globally
- Session-based IP persistence or rotation
- High success rate for YouTube
