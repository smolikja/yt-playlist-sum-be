"""
Service layer for managing background summarization jobs.
"""
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from loguru import logger

from app.models.sql import JobModel, ConversationModel
from app.models.enums import JobStatus
from app.models.api import PlaylistRequest, ConversationDetailResponse, MessageResponse
from app.repositories.job import JobRepository
from app.repositories.chat import ChatRepository
from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    ForbiddenError,
    BadRequestError,
    TooManyRequestsError,
)


class JobService:
    """
    Service for managing background summarization jobs.
    
    Handles job creation, status tracking, claiming completed jobs,
    and retry functionality.
    """
    
    def __init__(
        self,
        job_repository: JobRepository,
        chat_repository: ChatRepository,
    ) -> None:
        """
        Initialize the JobService.
        
        Args:
            job_repository: Repository for job database operations.
            chat_repository: Repository for conversation database operations.
        """
        self.job_repository = job_repository
        self.chat_repository = chat_repository

    async def create_job(
        self, user_id: uuid.UUID, playlist_url: str
    ) -> JobModel:
        """
        Create a new pending summarization job.
        
        Validates that the user hasn't exceeded the concurrent job limit.
        
        Args:
            user_id: The UUID of the user creating the job.
            playlist_url: The YouTube playlist URL to summarize.
            
        Returns:
            The created JobModel.
            
        Raises:
            TooManyRequestsError: If user has reached concurrent job limit.
        """
        # Check concurrent job limit
        active_count = await self.job_repository.count_active_user_jobs(user_id)
        if active_count >= settings.JOB_MAX_CONCURRENT_PER_USER:
            raise TooManyRequestsError(
                f"Maximum {settings.JOB_MAX_CONCURRENT_PER_USER} concurrent jobs allowed. "
                "Please wait for existing jobs to complete."
            )
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=settings.JOB_EXPIRY_DAYS)
        
        job = JobModel(
            user_id=user_id,
            playlist_url=playlist_url,
            status=JobStatus.PENDING.value,
            expires_at=expires_at,
        )
        
        job = await self.job_repository.create_job(job)
        logger.info(f"Created job {job.id} for user {user_id}")
        return job

    async def get_user_jobs(self, user_id: uuid.UUID) -> List[JobModel]:
        """
        Get all jobs for a user.
        
        Args:
            user_id: The UUID of the user.
            
        Returns:
            List of JobModel instances.
        """
        return await self.job_repository.get_user_jobs(user_id)

    async def get_job_status(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> JobModel:
        """
        Get job status with ownership validation.
        
        Args:
            job_id: The UUID of the job.
            user_id: The UUID of the user (for ownership check).
            
        Returns:
            The JobModel if found and owned by user.
            
        Raises:
            NotFoundError: If job doesn't exist.
            ForbiddenError: If user doesn't own the job.
        """
        job = await self.job_repository.get_job(job_id)
        if not job:
            raise NotFoundError("job", str(job_id))
        if job.user_id != user_id:
            raise ForbiddenError("You don't have access to this job.")
        return job

    async def claim_job(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationDetailResponse:
        """
        Claim a completed job and return the created conversation.
        
        The job is deleted after claiming (transformed to conversation).
        
        Args:
            job_id: The UUID of the job to claim.
            user_id: The UUID of the user claiming the job.
            
        Returns:
            ConversationDetailResponse with full conversation details.
            
        Raises:
            NotFoundError: If job doesn't exist.
            ForbiddenError: If user doesn't own the job.
            BadRequestError: If job is not completed.
        """
        job = await self.get_job_status(job_id, user_id)
        
        if job.status != JobStatus.COMPLETED.value:
            raise BadRequestError(
                f"Cannot claim job with status '{job.status}'. "
                "Only completed jobs can be claimed."
            )
        
        if not job.result_conversation_id:
            raise BadRequestError(
                "Job completed but no conversation was created. "
                "This may indicate an error during processing."
            )
        
        # Get the conversation with messages
        conversation = await self.chat_repository.get_conversation_with_messages(
            job.result_conversation_id, user_id
        )
        
        if not conversation:
            raise NotFoundError("conversation", job.result_conversation_id)
        
        # Delete the job (transform complete)
        await self.job_repository.delete_job(job)
        logger.info(f"User {user_id} claimed job {job_id} -> conversation {conversation.id}")
        
        # Return conversation details
        return ConversationDetailResponse(
            id=conversation.id,
            title=conversation.title,
            playlist_url=conversation.playlist_url,
            summary=conversation.summary or "",
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at,
                )
                for m in sorted(conversation.messages, key=lambda x: x.created_at)
            ],
        )

    async def retry_job(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> JobModel:
        """
        Retry a failed job by resetting it to pending status.
        
        Args:
            job_id: The UUID of the job to retry.
            user_id: The UUID of the user (for ownership check).
            
        Returns:
            The updated JobModel.
            
        Raises:
            NotFoundError: If job doesn't exist.
            ForbiddenError: If user doesn't own the job.
            BadRequestError: If job is not in failed status.
        """
        job = await self.get_job_status(job_id, user_id)
        
        if job.status != JobStatus.FAILED.value:
            raise BadRequestError(
                f"Cannot retry job with status '{job.status}'. "
                "Only failed jobs can be retried."
            )
        
        # Reset to pending
        await self.job_repository.update_job_status(
            job_id, JobStatus.PENDING, error_message=None
        )
        
        # Refresh and return
        updated_job = await self.job_repository.get_job(job_id)
        logger.info(f"User {user_id} retried job {job_id}")
        return updated_job  # type: ignore

    async def cancel_job(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """
        Cancel/delete a pending or failed job.
        
        Args:
            job_id: The UUID of the job to cancel.
            user_id: The UUID of the user (for ownership check).
            
        Raises:
            NotFoundError: If job doesn't exist.
            ForbiddenError: If user doesn't own the job.
            BadRequestError: If job is running or completed.
        """
        job = await self.get_job_status(job_id, user_id)
        
        if job.status == JobStatus.RUNNING.value:
            raise BadRequestError(
                "Cannot cancel a running job. Please wait for it to complete or fail."
            )
        
        if job.status == JobStatus.COMPLETED.value:
            raise BadRequestError(
                "Cannot cancel a completed job. Use claim to get the result, "
                "or wait for it to expire."
            )
        
        await self.job_repository.delete_job(job)
        logger.info(f"User {user_id} cancelled job {job_id}")
