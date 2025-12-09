from typing import Optional
import uuid
from loguru import logger
from app.models import ProxyConfig

class ProxyService:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, 
                 login: Optional[str] = None, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.login = login
        self.password = password

    def get_proxies(self) -> Optional[ProxyConfig]:
        """
        Constructs the authenticated proxy URL string for DataImpulse.
        Appends a random session ID to the login to force a new IP for every request.
        Returns a ProxyConfig object.
        """
        if not (self.host and self.port and self.login and self.password):
            logger.info("Proxy settings not fully configured. Using direct connection.")
            return None

        # Generate a random session ID to force IP rotation
        session_id = str(uuid.uuid4())
        # DataImpulse format: login__session-ID
        login_with_session = f"{self.login}__session-{session_id}"

        # Construct the authenticated URL
        # Format: http://login__session-id:password@host:port
        proxy_url = (
            f"http://{login_with_session}:{self.password}"
            f"@{self.host}:{self.port}"
        )

        logger.info(f"Fetching transcript using DataImpulse proxy configuration (Session: {session_id})...")
        
        return ProxyConfig(
            http=proxy_url,
            https=proxy_url
        )