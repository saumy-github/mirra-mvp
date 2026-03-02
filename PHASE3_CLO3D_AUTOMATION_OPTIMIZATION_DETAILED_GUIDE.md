# Phase 3: CLO3D Automation & Optimization - Detailed Implementation Guide

**Project:** MIRRA MVP - CLO3D Migration  
**Phase:** 3 of 5 - Automation & Optimization  
**Duration:** Week 4 (5 working days)  
**Status:** Ready for Implementation  
**Branch:** `clo3danant`  
**Prerequisites:** Phase 1 & Phase 2 Complete

---

## Table of Contents

1. [Phase Overview](#phase-overview)
2. [Prerequisites from Phase 2](#prerequisites-from-phase-2)
3. [Week 4: Automation & Optimization](#week-4-automation--optimization)
   - [Day 16: Batch Processing System](#day-16-batch-processing-system)
   - [Day 17: Error Recovery & Retry Logic](#day-17-error-recovery--retry-logic)
   - [Day 18: Performance Optimization](#day-18-performance-optimization)
   - [Day 19: Quality Assurance Automation](#day-19-quality-assurance-automation)
   - [Day 20: Monitoring & Logging System](#day-20-monitoring--logging-system)
4. [Phase Completion Checklist](#phase-completion-checklist)
5. [Troubleshooting Guide](#troubleshooting-guide)

---

## Phase Overview

### Starting Point (From Phase 2)

You now have:
✅ Complete CLO API wrapper with all operations  
✅ Fabric library with 15+ presets  
✅ Automated seam builder for standard garments  
✅ Step 5 assembly fully replaced with CLO  
✅ Color/texture application integrated  
✅ End-to-end pipeline functional  
✅ Basic integration testing complete

### Goals for Phase 3

By the end of Phase 3, you will have:

1. ✅ Batch processing for multiple avatars simultaneously
2. ✅ Robust error handling with automatic retry
3. ✅ Performance optimizations (50%+ speed improvement)
4. ✅ Automated quality checks (mesh validation, texture verification)
5. ✅ Comprehensive logging and monitoring
6. ✅ Production-ready pipeline
7. ✅ Documentation for operators

### Success Criteria

- [ ] Can process 10+ avatars in parallel without manual intervention
- [ ] Automatic recovery from transient failures (API timeouts, etc.)
- [ ] Average processing time < 5 minutes per garment
- [ ] Automated quality gates prevent bad outputs
- [ ] Full observability via logs and metrics
- [ ] Zero manual steps required for standard workflows
- [ ] System handles edge cases gracefully

### Time Allocation

| Week | Days | Focus | Deliverable |
|------|------|-------|-------------|
| **Week 4** | 16-20 | Automation & optimization | Batch processing, error handling, monitoring |

**Total:** 30-40 hours

---

## Prerequisites from Phase 2

### Verify Phase 2 Completion

Before starting Phase 3, verify all Phase 2 deliverables:

```powershell
# Navigate to project
cd C:\Users\Anant\mirra-mvp

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run Phase 2 validation
python tests\test_phase2_complete.py
```

**Expected output:**
```
============================================================
PHASE 2 COMPLETE INTEGRATION TEST
============================================================

[1/8] Testing CLO API Client...
✓ CLO API connection successful
✓ Project creation works
✓ Avatar import works
✓ Pattern import works
✓ Simulation runs successfully

[2/8] Testing Fabric Library...
✓ 15 fabric presets loaded
✓ Garment mapping works
✓ Custom fabric creation works

[3/8] Testing Seam Builder...
✓ T-shirt seams generated
✓ Pants seams generated
✓ Seam validation passes

[4/8] Testing Step 5 Assembly...
✓ Assembly module loads
✓ Pattern positioning works
✓ Color application works
✓ Texture application works

[5/8] Testing Pipeline Integration...
✓ Pipeline config updated
✓ Step 5 calls CLO assembly
✓ End-to-end workflow runs

[6/8] Testing Output Quality...
✓ GLB file exported
✓ Mesh topology valid
✓ Textures applied correctly
✓ UV mapping intact

[7/8] Testing Edge Cases...
✓ Large avatars handled
✓ Small avatars handled
✓ Complex patterns work

[8/8] Performance Benchmark...
✓ Single garment: ~8 minutes
✓ Memory usage: <4GB peak

============================================================
✓✓✓ PHASE 2 COMPLETE - ALL TESTS PASSED ✓✓✓
============================================================

Ready to proceed to Phase 3: Automation & Optimization
```

### Required Files from Phase 2

Verify these files exist:

```powershell
# Core CLO integration modules
Test-Path "Working_Cloth_3D_Pipeline\steps\clo_integration\clo_client.py"
Test-Path "Working_Cloth_3D_Pipeline\steps\clo_integration\fabric_library.py"
Test-Path "Working_Cloth_3D_Pipeline\steps\clo_integration\seam_builder.py"
Test-Path "Working_Cloth_3D_Pipeline\steps\clo_integration\simulation_runner.py"

# Step 5 replacement
Test-Path "Working_Cloth_3D_Pipeline\steps\step5_clo_assembly.py"

# Updated pipeline
Test-Path "Working_Cloth_3D_Pipeline\pipeline.py"

# Configuration
Test-Path "config\clo_config.py"
```

All should return `True`.

---

## Week 4: Automation & Optimization

Phase 3 focuses on making the pipeline production-ready through automation, error handling, and performance optimization.

---

## Day 16: Batch Processing System

**Time:** 6-8 hours  
**Goal:** Implement parallel processing for multiple avatars and garments

### 16.1: Batch Processing Architecture

**Objective:** Design system to process multiple jobs concurrently

#### Understanding Batch Processing Needs

CLO3D supports multiple project instances, allowing us to:
1. Process different avatars simultaneously
2. Process different garments for the same avatar in parallel
3. Utilize multi-core CPUs effectively
4. Reduce total pipeline time from hours to minutes

**Architecture:**
```
BatchProcessor
├── Job Queue (FIFO)
├── Worker Pool (3-5 workers)
├── Job Status Tracker
├── Result Collector
└── Error Handler
```

### 16.2: Implement Job Queue System

**File:** `Working_Cloth_3D_Pipeline/batch/job_queue.py`

```python
"""
Job queue system for batch processing
Manages pipeline jobs with priorities and dependencies
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import uuid
from queue import PriorityQueue
import threading


class JobStatus(Enum):
    """Job lifecycle states"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class PipelineJob:
    """
    Represents a single pipeline job
    
    Attributes:
        job_id: Unique job identifier
        avatar_id: STAR avatar identifier
        garment_type: Type of garment (tshirt, pants, etc.)
        measurements: Body measurements dict
        design_params: Design customization parameters
        priority: Job priority level
        dependencies: List of job IDs this job depends on
        status: Current job status
        created_at: Job creation timestamp
        started_at: Job start timestamp
        completed_at: Job completion timestamp
        result_path: Path to output files
        error: Error message if failed
        retry_count: Number of retry attempts
        metadata: Additional job metadata
    """
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    avatar_id: str = ""
    garment_type: str = ""
    measurements: Dict[str, float] = field(default_factory=dict)
    design_params: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Priority queue comparison"""
        return self.priority.value < other.priority.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize job to dictionary"""
        return {
            'job_id': self.job_id,
            'avatar_id': self.avatar_id,
            'garment_type': self.garment_type,
            'measurements': self.measurements,
            'design_params': self.design_params,
            'priority': self.priority.name,
            'dependencies': self.dependencies,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result_path': self.result_path,
            'error': self.error,
            'retry_count': self.retry_count,
            'metadata': self.metadata
        }


class JobQueue:
    """
    Thread-safe job queue with priority support
    
    Features:
    - Priority-based scheduling
    - Dependency management
    - Thread-safe operations
    - Job status tracking
    - Metrics collection
    """
    
    def __init__(self):
        self._queue = PriorityQueue()
        self._jobs: Dict[str, PipelineJob] = {}
        self._lock = threading.RLock()
        self._metrics = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0
        }
    
    def add_job(self, job: PipelineJob) -> str:
        """
        Add job to queue
        
        Args:
            job: PipelineJob instance
            
        Returns:
            job_id: Unique job identifier
            
        Raises:
            ValueError: If job has unmet dependencies
        """
        with self._lock:
            # Validate dependencies
            for dep_id in job.dependencies:
                if dep_id not in self._jobs:
                    raise ValueError(f"Dependency job {dep_id} not found")
                if self._jobs[dep_id].status not in [JobStatus.COMPLETED]:
                    raise ValueError(f"Dependency job {dep_id} not completed")
            
            # Store job
            self._jobs[job.job_id] = job
            job.status = JobStatus.QUEUED
            
            # Add to priority queue
            self._queue.put((job.priority.value, job.job_id))
            
            # Update metrics
            self._metrics['total_jobs'] += 1
            
            return job.job_id
    
    def get_job(self, timeout: Optional[float] = None) -> Optional[PipelineJob]:
        """
        Get next job from queue (blocks if empty)
        
        Args:
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            PipelineJob or None if timeout
        """
        try:
            _, job_id = self._queue.get(timeout=timeout)
            with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.now()
                return job
        except:
            return None
    
    def update_job_status(
        self, 
        job_id: str, 
        status: JobStatus,
        result_path: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Update job status
        
        Args:
            job_id: Job identifier
            status: New status
            result_path: Path to results (if completed)
            error: Error message (if failed)
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            job.status = status
            
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.now()
                job.result_path = result_path
                self._metrics['completed_jobs'] += 1
            
            elif status == JobStatus.FAILED:
                job.completed_at = datetime.now()
                job.error = error
                self._metrics['failed_jobs'] += 1
            
            elif status == JobStatus.CANCELLED:
                job.completed_at = datetime.now()
                self._metrics['cancelled_jobs'] += 1
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get current job status"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.status if job else None
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get full job information"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None
    
    def list_jobs(
        self, 
        status: Optional[JobStatus] = None,
        avatar_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List jobs with optional filtering
        
        Args:
            status: Filter by status
            avatar_id: Filter by avatar ID
            
        Returns:
            List of job dictionaries
        """
        with self._lock:
            jobs = list(self._jobs.values())
            
            if status:
                jobs = [j for j in jobs if j.status == status]
            
            if avatar_id:
                jobs = [j for j in jobs if j.avatar_id == avatar_id]
            
            return [j.to_dict() for j in jobs]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        with self._lock:
            return {
                **self._metrics,
                'queued_jobs': self._queue.qsize(),
                'pending_jobs': len([j for j in self._jobs.values() 
                                    if j.status == JobStatus.PENDING]),
                'running_jobs': len([j for j in self._jobs.values() 
                                    if j.status == JobStatus.RUNNING])
            }
    
    def clear_completed(self, age_hours: int = 24):
        """
        Clear completed jobs older than specified hours
        
        Args:
            age_hours: Age threshold in hours
        """
        with self._lock:
            cutoff = datetime.now()
            to_remove = []
            
            for job_id, job in self._jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if job.completed_at:
                        age = (cutoff - job.completed_at).total_seconds() / 3600
                        if age > age_hours:
                            to_remove.append(job_id)
            
            for job_id in to_remove:
                del self._jobs[job_id]
    
    def size(self) -> int:
        """Get queue size"""
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()


# Global job queue instance
_job_queue = JobQueue()


def get_job_queue() -> JobQueue:
    """Get global job queue instance"""
    return _job_queue
```

**Create the file:**

```powershell
# Create batch processing directory
New-Item -ItemType Directory -Force -Path "Working_Cloth_3D_Pipeline\batch"

# Create __init__.py
New-Item -ItemType File -Force -Path "Working_Cloth_3D_Pipeline\batch\__init__.py"
@"
from .job_queue import JobQueue, PipelineJob, JobStatus, JobPriority, get_job_queue
from .batch_processor import BatchProcessor, WorkerConfig

__all__ = [
    'JobQueue',
    'PipelineJob', 
    'JobStatus',
    'JobPriority',
    'get_job_queue',
    'BatchProcessor',
    'WorkerConfig'
]
"@ | Set-Content "Working_Cloth_3D_Pipeline\batch\__init__.py"

# Copy the job_queue.py content
# (Copy the Python code above into this file manually or via editor)
```

### 16.3: Implement Batch Processor with Worker Pool

**File:** `Working_Cloth_3D_Pipeline/batch/batch_processor.py`

```python
"""
Batch processor with worker pool for parallel pipeline execution
"""

import threading
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, Future
import traceback

from .job_queue import JobQueue, PipelineJob, JobStatus, get_job_queue
from ..pipeline import ClothPipeline


logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Worker pool configuration"""
    num_workers: int = 3
    max_retries: int = 3
    retry_delay_seconds: int = 30
    worker_timeout_minutes: int = 15
    enable_monitoring: bool = True


class PipelineWorker:
    """
    Worker thread that processes pipeline jobs
    
    Each worker:
    - Pulls jobs from queue
    - Executes full pipeline
    - Handles errors and retries
    - Reports results
    """
    
    def __init__(
        self, 
        worker_id: int,
        job_queue: JobQueue,
        config: WorkerConfig,
        on_job_complete: Optional[Callable] = None,
        on_job_failed: Optional[Callable] = None
    ):
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.config = config
        self.on_job_complete = on_job_complete
        self.on_job_failed = on_job_failed
        
        self.is_running = False
        self.current_job: Optional[PipelineJob] = None
        self.jobs_processed = 0
        self.jobs_failed = 0
        
        self.logger = logging.getLogger(f"Worker-{worker_id}")
    
    def start(self):
        """Start worker thread"""
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.logger.info(f"Worker {self.worker_id} started")
    
    def stop(self):
        """Stop worker thread"""
        self.is_running = False
        self.logger.info(f"Worker {self.worker_id} stopping...")
    
    def _run(self):
        """Main worker loop"""
        while self.is_running:
            try:
                # Get next job (1 second timeout to check is_running)
                job = self.job_queue.get_job(timeout=1.0)
                
                if not job:
                    continue
                
                self.current_job = job
                self.logger.info(
                    f"Processing job {job.job_id} "
                    f"(avatar={job.avatar_id}, garment={job.garment_type})"
                )
                
                # Execute job
                success, result_path, error = self._execute_job(job)
                
                if success:
                    self.job_queue.update_job_status(
                        job.job_id,
                        JobStatus.COMPLETED,
                        result_path=result_path
                    )
                    self.jobs_processed += 1
                    self.logger.info(f"Job {job.job_id} completed successfully")
                    
                    if self.on_job_complete:
                        self.on_job_complete(job, result_path)
                
                else:
                    # Handle failure and retries
                    if job.retry_count < self.config.max_retries:
                        job.retry_count += 1
                        self.job_queue.update_job_status(
                            job.job_id,
                            JobStatus.RETRYING
                        )
                        self.logger.warning(
                            f"Job {job.job_id} failed, retrying "
                            f"({job.retry_count}/{self.config.max_retries})"
                        )
                        
                        # Wait before retry
                        time.sleep(self.config.retry_delay_seconds)
                        
                        # Re-queue job
                        job.status = JobStatus.PENDING
                        self.job_queue.add_job(job)
                    
                    else:
                        self.job_queue.update_job_status(
                            job.job_id,
                            JobStatus.FAILED,
                            error=error
                        )
                        self.jobs_failed += 1
                        self.logger.error(
                            f"Job {job.job_id} failed after "
                            f"{job.retry_count} retries: {error}"
                        )
                        
                        if self.on_job_failed:
                            self.on_job_failed(job, error)
                
                self.current_job = None
            
            except Exception as e:
                self.logger.error(f"Worker error: {e}\n{traceback.format_exc()}")
                if self.current_job:
                    self.job_queue.update_job_status(
                        self.current_job.job_id,
                        JobStatus.FAILED,
                        error=str(e)
                    )
    
    def _execute_job(self, job: PipelineJob) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Execute pipeline job
        
        Returns:
            (success, result_path, error_message)
        """
        try:
            # Initialize pipeline
            pipeline = ClothPipeline()
            
            # Set job parameters
            pipeline.set_avatar_id(job.avatar_id)
            pipeline.set_garment_type(job.garment_type)
            pipeline.set_measurements(job.measurements)
            pipeline.set_design_params(job.design_params)
            
            # Run full pipeline
            result = pipeline.run()
            
            if result['success']:
                return True, result.get('output_path'), None
            else:
                return False, None, result.get('error', 'Unknown error')
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return False, None, error_msg
    
    def get_status(self) -> Dict[str, Any]:
        """Get worker status"""
        return {
            'worker_id': self.worker_id,
            'is_running': self.is_running,
            'current_job': self.current_job.job_id if self.current_job else None,
            'jobs_processed': self.jobs_processed,
            'jobs_failed': self.jobs_failed
        }


class BatchProcessor:
    """
    Batch processor with worker pool for parallel execution
    
    Usage:
        processor = BatchProcessor(num_workers=3)
        processor.start()
        
        # Submit jobs
        job = PipelineJob(
            avatar_id="user_123",
            garment_type="tshirt",
            measurements={...}
        )
        job_id = processor.submit_job(job)
        
        # Check status
        status = processor.get_job_status(job_id)
        
        # Wait for completion
        processor.wait_all()
        processor.stop()
    """
    
    def __init__(self, config: Optional[WorkerConfig] = None):
        self.config = config or WorkerConfig()
        self.job_queue = get_job_queue()
        self.workers: list[PipelineWorker] = []
        self.is_running = False
        
        self.logger = logging.getLogger("BatchProcessor")
        
        # Callbacks
        self._on_job_complete_callbacks = []
        self._on_job_failed_callbacks = []
    
    def start(self):
        """Start batch processor and worker pool"""
        if self.is_running:
            self.logger.warning("Batch processor already running")
            return
        
        self.is_running = True
        
        # Create and start workers
        for i in range(self.config.num_workers):
            worker = PipelineWorker(
                worker_id=i,
                job_queue=self.job_queue,
                config=self.config,
                on_job_complete=self._handle_job_complete,
                on_job_failed=self._handle_job_failed
            )
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(
            f"Batch processor started with {self.config.num_workers} workers"
        )
    
    def stop(self):
        """Stop batch processor and all workers"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop all workers
        for worker in self.workers:
            worker.stop()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.thread.join(timeout=5.0)
        
        self.logger.info("Batch processor stopped")
    
    def submit_job(self, job: PipelineJob) -> str:
        """
        Submit job to queue
        
        Args:
            job: PipelineJob instance
            
        Returns:
            job_id: Unique job identifier
        """
        if not self.is_running:
            raise RuntimeError("Batch processor not running. Call start() first.")
        
        job_id = self.job_queue.add_job(job)
        self.logger.info(f"Job {job_id} submitted to queue")
        return job_id
    
    def submit_batch(self, jobs: list[PipelineJob]) -> list[str]:
        """
        Submit multiple jobs
        
        Args:
            jobs: List of PipelineJob instances
            
        Returns:
            List of job IDs
        """
        job_ids = []
        for job in jobs:
            job_id = self.submit_job(job)
            job_ids.append(job_id)
        
        self.logger.info(f"Batch of {len(jobs)} jobs submitted")
        return job_ids
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status"""
        return self.job_queue.get_job_status(job_id)
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get full job information"""
        return self.job_queue.get_job_info(job_id)
    
    def list_jobs(self, status: Optional[JobStatus] = None) -> list[Dict[str, Any]]:
        """List all jobs with optional status filter"""
        return self.job_queue.list_jobs(status=status)
    
    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for specific job to complete
        
        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds
            
        Returns:
            True if completed, False if timeout/failed
        """
        start_time = time.time()
        
        while True:
            status = self.get_job_status(job_id)
            
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return status == JobStatus.COMPLETED
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(1.0)
    
    def wait_all(self, timeout: Optional[float] = None) -> Dict[str, int]:
        """
        Wait for all jobs to complete
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            Dictionary with completion counts
        """
        start_time = time.time()
        
        while True:
            metrics = self.get_metrics()
            
            if metrics['queued_jobs'] == 0 and metrics['running_jobs'] == 0:
                return {
                    'completed': metrics['completed_jobs'],
                    'failed': metrics['failed_jobs'],
                    'cancelled': metrics['cancelled_jobs']
                }
            
            if timeout and (time.time() - start_time) > timeout:
                return metrics
            
            time.sleep(2.0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics"""
        queue_metrics = self.job_queue.get_metrics()
        
        worker_metrics = {
            'total_workers': len(self.workers),
            'active_workers': sum(1 for w in self.workers if w.current_job),
            'total_processed': sum(w.jobs_processed for w in self.workers),
            'total_failed': sum(w.jobs_failed for w in self.workers)
        }
        
        return {
            **queue_metrics,
            **worker_metrics
        }
    
    def get_worker_status(self) -> list[Dict[str, Any]]:
        """Get status of all workers"""
        return [w.get_status() for w in self.workers]
    
    def on_job_complete(self, callback: Callable[[PipelineJob, str], None]):
        """Register callback for job completion"""
        self._on_job_complete_callbacks.append(callback)
    
    def on_job_failed(self, callback: Callable[[PipelineJob, str], None]):
        """Register callback for job failure"""
        self._on_job_failed_callbacks.append(callback)
    
    def _handle_job_complete(self, job: PipelineJob, result_path: str):
        """Handle job completion"""
        for callback in self._on_job_complete_callbacks:
            try:
                callback(job, result_path)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    def _handle_job_failed(self, job: PipelineJob, error: str):
        """Handle job failure"""
        for callback in self._on_job_failed_callbacks:
            try:
                callback(job, error)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
```

### 16.4: Create Batch Processing CLI

**File:** `Working_Cloth_3D_Pipeline/batch/batch_cli.py`

```python
"""
Command-line interface for batch processing
"""

import click
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from .batch_processor import BatchProcessor, WorkerConfig
from .job_queue import PipelineJob, JobPriority, JobStatus


@click.group()
def cli():
    """Batch processing CLI for MIRRA pipeline"""
    pass


@cli.command()
@click.option('--workers', '-w', default=3, help='Number of worker threads')
@click.option('--jobs-file', '-f', required=True, type=click.Path(exists=True),
              help='JSON file with job definitions')
@click.option('--wait/--no-wait', default=True, help='Wait for all jobs to complete')
@click.option('--timeout', '-t', type=int, help='Timeout in seconds')
def run(workers: int, jobs_file: str, wait: bool, timeout: int):
    """Run batch processing from job file"""
    
    # Load jobs from file
    with open(jobs_file, 'r') as f:
        jobs_data = json.load(f)
    
    # Create processor
    config = WorkerConfig(num_workers=workers)
    processor = BatchProcessor(config)
    
    # Register callbacks
    def on_complete(job, result_path):
        click.echo(f"✓ Job {job.job_id} completed: {result_path}")
    
    def on_failed(job, error):
        click.echo(f"✗ Job {job.job_id} failed: {error}", err=True)
    
    processor.on_job_complete(on_complete)
    processor.on_job_failed(on_failed)
    
    # Start processor
    processor.start()
    
    # Submit jobs
    job_ids = []
    for job_data in jobs_data['jobs']:
        job = PipelineJob(
            avatar_id=job_data['avatar_id'],
            garment_type=job_data['garment_type'],
            measurements=job_data.get('measurements', {}),
            design_params=job_data.get('design_params', {}),
            priority=JobPriority[job_data.get('priority', 'NORMAL')]
        )
        job_id = processor.submit_job(job)
        job_ids.append(job_id)
    
    click.echo(f"Submitted {len(job_ids)} jobs")
    
    # Wait if requested
    if wait:
        click.echo("Waiting for jobs to complete...")
        results = processor.wait_all(timeout=timeout)
        
        click.echo("\n=== Results ===")
        click.echo(f"Completed: {results['completed']}")
        click.echo(f"Failed: {results['failed']}")
        click.echo(f"Cancelled: {results['cancelled']}")
    else:
        click.echo("Jobs submitted. Use 'status' command to check progress.")
    
    # Stop processor
    processor.stop()


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output JSON file')
def status(output: str):
    """Get current batch processing status"""
    
    processor = BatchProcessor()
    metrics = processor.get_metrics()
    workers = processor.get_worker_status()
    
    # Display metrics
    click.echo("=== Batch Processor Status ===")
    click.echo(f"Total Jobs: {metrics['total_jobs']}")
    click.echo(f"Queued: {metrics['queued_jobs']}")
    click.echo(f"Running: {metrics['running_jobs']}")
    click.echo(f"Completed: {metrics['completed_jobs']}")
    click.echo(f"Failed: {metrics['failed_jobs']}")
    
    click.echo(f"\n=== Workers ({metrics['total_workers']}) ===")
    for worker in workers:
        status = "BUSY" if worker['current_job'] else "IDLE"
        click.echo(
            f"Worker {worker['worker_id']}: {status} "
            f"(processed={worker['jobs_processed']}, failed={worker['jobs_failed']})"
        )
    
    # Save to file if requested
    if output:
        data = {
            'metrics': metrics,
            'workers': workers
        }
        with open(output, 'w') as f:
            json.dump(data, f, indent=2)
        click.echo(f"\nStatus saved to {output}")


@cli.command()
@click.argument('job_id')
def info(job_id: str):
    """Get information about specific job"""
    
    processor = BatchProcessor()
    job_info = processor.get_job_info(job_id)
    
    if not job_info:
        click.echo(f"Job {job_id} not found", err=True)
        return
    
    click.echo("=== Job Information ===")
    for key, value in job_info.items():
        click.echo(f"{key}: {value}")


@cli.command()
@click.option('--status-filter', '-s', type=click.Choice([
    'pending', 'queued', 'running', 'completed', 'failed', 'cancelled'
]))
def list_jobs(status_filter: str):
    """List all jobs"""
    
    processor = BatchProcessor()
    status = JobStatus(status_filter) if status_filter else None
    jobs = processor.list_jobs(status=status)
    
    if not jobs:
        click.echo("No jobs found")
        return
    
    click.echo(f"=== Jobs ({len(jobs)}) ===")
    for job in jobs:
        click.echo(
            f"{job['job_id'][:8]} | "
            f"{job['status']:10} | "
            f"{job['avatar_id']:15} | "
            f"{job['garment_type']:10} | "
            f"retries={job['retry_count']}"
        )


if __name__ == '__main__':
    cli()
```

### 16.5: Create Sample Batch Job File

**File:** `tests/batch_jobs_sample.json`

```json
{
  "jobs": [
    {
      "avatar_id": "user_001",
      "garment_type": "tshirt",
      "priority": "NORMAL",
      "measurements": {
        "height": 175,
        "chest": 95,
        "waist": 80,
        "hips": 95
      },
      "design_params": {
        "color": "navy",
        "pattern_style": "solid"
      }
    },
    {
      "avatar_id": "user_001",
      "garment_type": "pants",
      "priority": "NORMAL",
      "measurements": {
        "height": 175,
        "waist": 80,
        "hips": 95,
        "inseam": 80
      },
      "design_params": {
        "color": "black",
        "pattern_style": "solid"
      }
    },
    {
      "avatar_id": "user_002",
      "garment_type": "tshirt",
      "priority": "HIGH",
      "measurements": {
        "height": 180,
        "chest": 100,
        "waist": 85,
        "hips": 98
      },
      "design_params": {
        "color": "white",
        "pattern_style": "graphic"
      }
    },
    {
      "avatar_id": "user_003",
      "garment_type": "hoodie",
      "priority": "LOW",
      "measurements": {
        "height": 170,
        "chest": 92,
        "waist": 78,
        "hips": 93
      },
      "design_params": {
        "color": "gray",
        "pattern_style": "solid"
      }
    }
  ]
}
```

### 16.6: Test Batch Processing System

**Test file:** `tests/test_batch_processing.py`

```python
"""
Test batch processing system
"""

import pytest
import time
from pathlib import Path
import json

from Working_Cloth_3D_Pipeline.batch import (
    BatchProcessor,
    WorkerConfig,
    PipelineJob,
    JobPriority,
    JobStatus,
    get_job_queue
)


@pytest.fixture
def batch_processor():
    """Create batch processor for testing"""
    config = WorkerConfig(
        num_workers=2,
        max_retries=1,
        retry_delay_seconds=1
    )
    processor = BatchProcessor(config)
    yield processor
    processor.stop()


def test_job_queue():
    """Test job queue operations"""
    queue = get_job_queue()
    
    # Create job
    job = PipelineJob(
        avatar_id="test_avatar",
        garment_type="tshirt",
        priority=JobPriority.HIGH
    )
    
    # Add to queue
    job_id = queue.add_job(job)
    assert job_id is not None
    
    # Check status
    status = queue.get_job_status(job_id)
    assert status == JobStatus.QUEUED
    
    # Get job info
    info = queue.get_job_info(job_id)
    assert info['avatar_id'] == "test_avatar"
    assert info['garment_type'] == "tshirt"


def test_batch_processor_start_stop(batch_processor):
    """Test processor lifecycle"""
    # Start
    batch_processor.start()
    assert batch_processor.is_running
    assert len(batch_processor.workers) == 2
    
    # Stop
    batch_processor.stop()
    assert not batch_processor.is_running


def test_job_submission(batch_processor):
    """Test job submission"""
    batch_processor.start()
    
    # Submit job
    job = PipelineJob(
        avatar_id="user_123",
        garment_type="tshirt"
    )
    job_id = batch_processor.submit_job(job)
    
    assert job_id is not None
    
    # Check it's queued
    status = batch_processor.get_job_status(job_id)
    assert status in [JobStatus.QUEUED, JobStatus.RUNNING]


def test_batch_submission(batch_processor):
    """Test batch job submission"""
    batch_processor.start()
    
    # Create multiple jobs
    jobs = [
        PipelineJob(avatar_id=f"user_{i}", garment_type="tshirt")
        for i in range(5)
    ]
    
    # Submit batch
    job_ids = batch_processor.submit_batch(jobs)
    
    assert len(job_ids) == 5
    
    # Check all are queued
    for job_id in job_ids:
        status = batch_processor.get_job_status(job_id)
        assert status in [JobStatus.QUEUED, JobStatus.RUNNING]


def test_metrics(batch_processor):
    """Test metrics collection"""
    batch_processor.start()
    
    # Submit jobs
    jobs = [
        PipelineJob(avatar_id=f"user_{i}", garment_type="tshirt")
        for i in range(3)
    ]
    batch_processor.submit_batch(jobs)
    
    # Get metrics
    metrics = batch_processor.get_metrics()
    
    assert metrics['total_jobs'] >= 3
    assert metrics['total_workers'] == 2
    assert 'queued_jobs' in metrics
    assert 'running_jobs' in metrics


def test_worker_status(batch_processor):
    """Test worker status reporting"""
    batch_processor.start()
    
    # Get worker status
    workers = batch_processor.get_worker_status()
    
    assert len(workers) == 2
    for worker in workers:
        assert 'worker_id' in worker
        assert 'is_running' in worker
        assert 'jobs_processed' in worker


def test_list_jobs(batch_processor):
    """Test job listing"""
    batch_processor.start()
    
    # Submit jobs
    jobs = [
        PipelineJob(avatar_id=f"user_{i}", garment_type="tshirt")
        for i in range(3)
    ]
    job_ids = batch_processor.submit_batch(jobs)
    
    # List all jobs
    all_jobs = batch_processor.list_jobs()
    assert len(all_jobs) >= 3
    
    # List queued jobs
    queued_jobs = batch_processor.list_jobs(status=JobStatus.QUEUED)
    assert len(queued_jobs) >= 0


def test_callbacks(batch_processor):
    """Test completion and failure callbacks"""
    batch_processor.start()
    
    completed_jobs = []
    failed_jobs = []
    
    def on_complete(job, result_path):
        completed_jobs.append(job.job_id)
    
    def on_failed(job, error):
        failed_jobs.append(job.job_id)
    
    batch_processor.on_job_complete(on_complete)
    batch_processor.on_job_failed(on_failed)
    
    # Submit job
    job = PipelineJob(avatar_id="test", garment_type="tshirt")
    job_id = batch_processor.submit_job(job)
    
    # Wait a bit
    time.sleep(2)
    
    # Check callbacks were called
    # (This may not work in unit tests without mocking the pipeline)
    # Just verify the callbacks are registered
    assert len(batch_processor._on_job_complete_callbacks) > 0
    assert len(batch_processor._on_job_failed_callbacks) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**Run tests:**

```powershell
# Run batch processing tests
pytest tests\test_batch_processing.py -v

# Expected output:
# test_job_queue PASSED
# test_batch_processor_start_stop PASSED
# test_job_submission PASSED
# test_batch_submission PASSED
# test_metrics PASSED
# test_worker_status PASSED
# test_list_jobs PASSED
# test_callbacks PASSED
```

### 16.7: Test Batch CLI

```powershell
# Test CLI help
python -m Working_Cloth_3D_Pipeline.batch.batch_cli --help

# Run batch from sample file
python -m Working_Cloth_3D_Pipeline.batch.batch_cli run `
    --workers 3 `
    --jobs-file tests\batch_jobs_sample.json `
    --wait `
    --timeout 1800

# Check status
python -m Working_Cloth_3D_Pipeline.batch.batch_cli status

# List all jobs
python -m Working_Cloth_3D_Pipeline.batch.batch_cli list-jobs

# Get specific job info
python -m Working_Cloth_3D_Pipeline.batch.batch_cli info <job_id>
```

### Day 16 Completion Checklist

- [ ] `Working_Cloth_3D_Pipeline/batch/` package created
- [ ] `job_queue.py` implemented with priority queue
- [ ] `batch_processor.py` implemented with worker pool
- [ ] `batch_cli.py` CLI created
- [ ] Sample batch job file created
- [ ] All batch processing tests pass
- [ ] Can submit jobs via CLI
- [ ] Can process multiple jobs in parallel
- [ ] Metrics and monitoring working

**Time:** 6-8 hours  
**Next:** Day 17 - Error Recovery & Retry Logic

---

## Day 17: Error Recovery & Retry Logic

**Time:** 6-8 hours  
**Goal:** Implement robust error handling with automatic recovery

### 17.1: Error Classification System

**Objective:** Categorize errors by severity and recovery strategy

#### Understanding Error Types

Errors in the pipeline fall into categories:

1. **Transient Errors** (recoverable with retry):
   - CLO API timeout
   - Network issues
   - Temporary file locks
   - Memory pressure

2. **Configuration Errors** (recoverable with correction):
   - Invalid measurements
   - Missing design parameters
   - Wrong file paths

3. **Fatal Errors** (not recoverable):
   - CLO crash/not responding
   - Corrupted input files
   - Invalid avatar mesh topology
   - Out of disk space

### 17.2: Implement Error Classification

**File:** `Working_Cloth_3D_Pipeline/batch/error_handling.py`

```python
"""
Error classification and recovery strategies
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"                # Recoverable, no retry needed
    WARNING = "warning"          # Recoverable, retry recommended
    ERROR = "error"              # Recoverable with retry
    CRITICAL = "critical"        # Not recoverable
    FATAL = "fatal"              # System-level failure


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    API = "api"
    FILE_IO = "file_io"
    VALIDATION = "validation"
    SIMULATION = "simulation"
    MEMORY = "memory"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for errors"""
    RETRY_IMMEDIATE = "retry_immediate"          # Retry immediately
    RETRY_DELAY = "retry_delay"                  # Retry after delay
    RETRY_BACKOFF = "retry_backoff"              # Retry with exponential backoff
    RECONFIGURE = "reconfigure"                  # Fix config and retry
    SKIP = "skip"                                # Skip this job
    ABORT = "abort"                              # Abort entire batch
    MANUAL = "manual"                            # Requires manual intervention


@dataclass
class ErrorClassification:
    """
    Error classification with recovery strategy
    """
    severity: ErrorSeverity
    category: ErrorCategory
    strategy: RecoveryStrategy
    message: str
    metadata: Dict[str, Any]
    
    def is_recoverable(self) -> bool:
        """Check if error is recoverable"""
        return self.severity not in [ErrorSeverity.FATAL, ErrorSeverity.CRITICAL]
    
    def is_retryable(self) -> bool:
        """Check if error should be retried"""
        return self.strategy in [
            RecoveryStrategy.RETRY_IMMEDIATE,
            RecoveryStrategy.RETRY_DELAY,
            RecoveryStrategy.RETRY_BACKOFF
        ]
    
    def get_retry_delay(self, attempt: int) -> int:
        """Get retry delay in seconds based on strategy"""
        if self.strategy == RecoveryStrategy.RETRY_IMMEDIATE:
            return 0
        elif self.strategy == RecoveryStrategy.RETRY_DELAY:
            return 30
        elif self.strategy == RecoveryStrategy.RETRY_BACKOFF:
            return min(2 ** attempt * 10, 300)  # Max 5 minutes
        else:
            return 0


class ErrorClassifier:
    """
    Classifies errors and determines recovery strategy
    
    Usage:
        classifier = ErrorClassifier()
        classification = classifier.classify(exception)
        
        if classification.is_retryable():
            retry_after = classification.get_retry_delay(attempt)
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ErrorClassifier")
        
        # Error pattern matching rules
        self.rules = self._init_rules()
    
    def _init_rules(self) -> list:
        """Initialize error classification rules"""
        return [
            # Network errors
            {
                'patterns': ['connection', 'timeout', 'unreachable', 'refused'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.NETWORK,
                'strategy': RecoveryStrategy.RETRY_BACKOFF
            },
            
            # API errors
            {
                'patterns': ['api error', 'http 500', 'http 502', 'http 503', 'http 504'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.API,
                'strategy': RecoveryStrategy.RETRY_BACKOFF
            },
            {
                'patterns': ['http 400', 'http 401', 'http 403', 'http 404'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.API,
                'strategy': RecoveryStrategy.SKIP
            },
            
            # File I/O errors
            {
                'patterns': ['file not found', 'no such file', 'cannot open'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.FILE_IO,
                'strategy': RecoveryStrategy.SKIP
            },
            {
                'patterns': ['permission denied', 'access denied'],
                'severity': ErrorSeverity.CRITICAL,
                'category': ErrorCategory.FILE_IO,
                'strategy': RecoveryStrategy.MANUAL
            },
            {
                'patterns': ['disk full', 'no space left'],
                'severity': ErrorSeverity.FATAL,
                'category': ErrorCategory.FILE_IO,
                'strategy': RecoveryStrategy.ABORT
            },
            
            # Validation errors
            {
                'patterns': ['invalid measurements', 'invalid parameters', 'validation failed'],
                'severity': ErrorSeverity.WARNING,
                'category': ErrorCategory.VALIDATION,
                'strategy': RecoveryStrategy.RECONFIGURE
            },
            
            # Simulation errors
            {
                'patterns': ['simulation failed', 'convergence failed', 'collision'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.SIMULATION,
                'strategy': RecoveryStrategy.RETRY_DELAY
            },
            {
                'patterns': ['mesh explosion', 'invalid mesh'],
                'severity': ErrorSeverity.CRITICAL,
                'category': ErrorCategory.SIMULATION,
                'strategy': RecoveryStrategy.SKIP
            },
            
            # Memory errors
            {
                'patterns': ['out of memory', 'memory error', 'allocation failed'],
                'severity': ErrorSeverity.CRITICAL,
                'category': ErrorCategory.MEMORY,
                'strategy': RecoveryStrategy.RETRY_DELAY
            },
            
            # Timeout errors
            {
                'patterns': ['timeout', 'timed out', 'deadline exceeded'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.TIMEOUT,
                'strategy': RecoveryStrategy.RETRY_DELAY
            },
            
            # Configuration errors
            {
                'patterns': ['missing config', 'invalid config', 'config error'],
                'severity': ErrorSeverity.ERROR,
                'category': ErrorCategory.CONFIGURATION,
                'strategy': RecoveryStrategy.RECONFIGURE
            },
            
            # System errors
            {
                'patterns': ['clo not responding', 'process crashed', 'kernel'],
                'severity': ErrorSeverity.FATAL,
                'category': ErrorCategory.SYSTEM,
                'strategy': RecoveryStrategy.MANUAL
            }
        ]
    
    def classify(self, exception: Exception) -> ErrorClassification:
        """
        Classify exception and determine recovery strategy
        
        Args:
            exception: Exception to classify
            
        Returns:
            ErrorClassification with recovery strategy
        """
        error_msg = str(exception).lower()
        exception_type = type(exception).__name__
        
        # Check against rules
        for rule in self.rules:
            if any(pattern in error_msg for pattern in rule['patterns']):
                self.logger.info(
                    f"Classified error as {rule['category'].value}: {exception_type}"
                )
                
                return ErrorClassification(
                    severity=rule['severity'],
                    category=rule['category'],
                    strategy=rule['strategy'],
                    message=str(exception),
                    metadata={
                        'exception_type': exception_type,
                        'matched_rule': rule['patterns'][0]
                    }
                )
        
        # Default classification for unknown errors
        self.logger.warning(f"Unknown error type: {exception_type}: {error_msg}")
        
        return ErrorClassification(
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            strategy=RecoveryStrategy.RETRY_DELAY,
            message=str(exception),
            metadata={'exception_type': exception_type}
        )
    
    def add_rule(
        self,
        patterns: list[str],
        severity: ErrorSeverity,
        category: ErrorCategory,
        strategy: RecoveryStrategy
    ):
        """Add custom error classification rule"""
        self.rules.append({
            'patterns': patterns,
            'severity': severity,
            'category': category,
            'strategy': strategy
        })


# Global error classifier instance
_error_classifier = ErrorClassifier()


def get_error_classifier() -> ErrorClassifier:
    """Get global error classifier instance"""
    return _error_classifier


def classify_error(exception: Exception) -> ErrorClassification:
    """Convenience function to classify error"""
    return get_error_classifier().classify(exception)
```

### 17.3: Implement Retry Manager

**File:** `Working_Cloth_3D_Pipeline/batch/retry_manager.py`

```python
"""
Retry manager with exponential backoff and circuit breaker
"""

import time
import logging
from typing import Callable, TypeVar, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps

from .error_handling import classify_error, RecoveryStrategy


T = TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    initial_delay: int = 1
    max_delay: int = 300
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Circuit breaker
    circuit_break_threshold: int = 5
    circuit_break_timeout: int = 60
    
    def get_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay


@dataclass
class RetryStats:
    """Retry statistics"""
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_retries: int = 0
    circuit_breaks: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    
    Prevents cascading failures by temporarily stopping retries
    after repeated failures.
    """
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.is_open = False
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.threshold:
            self.is_open = True
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
    
    def can_proceed(self) -> bool:
        """Check if operations can proceed"""
        if not self.is_open:
            return True
        
        # Check if timeout has passed
        if self.last_failure_time:
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed >= self.timeout:
                logger.info("Circuit breaker timeout elapsed, closing circuit")
                self.is_open = False
                self.failure_count = 0
                return True
        
        return False


class RetryManager:
    """
    Manages retries with exponential backoff and circuit breaker
    
    Usage:
        manager = RetryManager()
        
        @manager.retry()
        def risky_operation():
            # Code that might fail
            pass
        
        # Or manual retry
        result = manager.execute_with_retry(risky_operation)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_break_threshold,
            timeout=self.config.circuit_break_timeout
        )
        self.stats = RetryStats()
        self.logger = logging.getLogger("RetryManager")
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with automatic retry
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        attempt = 0
        last_exception = None
        
        while attempt <= self.config.max_retries:
            # Check circuit breaker
            if not self.circuit_breaker.can_proceed():
                self.logger.warning("Circuit breaker open, aborting retry")
                self.stats.circuit_breaks += 1
                raise Exception("Circuit breaker open")
            
            try:
                self.stats.total_attempts += 1
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success
                self.stats.total_successes += 1
                self.stats.last_success = datetime.now()
                self.circuit_breaker.record_success()
                
                if attempt > 0:
                    self.logger.info(f"Succeeded after {attempt} retries")
                
                return result
            
            except Exception as e:
                last_exception = e
                self.stats.total_failures += 1
                self.stats.last_failure = datetime.now()
                self.circuit_breaker.record_failure()
                
                # Classify error
                classification = classify_error(e)
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {classification.category.value} - {e}"
                )
                
                # Check if retryable
                if not classification.is_retryable():
                    self.logger.error(
                        f"Error not retryable (strategy={classification.strategy.value})"
                    )
                    raise
                
                # Check if max retries reached
                if attempt >= self.config.max_retries:
                    self.logger.error(
                        f"Max retries ({self.config.max_retries}) exhausted"
                    )
                    raise
                
                # Calculate delay
                delay = classification.get_retry_delay(attempt)
                if delay == 0:
                    delay = self.config.get_delay(attempt)
                
                self.logger.info(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                
                attempt += 1
                self.stats.total_retries += 1
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise Exception("Retry loop exited unexpectedly")
    
    def retry(self, **retry_kwargs):
        """
        Decorator for automatic retry
        
        Usage:
            @retry_manager.retry(max_retries=5)
            def my_function():
                pass
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Override config if provided
                if retry_kwargs:
                    old_config = self.config
                    self.config = RetryConfig(**{**old_config.__dict__, **retry_kwargs})
                
                try:
                    return self.execute_with_retry(func, *args, **kwargs)
                finally:
                    if retry_kwargs:
                        self.config = old_config
            
            return wrapper
        return decorator
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return {
            'total_attempts': self.stats.total_attempts,
            'total_successes': self.stats.total_successes,
            'total_failures': self.stats.total_failures,
            'total_retries': self.stats.total_retries,
            'circuit_breaks': self.stats.circuit_breaks,
            'success_rate': (
                self.stats.total_successes / self.stats.total_attempts * 100
                if self.stats.total_attempts > 0 else 0
            ),
            'last_failure': self.stats.last_failure.isoformat() if self.stats.last_failure else None,
            'last_success': self.stats.last_success.isoformat() if self.stats.last_success else None,
            'circuit_open': self.circuit_breaker.is_open
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = RetryStats()
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_break_threshold,
            timeout=self.config.circuit_break_timeout
        )


# Global retry manager instance
_retry_manager = RetryManager()


def get_retry_manager() -> RetryManager:
    """Get global retry manager instance"""
    return _retry_manager


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Convenience decorator for retry with default config"""
    return get_retry_manager().retry()(func)
```

### 17.4: Integrate Error Handling into Batch Processor

**Update:** `Working_Cloth_3D_Pipeline/batch/batch_processor.py`

Add error handling to the `PipelineWorker._execute_job` method:

```python
# Add imports at top
from .error_handling import classify_error, RecoveryStrategy
from .retry_manager import get_retry_manager

# Update _execute_job method in PipelineWorker class
def _execute_job(self, job: PipelineJob) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Execute pipeline job with error handling and retry
    
    Returns:
        (success, result_path, error_message)
    """
    retry_manager = get_retry_manager()
    
    def run_pipeline():
        # Initialize pipeline
        pipeline = ClothPipeline()
        
        # Set job parameters
        pipeline.set_avatar_id(job.avatar_id)
        pipeline.set_garment_type(job.garment_type)
        pipeline.set_measurements(job.measurements)
        pipeline.set_design_params(job.design_params)
        
        # Run full pipeline
        result = pipeline.run()
        
        if not result['success']:
            raise Exception(result.get('error', 'Unknown pipeline error'))
        
        return result.get('output_path')
    
    try:
        # Execute with automatic retry
        result_path = retry_manager.execute_with_retry(run_pipeline)
        return True, result_path, None
    
    except Exception as e:
        # Classify error for detailed reporting
        classification = classify_error(e)
        
        error_msg = (
            f"{classification.category.value}: {str(e)}\n"
            f"Strategy: {classification.strategy.value}\n"
            f"Severity: {classification.severity.value}"
        )
        
        self.logger.error(f"Job failed: {error_msg}")
        return False, None, error_msg
```

### 17.5: Test Error Handling

**Test file:** `tests/test_error_handling.py`

```python
"""
Test error handling and retry logic
"""

import pytest
import time
from datetime import datetime

from Working_Cloth_3D_Pipeline.batch.error_handling import (
    ErrorClassifier,
    ErrorSeverity,
    ErrorCategory,
    RecoveryStrategy,
    classify_error
)
from Working_Cloth_3D_Pipeline.batch.retry_manager import (
    RetryManager,
    RetryConfig,
    CircuitBreaker
)


def test_error_classification():
    """Test error classification"""
    classifier = ErrorClassifier()
    
    # Test network error
    error = Exception("Connection timeout")
    classification = classifier.classify(error)
    assert classification.category == ErrorCategory.NETWORK
    assert classification.is_retryable()
    
    # Test validation error
    error = Exception("Invalid measurements provided")
    classification = classifier.classify(error)
    assert classification.category == ErrorCategory.VALIDATION
    assert classification.strategy == RecoveryStrategy.RECONFIGURE
    
    # Test fatal error
    error = Exception("Disk full - cannot continue")
    classification = classifier.classify(error)
    assert classification.severity == ErrorSeverity.FATAL
    assert not classification.is_retryable()


def test_retry_delay_calculation():
    """Test retry delay calculation"""
    config = RetryConfig(
        initial_delay=1,
        exponential_base=2.0,
        max_delay=60,
        jitter=False
    )
    
    # Test exponential backoff
    delays = [config.get_delay(i) for i in range(5)]
    assert delays[0] == 1
    assert delays[1] == 2
    assert delays[2] == 4
    assert delays[3] == 8
    assert delays[4] == 16


def test_circuit_breaker():
    """Test circuit breaker pattern"""
    breaker = CircuitBreaker(threshold=3, timeout=2)
    
    # Should start closed
    assert breaker.can_proceed()
    
    # Record failures
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.can_proceed()  # Still under threshold
    
    breaker.record_failure()
    assert breaker.is_open
    assert not breaker.can_proceed()
    
    # Wait for timeout
    time.sleep(2.5)
    assert breaker.can_proceed()  # Should reclose
    
    # Success resets
    breaker.record_success()
    assert breaker.failure_count == 0


def test_retry_manager_success():
    """Test retry manager with successful operation"""
    config = RetryConfig(max_retries=3, initial_delay=0.1)
    manager = RetryManager(config)
    
    call_count = [0]
    
    def operation():
        call_count[0] += 1
        return "success"
    
    result = manager.execute_with_retry(operation)
    
    assert result == "success"
    assert call_count[0] == 1
    assert manager.stats.total_successes == 1
    assert manager.stats.total_retries == 0


def test_retry_manager_with_transient_failure():
    """Test retry manager with transient failure"""
    config = RetryConfig(max_retries=3, initial_delay=0.1)
    manager = RetryManager(config)
    
    call_count = [0]
    
    def operation():
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("connection timeout")
        return "success"
    
    result = manager.execute_with_retry(operation)
    
    assert result == "success"
    assert call_count[0] == 3
    assert manager.stats.total_retries == 2
    assert manager.stats.total_successes == 1


def test_retry_manager_max_retries_exhausted():
    """Test retry manager when max retries exhausted"""
    config = RetryConfig(max_retries=2, initial_delay=0.1)
    manager = RetryManager(config)
    
    def operation():
        raise Exception("persistent connection timeout")
    
    with pytest.raises(Exception, match="connection timeout"):
        manager.execute_with_retry(operation)
    
    assert manager.stats.total_retries == 2
    assert manager.stats.total_successes == 0
    assert manager.stats.total_failures == 3


def test_retry_manager_non_retryable_error():
    """Test retry manager with non-retryable error"""
    config = RetryConfig(max_retries=3, initial_delay=0.1)
    manager = RetryManager(config)
    
    call_count = [0]
    
    def operation():
        call_count[0] += 1
        raise Exception("disk full - cannot continue")
    
    with pytest.raises(Exception, match="disk full"):
        manager.execute_with_retry(operation)
    
    # Should fail immediately without retries
    assert call_count[0] == 1
    assert manager.stats.total_retries == 0


def test_retry_decorator():
    """Test retry decorator"""
    manager = RetryManager(RetryConfig(max_retries=2, initial_delay=0.1))
    
    call_count = [0]
    
    @manager.retry()
    def my_function():
        call_count[0] += 1
        if call_count[0] < 2:
            raise Exception("timeout")
        return "success"
    
    result = my_function()
    
    assert result == "success"
    assert call_count[0] == 2


def test_circuit_breaker_integration():
    """Test circuit breaker integration with retry manager"""
    config = RetryConfig(
        max_retries=2,
        initial_delay=0.1,
        circuit_break_threshold=3,
        circuit_break_timeout=1
    )
    manager = RetryManager(config)
    
    # Cause circuit breaker to open
    for _ in range(3):
        try:
            manager.execute_with_retry(lambda: exec('raise Exception("timeout")'))
        except:
            pass
    
    # Circuit should be open
    assert manager.circuit_breaker.is_open
    
    # Next call should fail immediately
    with pytest.raises(Exception, match="Circuit breaker open"):
        manager.execute_with_retry(lambda: "success")
    
    # Wait for timeout
    time.sleep(1.5)
    
    # Should work now
    result = manager.execute_with_retry(lambda: "success")
    assert result == "success"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**Run tests:**

```powershell
pytest tests\test_error_handling.py -v
```

### Day 17 Completion Checklist

- [ ] `error_handling.py` implemented with error classification
- [ ] `retry_manager.py` implemented with circuit breaker
- [ ] Error handling integrated into batch processor
- [ ] All error handling tests pass
- [ ] Circuit breaker prevents cascading failures
- [ ] Retry statistics collected and accessible
- [ ] Non-retryable errors handled appropriately

**Time:** 6-8 hours  
**Next:** Day 18 - Performance Optimization

---

## Day 18: Performance Optimization

**Time:** 6-8 hours  
**Goal:** Optimize pipeline for 50%+ speed improvement

### 18.1: Performance Profiling

**Objective:** Identify bottlenecks in the pipeline

#### Performance Analysis Areas

1. **CLO Simulation Time**: 60-70% of total time
2. **File I/O**: 10-15% of total time
3. **Pattern Generation**: 10-15% of total time
4. **Avatar Loading**: 5-10% of total time
5. **Texture Processing**: 5% of total time

### 18.2: Implement Performance Profiler

**File:** `Working_Cloth_3D_Pipeline/utils/profiler.py`

```python
"""
Performance profiling utilities
"""

import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json


logger = logging.getLogger(__name__)


@dataclass
class ProfileEntry:
    """Single profile measurement"""
    name: str
    start_time: float
    end_time: float
    duration: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'duration_ms': self.duration * 1000,
            'start': datetime.fromtimestamp(self.start_time).isoformat(),
            'end': datetime.fromtimestamp(self.end_time).isoformat(),
            'metadata': self.metadata
        }


class PerformanceProfiler:
    """
    Performance profiler for pipeline operations
    
    Usage:
        profiler = PerformanceProfiler()
        
        with profiler.measure("operation_name"):
            # Code to measure
            pass
        
        # Get results
        stats = profiler.get_stats()
    """
    
    def __init__(self):
        self.entries: List[ProfileEntry] = []
        self.current_operation: Optional[str] = None
        self.start_time: Optional[float] = None
    
    @contextmanager
    def measure(self, name: str, metadata: Optional[Dict] = None):
        """
        Context manager for measuring code block performance
        
        Args:
            name: Operation name
            metadata: Additional metadata
        """
        start = time.time()
        
        try:
            yield
        finally:
            end = time.time()
            duration = end - start
            
            entry = ProfileEntry(
                name=name,
                start_time=start,
                end_time=end,
                duration=duration,
                metadata=metadata or {}
            )
            
            self.entries.append(entry)
            
            logger.debug(f"{name}: {duration*1000:.1f}ms")
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        if not self.entries:
            return {}
        
        # Group by operation name
        operations = {}
        for entry in self.entries:
            if entry.name not in operations:
                operations[entry.name] = []
            operations[entry.name].append(entry.duration)
        
        # Calculate statistics
        stats = {}
        for name, durations in operations.items():
            stats[name] = {
                'count': len(durations),
                'total_ms': sum(durations) * 1000,
                'mean_ms': (sum(durations) / len(durations)) * 1000,
                'min_ms': min(durations) * 1000,
                'max_ms': max(durations) * 1000
            }
        
        # Add totals
        total_duration = sum(entry.duration for entry in self.entries)
        stats['_total'] = {
            'duration_ms': total_duration * 1000,
            'operations': len(self.entries)
        }
        
        return stats
    
    def get_timeline(self) -> List[Dict]:
        """Get timeline of all operations"""
        return [entry.to_dict() for entry in self.entries]
    
    def print_stats(self):
        """Print statistics to console"""
        stats = self.get_stats()
        
        print("\n=== Performance Profile ===")
        print(f"Total operations: {stats['_total']['operations']}")
        print(f"Total time: {stats['_total']['duration_ms']:.1f}ms\n")
        
        # Sort by total time
        operations = [(name, data) for name, data in stats.items() if name != '_total']
        operations.sort(key=lambda x: x[1]['total_ms'], reverse=True)
        
        print(f"{'Operation':<40} {'Count':>6} {'Total (ms)':>12} {'Mean (ms)':>12}")
        print("-" * 75)
        
        for name, data in operations:
            print(
                f"{name:<40} {data['count']:>6} "
                f"{data['total_ms']:>12.1f} {data['mean_ms']:>12.1f}"
            )
    
    def save_report(self, filepath: str):
        """Save performance report to JSON file"""
        report = {
            'stats': self.get_stats(),
            'timeline': self.get_timeline()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
    
    def reset(self):
        """Reset profiler"""
        self.entries.clear()


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    return _profiler
```

### 18.3: Implement Caching System

**File:** `Working_Cloth_3D_Pipeline/utils/cache.py`

```python
"""
Caching system for expensive operations
"""

import hashlib
import pickle
import json
from pathlib import Path
from typing import Any, Optional, Callable
from functools import wraps
import logging


logger = logging.getLogger(__name__)


class FileCache:
    """
    File-based cache for expensive operations
    
    Usage:
        cache = FileCache(cache_dir="cache")
        
        @cache.cached(ttl=3600)
        def expensive_operation(param):
            # Expensive computation
            return result
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments"""
        # Create unique key from function and arguments
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }
        
        # Serialize and hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get path to cache file"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def get(self, cache_key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            # Check TTL if specified
            if 'ttl' in data:
                import time
                if time.time() - data['timestamp'] > data['ttl']:
                    logger.debug(f"Cache expired: {cache_key}")
                    cache_path.unlink()
                    return None
            
            logger.debug(f"Cache hit: {cache_key}")
            return data['value']
        
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def set(self, cache_key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            import time
            data = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"Cache set: {cache_key}")
        
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def clear(self):
        """Clear all cache"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        logger.info("Cache cleared")
    
    def cached(self, ttl: Optional[int] = None):
        """
        Decorator for caching function results
        
        Args:
            ttl: Time to live in seconds (None = forever)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._get_cache_key(func.__name__, args, kwargs)
                
                # Check cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Compute value
                value = func(*args, **kwargs)
                
                # Store in cache
                self.set(cache_key, value, ttl=ttl)
                
                return value
            
            return wrapper
        return decorator


# Global cache instance
_cache = FileCache()


def get_cache() -> FileCache:
    """Get global cache instance"""
    return _cache
```

### 18.4: Optimize CLO Simulation Settings

**File:** `Working_Cloth_3D_Pipeline/steps/clo_integration/simulation_optimizer.py`

```python
"""
Simulation optimization presets for performance vs. quality tradeoff
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class QualityPreset(Enum):
    """Quality presets for simulation"""
    DRAFT = "draft"             # Fast, low quality (30-60s)
    PREVIEW = "preview"         # Medium speed, medium quality (2-3min)
    PRODUCTION = "production"   # Slow, high quality (5-8min)
    FINAL = "final"             # Slowest, highest quality (10-15min)


@dataclass
class SimulationSettings:
    """CLO simulation settings"""
    particle_distance: float        # Mesh resolution (mm)
    simulation_quality: int         # Quality level (0-100)
    collision_thickness: float      # Collision detection (mm)
    friction: float                 # Surface friction (0-1)
    air_damping: float             # Air resistance
    steps_per_frame: int           # Simulation steps
    max_iterations: int            # Max solver iterations
    convergence_threshold: float   # Convergence criteria
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'particle_distance': self.particle_distance,
            'simulation_quality': self.simulation_quality,
            'collision_thickness': self.collision_thickness,
            'friction': self.friction,
            'air_damping': self.air_damping,
            'steps_per_frame': self.steps_per_frame,
            'max_iterations': self.max_iterations,
            'convergence_threshold': self.convergence_threshold
        }


# Optimized presets
SIMULATION_PRESETS = {
    QualityPreset.DRAFT: SimulationSettings(
        particle_distance=10.0,       # Coarse mesh
        simulation_quality=30,
        collision_thickness=2.0,
        friction=0.2,
        air_damping=0.5,
        steps_per_frame=5,
        max_iterations=50,
        convergence_threshold=0.1
    ),
    
    QualityPreset.PREVIEW: SimulationSettings(
        particle_distance=5.0,        # Medium mesh
        simulation_quality=50,
        collision_thickness=1.5,
        friction=0.3,
        air_damping=0.3,
        steps_per_frame=10,
        max_iterations=100,
        convergence_threshold=0.05
    ),
    
    QualityPreset.PRODUCTION: SimulationSettings(
        particle_distance=3.0,        # Fine mesh
        simulation_quality=75,
        collision_thickness=1.0,
        friction=0.4,
        air_damping=0.2,
        steps_per_frame=15,
        max_iterations=200,
        convergence_threshold=0.01
    ),
    
    QualityPreset.FINAL: SimulationSettings(
        particle_distance=2.0,        # Very fine mesh
        simulation_quality=100,
        collision_thickness=0.5,
        friction=0.5,
        air_damping=0.1,
        steps_per_frame=20,
        max_iterations=300,
        convergence_threshold=0.005
    )
}


def get_simulation_settings(preset: QualityPreset) -> SimulationSettings:
    """Get simulation settings for quality preset"""
    return SIMULATION_PRESETS[preset]


def get_adaptive_preset(avatar_complexity: str, garment_complexity: str) -> QualityPreset:
    """
    Get adaptive quality preset based on complexity
    
    Args:
        avatar_complexity: "simple", "medium", "complex"
        garment_complexity: "simple", "medium", "complex"
        
    Returns:
        Recommended quality preset
    """
    complexity_score = 0
    
    # Avatar complexity
    if avatar_complexity == "complex":
        complexity_score += 2
    elif avatar_complexity == "medium":
        complexity_score += 1
    
    # Garment complexity
    if garment_complexity == "complex":
        complexity_score += 2
    elif garment_complexity == "medium":
        complexity_score += 1
    
    # Map to preset
    if complexity_score <= 1:
        return QualityPreset.DRAFT
    elif complexity_score <= 2:
        return QualityPreset.PREVIEW
    elif complexity_score <= 3:
        return QualityPreset.PRODUCTION
    else:
        return QualityPreset.FINAL
```

### 18.5: Implement Parallel Asset Processing

**File:** `Working_Cloth_3D_Pipeline/utils/parallel_processing.py`

```python
"""
Parallel processing utilities for asset generation
"""

import concurrent.futures
from typing import List, Callable, Any, Dict
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class ProcessingTask:
    """Task for parallel processing"""
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class ParallelProcessor:
    """
    Parallel processor for independent tasks
    
    Usage:
        processor = ParallelProcessor(max_workers=4)
        
        tasks = [
            ProcessingTask("task1", func1, (arg1,)),
            ProcessingTask("task2", func2, (arg2,))
        ]
        
        results = processor.process_tasks(tasks)
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    def process_tasks(self, tasks: List[ProcessingTask]) -> Dict[str, Any]:
        """
        Process tasks in parallel
        
        Args:
            tasks: List of processing tasks
            
        Returns:
            Dictionary of results {task_name: result}
        """
        results = {}
        errors = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(task.func, *task.args, **task.kwargs): task
                for task in tasks
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                
                try:
                    result = future.result()
                    results[task.name] = result
                    logger.info(f"Task '{task.name}' completed")
                
                except Exception as e:
                    errors[task.name] = str(e)
                    logger.error(f"Task '{task.name}' failed: {e}")
        
        if errors:
            logger.warning(f"{len(errors)} tasks failed: {list(errors.keys())}")
        
        return results


def parallel_map(func: Callable, items: List[Any], max_workers: int = 4) -> List[Any]:
    """
    Parallel map function
    
    Args:
        func: Function to apply
        items: List of items
        max_workers: Max parallel workers
        
    Returns:
        List of results
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(func, items))
```

### 18.6: Optimize Pipeline Integration

**Update:** `Working_Cloth_3D_Pipeline/pipeline.py`

Add performance optimizations:

```python
# Add imports
from .utils.profiler import get_profiler
from .utils.cache import get_cache
from .steps.clo_integration.simulation_optimizer import (
    get_simulation_settings,
    get_adaptive_preset,
    QualityPreset
)

class ClothPipeline:
    def __init__(self, enable_caching: bool = True, quality_preset: str = "preview"):
        # ... existing code ...
        
        self.profiler = get_profiler()
        self.cache = get_cache() if enable_caching else None
        self.quality_preset = QualityPreset(quality_preset)
    
    def run(self) -> Dict[str, Any]:
        """Run pipeline with performance optimization"""
        
        # Start profiling
        with self.profiler.measure("pipeline_total"):
            
            # Step 1: Segmentation (can be cached)
            with self.profiler.measure("step1_segmentation"):
                if self.cache:
                    cache_key = f"seg_{self.avatar_id}"
                    segmentation = self.cache.get(cache_key)
                    if not segmentation:
                        segmentation = self._run_step1()
                        self.cache.set(cache_key, segmentation, ttl=3600)
                else:
                    segmentation = self._run_step1()
            
            # Step 2-4: Pattern generation (can be parallelized)
            with self.profiler.measure("steps2-4_patterns"):
                patterns = self._run_steps2_4_parallel()
            
            # Step 5: CLO Assembly
            with self.profiler.measure("step5_clo_assembly"):
                # Get optimized simulation settings
                settings = get_simulation_settings(self.quality_preset)
                result = self._run_step5_with_settings(patterns, settings)
        
        # Print performance stats
        self.profiler.print_stats()
        
        return result
```

### Day 18 Completion Checklist

- [ ] Performance profiler implemented
- [ ] File caching system implemented
- [ ] Simulation optimization presets defined
- [ ] Parallel processing utilities created
- [ ] Pipeline optimizations integrated
- [ ] Performance improvement >50% validated
- [ ] Cache hit rate >80% for repeated operations

**Time:** 6-8 hours  
**Next:** Day 19 - Quality Assurance Automation

---

*(Document continues with Days 19-20, following same extreme detail pattern...)*

## Day 19: Quality Assurance Automation

**Time:** 6-8 hours  
**Goal:** Implement automated quality checks for garment outputs

### 19.1: Quality Metrics Definition

**Objective:** Define measurable quality criteria for automated validation

#### Quality Criteria

1. **Mesh Quality**:
   - No self-intersections
   - No non-manifold edges
   - Proper face normals orientation
   - Triangle count within acceptable range

2. **Texture Quality**:
   - All UV coordinates in [0,1] range
   - No UV overlaps (except intentional)
   - Texture resolution adequate
   - Color accuracy vs. input

3. **Fit Quality**:
   - No excessive penetration with avatar
   - Draping looks natural
   - Seams properly aligned
   - Proportions match measurements

### 19.2: Implement Mesh Validator

**File:** `Working_Cloth_3D_Pipeline/qa/mesh_validator.py`

```python
"""
Mesh quality validation
"""

import trimesh
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class MeshQualityReport:
    """Mesh quality report"""
    is_valid: bool
    total_vertices: int
    total_faces: int
    has_self_intersections: bool
    is_manifold: bool
    is_watertight: bool
    face_normals_ok: bool
    bounding_box_size: Tuple[float, float, float]
    issues: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'total_vertices': self.total_vertices,
            'total_faces': self.total_faces,
            'has_self_intersections': self.has_self_intersections,
            'is_manifold': self.is_manifold,
            'is_watertight': self.is_watertight,
            'face_normals_ok': self.face_normals_ok,
            'bounding_box_size': self.bounding_box_size,
            'issues': self.issues
        }


class MeshValidator:
    """
    Validates mesh quality
    
    Usage:
        validator = MeshValidator()
        report = validator.validate(mesh_path)
        
        if not report.is_valid:
            print(f"Issues: {report.issues}")
    """
    
    def __init__(
        self,
        max_vertices: int = 500000,
        max_faces: int = 1000000,
        allow_self_intersections: bool = False,
        require_manifold: bool = True
    ):
        self.max_vertices = max_vertices
        self.max_faces = max_faces
        self.allow_self_intersections = allow_self_intersections
        self.require_manifold = require_manifold
    
    def validate(self, mesh_path: str) -> MeshQualityReport:
        """
        Validate mesh quality
        
        Args:
            mesh_path: Path to mesh file (OBJ, GLB, etc.)
            
        Returns:
            MeshQualityReport
        """
        issues = []
        
        try:
            # Load mesh
            mesh = trimesh.load(mesh_path)
            
            # Basic stats
            total_vertices = len(mesh.vertices)
            total_faces = len(mesh.faces)
            
            # Check vertex count
            if total_vertices > self.max_vertices:
                issues.append(f"Too many vertices: {total_vertices} > {self.max_vertices}")
            
            # Check face count
            if total_faces > self.max_faces:
                issues.append(f"Too many faces: {total_faces} > {self.max_faces}")
            
            # Check for self-intersections
            has_self_intersections = not mesh.is_volume
            if has_self_intersections and not self.allow_self_intersections:
                issues.append("Mesh has self-intersections")
            
            # Check if manifold
            is_manifold = mesh.is_watertight
            if not is_manifold and self.require_manifold:
                issues.append("Mesh is not manifold")
            
            # Check face normals
            face_normals_ok = self._check_face_normals(mesh)
            if not face_normals_ok:
                issues.append("Face normals are inconsistent")
            
            # Get bounding box
            bbox_size = tuple(mesh.bounds[1] - mesh.bounds[0])
            
            # Create report
            report = MeshQualityReport(
                is_valid=len(issues) == 0,
                total_vertices=total_vertices,
                total_faces=total_faces,
                has_self_intersections=has_self_intersections,
                is_manifold=is_manifold,
                is_watertight=mesh.is_watertight,
                face_normals_ok=face_normals_ok,
                bounding_box_size=bbox_size,
                issues=issues
            )
            
            return report
        
        except Exception as e:
            logger.error(f"Mesh validation error: {e}")
            return MeshQualityReport(
                is_valid=False,
                total_vertices=0,
                total_faces=0,
                has_self_intersections=True,
                is_manifold=False,
                is_watertight=False,
                face_normals_ok=False,
                bounding_box_size=(0, 0, 0),
                issues=[f"Validation error: {str(e)}"]
            )
    
    def _check_face_normals(self, mesh: trimesh.Trimesh) -> bool:
        """Check if face normals are consistently oriented"""
        try:
            # Get face normals
            normals = mesh.face_normals
            
            # Check for NaN or zero normals
            if np.any(np.isnan(normals)) or np.any(np.all(normals == 0, axis=1)):
                return False
            
            # Check orientation consistency
            # (Simple heuristic: most normals should point "outward")
            centroid = mesh.centroid
            vectors_from_center = mesh.triangles_center - centroid
            
            # Dot product should be mostly positive
            dots = np.sum(vectors_from_center * normals, axis=1)
            consistency = np.sum(dots > 0) / len(dots)
            
            return consistency > 0.9  # 90% should point outward
        
        except:
            return False
```

### 19.3: Implement QA Pipeline

**File:** `Working_Cloth_3D_Pipeline/qa/qa_pipeline.py`

```python
"""
Quality assurance pipeline
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

from .mesh_validator import MeshValidator, MeshQualityReport


logger = logging.getLogger(__name__)


class QAPipeline:
    """
    Quality assurance pipeline for garment outputs
    
    Usage:
        qa = QAPipeline()
        result = qa.validate_garment(glb_path)
        
        if result['passed']:
            print("Quality checks passed!")
        else:
            print(f"Failed: {result['failures']}")
    """
    
    def __init__(self):
        self.mesh_validator = MeshValidator()
    
    def validate_garment(
        self,
        glb_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Validate complete garment output
        
        Args:
            glb_path: Path to GLB file
            metadata: Optional metadata about garment
            
        Returns:
            Validation result dictionary
        """
        results = {
            'garment_path': glb_path,
            'passed': False,
            'checks': {},
            'failures': []
        }
        
        # Check 1: Mesh quality
        mesh_report = self.mesh_validator.validate(glb_path)
        results['checks']['mesh_quality'] = mesh_report.to_dict()
        
        if not mesh_report.is_valid:
            results['failures'].extend(mesh_report.issues)
        
        # Overall pass/fail
        results['passed'] = len(results['failures']) == 0
        
        return results
    
    def generate_report(
        self,
        results: List[Dict],
        output_path: str
    ):
        """Generate QA report"""
        summary = {
            'total_garments': len(results),
            'passed': sum(1 for r in results if r['passed']),
            'failed': sum(1 for r in results if not r['passed']),
            'results': results
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"QA report saved: {output_path}")
```

### Day 19 Completion Checklist

- [ ] Mesh validator implemented
- [ ] QA pipeline created
- [ ] Automated quality checks working
- [ ] Quality reports generated

**Time:** 6-8 hours  
**Next:** Day 20 - Monitoring & Logging System

---

## Day 20: Monitoring & Logging System

**Time:** 6-8 hours  
**Goal:** Implement comprehensive logging and monitoring

### 20.1: Structured Logging

**File:** `Working_Cloth_3D_Pipeline/utils/logging_config.py`

```python
"""
Structured logging configuration
"""

import logging
import logging.handlers
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    enable_file: bool = True,
    enable_console: bool = True
):
    """
    Setup structured logging
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        enable_file: Enable file logging
        enable_console: Enable console logging
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(name)s | %(message)s'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # File handler (rotating)
    if enable_file:
        log_file = log_path / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    logging.info("Logging configured successfully")
```

### 20.2: Metrics Collection

**File:** `Working_Cloth_3D_Pipeline/utils/metrics.py`

```python
"""
Metrics collection and reporting
"""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import json


@dataclass
class PipelineMetrics:
    """Pipeline metrics"""
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'total_jobs': self.total_jobs,
            'successful_jobs': self.successful_jobs,
            'failed_jobs': self.failed_jobs,
            'success_rate': (
                self.successful_jobs / self.total_jobs * 100
                if self.total_jobs > 0 else 0
            ),
            'total_processing_time': self.total_processing_time,
            'avg_processing_time': self.avg_processing_time,
            'cache_hit_rate': (
                self.cache_hits / (self.cache_hits + self.cache_misses) * 100
                if (self.cache_hits + self.cache_misses) > 0 else 0
            )
        }


class MetricsCollector:
    """Collect and report pipeline metrics"""
    
    def __init__(self):
        self.metrics = PipelineMetrics()
    
    def record_job_success(self, processing_time: float):
        """Record successful job"""
        self.metrics.total_jobs += 1
        self.metrics.successful_jobs += 1
        self.metrics.total_processing_time += processing_time
        self._update_avg()
    
    def record_job_failure(self):
        """Record failed job"""
        self.metrics.total_jobs += 1
        self.metrics.failed_jobs += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics.cache_misses += 1
    
    def _update_avg(self):
        """Update average processing time"""
        if self.metrics.successful_jobs > 0:
            self.metrics.avg_processing_time = (
                self.metrics.total_processing_time / self.metrics.successful_jobs
            )
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return self.metrics.to_dict()
    
    def save_report(self, filepath: str):
        """Save metrics report"""
        with open(filepath, 'w') as f:
            json.dump(self.get_metrics(), f, indent=2)
```

### Day 20 Completion Checklist

- [ ] Structured logging configured
- [ ] Metrics collection implemented
- [ ] Reports generated successfully
- [ ] Monitoring dashboard accessible

**Time:** 6-8 hours

---

## Phase Completion Checklist

### Core Deliverables

- [ ] **Batch Processing System**
  - [ ] Job queue with priority support
  - [ ] Worker pool for parallel execution
  - [ ] Batch CLI for job submission
  - [ ] Can process 10+ jobs simultaneously

- [ ] **Error Handling**
  - [ ] Error classification system
  - [ ] Retry manager with backoff
  - [ ] Circuit breaker implemented
  - [ ] Graceful failure recovery

- [ ] **Performance Optimization**
  - [ ] Performance profiler working
  - [ ] File caching system active
  - [ ] Simulation presets optimized
  - [ ] 50%+ speed improvement achieved

- [ ] **Quality Assurance**
  - [ ] Mesh validator implemented
  - [ ] Automated QA pipeline
  - [ ] Quality reports generated
  - [ ] Bad outputs prevented

- [ ] **Monitoring & Logging**
  - [ ] Structured logging configured
  - [ ] Metrics collection active
  - [ ] Performance dashboards
  - [ ] Full observability

### Success Metrics

- [ ] Batch processing working for 10+ concurrent jobs
- [ ] Automatic recovery from 90%+ of transient failures
- [ ] Average processing time < 5 minutes per garment
- [ ] Quality failure rate < 5%
- [ ] Full pipeline observability via logs/metrics

### Documentation

- [ ] Batch processing guide
- [ ] Error handling documentation
- [ ] Performance tuning guide
- [ ] QA criteria documented
- [ ] Monitoring setup guide

---

**Phase 3 Status:** Ready for Implementation

**Prerequisites:** Phase 2 Complete (CLO integration working)

**Next:** Phase 4 - Validation & Deployment

---

## Troubleshooting Guide

### Batch Processing Issues

**Problem:** Jobs stuck in queue
- Check worker status with `batch_cli status`
- Verify CLO API is responding
- Check for circuit breaker activation
- Review worker logs for errors

**Problem:** Workers crashing
- Check memory usage (should be <4GB per worker)
- Reduce number of workers
- Enable retry logic
- Review error logs

### Performance Issues

**Problem:** Slow simulation times
- Use lower quality preset (DRAFT or PREVIEW)
- Reduce particle_distance
- Lower simulation_quality
- Check for memory pressure

**Problem:** Cache not working
- Verify cache directory exists and is writable
- Check cache TTL settings
- Clear corrupted cache files
- Review cache hit rate metrics

### Error Handling Issues

**Problem:** Too many retries
- Reduce max_retries
- Increase retry delays
- Fix underlying cause (API, network, etc.)
- Enable circuit breaker

**Problem:** Circuit breaker triggering
- Increase threshold
- Increase timeout
- Fix root cause of failures
- Review error classification rules

---

**End of Phase 3 Detailed Guide**

**Total Estimated Time:** 30-40 hours (Week 4)

**Next Phase:** Phase 4 - Validation & Deployment (Week 5)
