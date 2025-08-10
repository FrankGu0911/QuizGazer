"""
Background Task Manager - Manages asynchronous document processing tasks with progress tracking.
"""

import uuid
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List, Callable, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, Empty
import os

try:
    from .models import ProcessingTask, DocumentType, ProcessingStatus
    from .document_processor import DocumentProcessor
except ImportError:
    from models import ProcessingTask, DocumentType, ProcessingStatus
    from document_processor import DocumentProcessor


class TaskProgressCallback:
    """Callback wrapper for task progress updates."""
    
    def __init__(self, task_id: str, callback: Callable[[str, float, str], None]):
        self.task_id = task_id
        self.callback = callback
    
    def update(self, progress: float, message: str = ""):
        """Update task progress."""
        try:
            self.callback(self.task_id, progress, message)
        except Exception as e:
            logging.warning(f"Progress callback failed for task {self.task_id}: {e}")


class BackgroundTaskManager:
    """Manages asynchronous document processing tasks with progress tracking."""
    
    def __init__(self, max_workers: int = 3, cleanup_interval: int = 3600):
        """
        Initialize the Background Task Manager.
        
        Args:
            max_workers: Maximum number of concurrent processing tasks
            cleanup_interval: Interval in seconds for automatic cleanup
        """
        self.max_workers = max_workers
        self.cleanup_interval = cleanup_interval
        self.logger = logging.getLogger(__name__)
        
        # Task storage
        self._tasks: Dict[str, ProcessingTask] = {}
        self._task_futures: Dict[str, Future] = {}
        self._progress_callbacks: Dict[str, List[TaskProgressCallback]] = {}
        self._cancelled_tasks: set = set()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Thread pool for processing tasks
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TaskManager")
        
        # Document processor
        self._document_processor = DocumentProcessor()
        
        # Cleanup thread
        self._cleanup_thread = None
        self._shutdown_event = threading.Event()
        self._start_cleanup_thread()
        
        self.logger.info(f"BackgroundTaskManager initialized with {max_workers} workers")
    
    def submit_processing_task(self, collection_id: str, file_path: str, doc_type: DocumentType, 
                             document_id: str = None) -> ProcessingTask:
        """
        Submit a document processing task.
        
        Args:
            collection_id: ID of the target collection
            file_path: Path to the document file
            doc_type: Type of document to process
            document_id: Optional document ID
            
        Returns:
            ProcessingTask object with task details
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        task_id = str(uuid.uuid4())
        if not document_id:
            document_id = str(uuid.uuid4())
        
        # Create task object
        task = ProcessingTask(
            id=task_id,
            document_id=document_id,
            collection_id=collection_id,
            filename=os.path.basename(file_path),
            status=ProcessingStatus.PENDING,
            progress=0.0,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            error_message=None
        )
        
        with self._lock:
            self._tasks[task_id] = task
            self._progress_callbacks[task_id] = []
            
            # Submit task to thread pool
            future = self._executor.submit(self._process_document_task, task, file_path, doc_type)
            self._task_futures[task_id] = future
        
        self.logger.info(f"Submitted processing task {task_id} for file {file_path}")
        return task
    
    def get_task_status(self, task_id: str) -> Optional[ProcessingTask]:
        """
        Get the status of a processing task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            ProcessingTask object or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a processing task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled, False otherwise
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            # Can only cancel pending or processing tasks
            if task.status not in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
                return False
            
            # Mark task as cancelled
            self._cancelled_tasks.add(task_id)
            task.status = ProcessingStatus.CANCELLED
            task.completed_at = datetime.now()
            
            # Try to cancel the future
            future = self._task_futures.get(task_id)
            if future:
                cancelled = future.cancel()
                if not cancelled and not future.done():
                    # If we can't cancel the future, it's already running
                    # The task will check the cancelled flag during processing
                    pass
            
            self._notify_progress(task_id, 0.0, "Task cancelled")
            self.logger.info(f"Cancelled task {task_id}")
            return True
    
    def list_active_tasks(self) -> List[ProcessingTask]:
        """
        List all active processing tasks.
        
        Returns:
            List of active ProcessingTask objects
        """
        with self._lock:
            active_statuses = [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]
            return [task for task in self._tasks.values() if task.status in active_statuses]
    
    def list_all_tasks(self) -> List[ProcessingTask]:
        """
        List all tasks (active and completed).
        
        Returns:
            List of all ProcessingTask objects
        """
        with self._lock:
            return list(self._tasks.values())
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """
        Clean up completed tasks older than specified hours.
        
        Args:
            older_than_hours: Remove tasks completed more than this many hours ago
            
        Returns:
            Number of tasks cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        cleaned_count = 0
        
        with self._lock:
            tasks_to_remove = []
            
            for task_id, task in self._tasks.items():
                # Only clean up completed, failed, or cancelled tasks
                if task.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                    completion_time = task.completed_at or task.created_at
                    if completion_time < cutoff_time:
                        tasks_to_remove.append(task_id)
            
            # Remove old tasks
            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                self._task_futures.pop(task_id, None)
                self._progress_callbacks.pop(task_id, None)
                self._cancelled_tasks.discard(task_id)
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old tasks")
        
        return cleaned_count
    
    def register_progress_callback(self, task_id: str, callback: Callable[[str, float, str], None]) -> bool:
        """
        Register a callback for task progress updates.
        
        Args:
            task_id: ID of the task to monitor
            callback: Function to call with (task_id, progress, message)
            
        Returns:
            True if callback was registered, False if task not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            callback_wrapper = TaskProgressCallback(task_id, callback)
            self._progress_callbacks[task_id].append(callback_wrapper)
            
            # If task is already completed, immediately call callback with final status
            task = self._tasks[task_id]
            if task.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                callback_wrapper.update(task.progress, f"Task {task.status.value}")
            
            return True
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about task processing.
        
        Returns:
            Dictionary with task statistics
        """
        with self._lock:
            stats = {
                "total_tasks": len(self._tasks),
                "pending_tasks": 0,
                "processing_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "cancelled_tasks": 0,
                "active_workers": self.max_workers
            }
            
            for task in self._tasks.values():
                if task.status == ProcessingStatus.PENDING:
                    stats["pending_tasks"] += 1
                elif task.status == ProcessingStatus.PROCESSING:
                    stats["processing_tasks"] += 1
                elif task.status == ProcessingStatus.COMPLETED:
                    stats["completed_tasks"] += 1
                elif task.status == ProcessingStatus.FAILED:
                    stats["failed_tasks"] += 1
                elif task.status == ProcessingStatus.CANCELLED:
                    stats["cancelled_tasks"] += 1
            
            return stats
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """
        Shutdown the task manager.
        
        Args:
            wait: Whether to wait for running tasks to complete
            timeout: Maximum time to wait for shutdown
        """
        self.logger.info("Shutting down BackgroundTaskManager...")
        
        # Signal cleanup thread to stop
        self._shutdown_event.set()
        
        # Shutdown executor (timeout parameter not supported in older Python versions)
        self._executor.shutdown(wait=wait)
        
        # Wait for cleanup thread
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        
        self.logger.info("BackgroundTaskManager shutdown complete")
    
    def _process_document_task(self, task: ProcessingTask, file_path: str, doc_type: DocumentType) -> List:
        """
        Process a document in the background.
        
        Args:
            task: ProcessingTask object
            file_path: Path to the document file
            doc_type: Type of document to process
            
        Returns:
            List of DocumentChunk objects
        """
        task_id = task.id
        
        try:
            # Check if task was cancelled before starting
            if task_id in self._cancelled_tasks:
                return []
            
            # Update task status to processing
            with self._lock:
                task.status = ProcessingStatus.PROCESSING
                task.started_at = datetime.now()
            
            self._notify_progress(task_id, 0.1, "Starting document processing...")
            
            # Check file size for progress estimation
            file_size = os.path.getsize(file_path)
            is_large_file = file_size > 5 * 1024 * 1024  # 5MB threshold
            
            # Process document with progress updates
            if is_large_file:
                self._notify_progress(task_id, 0.2, "Processing large file...")
            else:
                self._notify_progress(task_id, 0.3, "Processing document...")
            
            # Check for cancellation during processing
            if task_id in self._cancelled_tasks:
                return []
            
            # Actual document processing
            chunks = self._document_processor.process_document(file_path, doc_type, task.document_id)
            
            # Check for cancellation after processing
            if task_id in self._cancelled_tasks:
                return []
            
            self._notify_progress(task_id, 0.8, f"Generated {len(chunks)} chunks")
            
            # Simulate additional processing time for large files
            if is_large_file:
                time.sleep(0.5)  # Brief pause to simulate indexing
                self._notify_progress(task_id, 0.9, "Finalizing...")
            
            # Mark task as completed
            with self._lock:
                task.status = ProcessingStatus.COMPLETED
                task.completed_at = datetime.now()
                task.progress = 1.0
            
            self._notify_progress(task_id, 1.0, f"Processing completed: {len(chunks)} chunks generated")
            self.logger.info(f"Task {task_id} completed successfully with {len(chunks)} chunks")
            
            return chunks
            
        except Exception as e:
            # Mark task as failed
            with self._lock:
                task.status = ProcessingStatus.FAILED
                task.completed_at = datetime.now()
                task.error_message = str(e)
            
            self._notify_progress(task_id, 0.0, f"Processing failed: {str(e)}")
            self.logger.error(f"Task {task_id} failed: {e}")
            
            return []
    
    def _notify_progress(self, task_id: str, progress: float, message: str = ""):
        """
        Notify all registered callbacks about task progress.
        
        Args:
            task_id: ID of the task
            progress: Progress value (0.0 to 1.0)
            message: Progress message
        """
        with self._lock:
            # Update task progress
            task = self._tasks.get(task_id)
            if task:
                task.progress = progress
            
            # Notify callbacks
            callbacks = self._progress_callbacks.get(task_id, [])
            for callback in callbacks:
                callback.update(progress, message)
    
    def _start_cleanup_thread(self):
        """Start the automatic cleanup thread."""
        def cleanup_worker():
            while not self._shutdown_event.wait(self.cleanup_interval):
                try:
                    self.cleanup_completed_tasks()
                except Exception as e:
                    self.logger.error(f"Cleanup thread error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True, name="TaskCleanup")
        self._cleanup_thread.start()
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.shutdown(wait=False, timeout=5.0)
        except Exception:
            pass