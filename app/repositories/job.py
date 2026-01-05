"""
Repository layer for managing JobModel data.
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func as sql_func
import uuid

from app.models.sql import JobModel
from app.models.enums import JobStatus


class JobRepository:
    """
    Repository layer for managing background job data.
    
    Provides CRUD operations and specialized queries for job management.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the JobRepository.
        
        Args:
            db: Async database session.
        """
        self.db = db

    async def create_job(self, job: JobModel) -> JobModel:
        """
        Create a new job in the database.
        
        Args:
            job: The JobModel instance to persist.
            
        Returns:
            The persisted job with generated ID.
        """
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: uuid.UUID) -> Optional[JobModel]:
        """
        Retrieve a job by its ID.
        
        Args:
            job_id: The UUID of the job.
            
        Returns:
            The JobModel if found, None otherwise.
        """
        query = select(JobModel).where(JobModel.id == job_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_job_for_user(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[JobModel]:
        """
        Retrieve a job by ID with user ownership validation.
        
        Args:
            job_id: The UUID of the job.
            user_id: The UUID of the user who should own the job.
            
        Returns:
            The JobModel if found and owned by user, None otherwise.
        """
        query = select(JobModel).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_user_jobs(
        self, user_id: uuid.UUID, limit: int = 20
    ) -> List[JobModel]:
        """
        Retrieve all jobs for a specific user, ordered by creation time.
        
        Args:
            user_id: The UUID of the user.
            limit: Maximum number of jobs to return.
            
        Returns:
            List of JobModel instances.
        """
        query = (
            select(JobModel)
            .where(JobModel.user_id == user_id)
            .order_by(JobModel.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_pending_jobs(self, limit: int = 10) -> List[JobModel]:
        """
        Retrieve pending jobs for processing, ordered by creation time.
        
        Args:
            limit: Maximum number of jobs to fetch.
            
        Returns:
            List of pending JobModel instances.
        """
        query = (
            select(JobModel)
            .where(JobModel.status == JobStatus.PENDING.value)
            .order_by(JobModel.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_active_user_jobs(self, user_id: uuid.UUID) -> int:
        """
        Count active (pending or running) jobs for a user.
        
        Used for enforcing concurrent job limits.
        
        Args:
            user_id: The UUID of the user.
            
        Returns:
            Count of active jobs.
        """
        query = (
            select(sql_func.count())
            .select_from(JobModel)
            .where(
                JobModel.user_id == user_id,
                JobModel.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: JobStatus,
        error_message: Optional[str] = None,
        result_conversation_id: Optional[str] = None,
    ) -> None:
        """
        Update the status of a job.
        
        Args:
            job_id: The UUID of the job.
            status: The new status to set.
            error_message: Optional error message (for failed status).
            result_conversation_id: Optional conversation ID (for completed status).
        """
        now = datetime.utcnow()
        values: dict = {"status": status.value}
        
        if status == JobStatus.RUNNING:
            values["started_at"] = now
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            values["completed_at"] = now
            
        if error_message is not None:
            values["error_message"] = error_message
        if result_conversation_id is not None:
            values["result_conversation_id"] = result_conversation_id
            
        query = update(JobModel).where(JobModel.id == job_id).values(**values)
        await self.db.execute(query)
        await self.db.commit()

    async def delete_job(self, job: JobModel) -> None:
        """
        Delete a job from the database.
        
        Args:
            job: The JobModel instance to delete.
        """
        await self.db.delete(job)
        await self.db.commit()

    async def delete_expired_jobs(self) -> int:
        """
        Delete all expired jobs (cleanup task).
        
        Returns:
            Number of jobs deleted.
        """
        now = datetime.utcnow()
        query = delete(JobModel).where(JobModel.expires_at < now)
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount or 0
