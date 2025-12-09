from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.models.sql import VideoModel

class VideoRepository:
    """
    Repository layer for managing VideoModel data in the database.
    Abstracts direct SQLAlchemy sessions and operations.
    """
    def __init__(self, db: AsyncSession):
        """
        Initialize the VideoRepository.

        Args:
            db (AsyncSession): The SQLAlchemy async session for database operations.
        """
        self.db = db

    async def get_existing_videos(self, video_ids: List[str]) -> List[VideoModel]:
        """
        Retrieves existing VideoModels from the database matching the provided list of IDs.

        Args:
            video_ids (List[str]): A list of YouTube video IDs to check for.

        Returns:
            List[VideoModel]: A list of VideoModel objects found in the database.
        """
        if not video_ids:
            return []
        query = select(VideoModel).where(VideoModel.id.in_(video_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def save_videos(self, videos: List[VideoModel]):
        """
        Bulk saves a list of VideoModel objects to the database.
        Ignores duplicates using ON CONFLICT DO NOTHING logic.

        Args:
            videos (List[VideoModel]): A list of VideoModel objects to persist.
        """
        if not videos:
            return

        # Prepare values for bulk insert
        values = [
            {
                "id": video.id,
                "title": video.title,
                "transcript": video.transcript,
                "language": video.language,
                "created_at": video.created_at,
            }
            for video in videos
        ]

        stmt = insert(VideoModel).values(values)
        
        # On conflict do nothing (ignore duplicates)
        stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
        
        await self.db.execute(stmt)
        await self.db.commit()
