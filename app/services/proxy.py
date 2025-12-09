from typing import Dict, Optional
import uuid
from loguru import logger
from app.core.config import settings

class ProxyService:
    @staticmethod
    def get_proxies() -> Optional[Dict[str, str]]:
        """
        Constructs the authenticated proxy URL string for DataImpulse.
        Appends a random session ID to the login to force a new IP for every request.
        Returns a dictionary compatible with requests/youtube-transcript-api.
        """
        if not (settings.DATAIMPULSE_HOST and settings.DATAIMPULSE_PORT and 
                settings.DATAIMPULSE_LOGIN and settings.DATAIMPULSE_PASSWORD):
            logger.info("Proxy settings not fully configured. Using direct connection.")
            return None

        # Generate a random session ID to force IP rotation
        session_id = str(uuid.uuid4())
        # DataImpulse format: login__session-ID
        login_with_session = f"{settings.DATAIMPULSE_LOGIN}__session-{session_id}"

        # Construct the authenticated URL
        # Format: http://login__session-id:password@host:port
        proxy_url = (
            f"http://{login_with_session}:{settings.DATAIMPULSE_PASSWORD}"
            f"@{settings.DATAIMPULSE_HOST}:{settings.DATAIMPULSE_PORT}"
        )

        logger.info(f"Fetching transcript using DataImpulse proxy configuration (Session: {session_id})...")
        
        # Return dict expected by requests/youtube-transcript-api
        return {
            "http": proxy_url,
            "https": proxy_url
        }
