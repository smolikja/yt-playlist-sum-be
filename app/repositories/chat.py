from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sql import ConversationModel

class ChatRepository:
    """
    Repository layer for managing ConversationModel data.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(self, conversation: ConversationModel) -> ConversationModel:
        """
        Saves a new conversation to the database.

        Args:
            conversation (ConversationModel): The conversation object to save.

        Returns:
            ConversationModel: The saved conversation object with updated state.
        """
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_user_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> List[ConversationModel]:
        """
        Retrieves a list of conversations for a specific user, ordered by creation date.

        Args:
            user_id (str): The user ID to filter by.
            limit (int): Maximum number of records to return.
            offset (int): Number of records to skip.

        Returns:
            List[ConversationModel]: A list of ConversationModel objects.
        """
        query = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
