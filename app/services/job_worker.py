"""
Background worker for processing summarization jobs.
"""
import asyncio
from typing import Optional
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sql import JobModel, ConversationModel
from app.models.enums import JobStatus
from app.models.api import PlaylistRequest
from app.repositories.job import JobRepository
from app.repositories.chat import ChatRepository
from app.services.chat import ChatService
from app.services.summarization import SummarizationService
from app.services.youtube import YouTubeService
from app.services.ingestion import IngestionService
from app.services.retrieval import RetrievalService
from app.core.config import settings
from app.core.db import get_db_session


class JobWorker:
    """
    Background worker that processes pending summarization jobs.
    
    Runs as an asyncio task, polling for pending jobs and processing them
    using the ChatService.
    """
    
    def __init__(
        self,
        poll_interval: int = 5,
    ) -> None:
        """
        Initialize the JobWorker.
        
        Args:
            poll_interval: Seconds between polling for new jobs.
        """
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the worker loop as a background task."""
        if self._running:
            logger.warning("JobWorker already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("JobWorker started")

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("JobWorker stopped")

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                await self._process_pending_jobs()
            except Exception as e:
                logger.error(f"Error in job worker loop: {e}")
            
            await asyncio.sleep(self.poll_interval)

    async def _process_pending_jobs(self) -> None:
        """Fetch and process pending jobs."""
        async for db in get_db_session():
            job_repository = JobRepository(db)
            
            # Get pending jobs
            pending_jobs = await job_repository.get_pending_jobs(limit=1)
            
            for job in pending_jobs:
                await self._process_single_job(job, db)

    async def _process_single_job(
        self, job: JobModel, db: AsyncSession
    ) -> None:
        """
        Process a single summarization job.
        
        Args:
            job: The JobModel to process.
            db: Database session.
        """
        job_repository = JobRepository(db)
        chat_repository = ChatRepository(db)
        
        logger.info(f"Processing job {job.id} for user {job.user_id}")
        
        # Mark as running
        await job_repository.update_job_status(job.id, JobStatus.RUNNING)
        
        try:
            # Import standalone factory functions (no FastAPI Depends)
            from app.api.dependencies import (
                create_youtube_service,
                create_summarization_service,
                create_ingestion_service,
                create_retrieval_service,
                get_rag_chat_llm_provider,
                get_fast_chat_llm_provider,
            )
            
            # Create service dependencies
            youtube_service = create_youtube_service(db)
            summarization_service = create_summarization_service()
            ingestion_service = await create_ingestion_service(db)
            retrieval_service = await create_retrieval_service(db)
            rag_llm = get_rag_chat_llm_provider()
            fast_llm = get_fast_chat_llm_provider()
            
            chat_service = ChatService(
                youtube_service=youtube_service,
                summarization_service=summarization_service,
                ingestion_service=ingestion_service,
                retrieval_service=retrieval_service,
                rag_llm_provider=rag_llm,
                fast_llm_provider=fast_llm,
                chat_repository=chat_repository,
            )
            
            # Execute summarization with timeout
            request = PlaylistRequest(url=job.playlist_url)  # type: ignore
            
            result = await asyncio.wait_for(
                chat_service.create_session(job.user_id, request),
                timeout=settings.JOB_TIMEOUT_SECONDS,
            )
            
            # Mark as completed
            await job_repository.update_job_status(
                job.id,
                JobStatus.COMPLETED,
                result_conversation_id=result.conversation_id,
            )
            logger.info(f"Job {job.id} completed successfully -> conversation {result.conversation_id}")
            
        except asyncio.TimeoutError:
            error_msg = f"Job timed out after {settings.JOB_TIMEOUT_SECONDS} seconds"
            await job_repository.update_job_status(
                job.id, JobStatus.FAILED, error_message=error_msg
            )
            logger.error(f"Job {job.id} failed: {error_msg}")
            
        except Exception as e:
            error_msg = str(e)
            await job_repository.update_job_status(
                job.id, JobStatus.FAILED, error_message=error_msg
            )
            logger.error(f"Job {job.id} failed: {error_msg}")


# Singleton instance for application lifecycle
_worker_instance: Optional[JobWorker] = None


def get_job_worker() -> JobWorker:
    """Get or create the singleton JobWorker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = JobWorker(poll_interval=5)
    return _worker_instance
