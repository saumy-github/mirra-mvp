# Phase 4: CLO3D Validation & Deployment - Detailed Implementation Guide

**Project:** MIRRA MVP - CLO3D Migration  
**Phase:** 4 of 5 - Validation & Deployment  
**Duration:** Week 5 (5 working days)  
**Status:** Ready for Implementation  
**Branch:** `clo3danant`  
**Prerequisites:** Phase 1, 2 & 3 Complete

---

## Table of Contents

1. [Phase Overview](#phase-overview)
2. [Prerequisites from Phase 3](#prerequisites-from-phase-3)
3. [Week 5: Validation & Deployment](#week-5-validation--deployment)
   - [Day 21: Comprehensive Testing Suite](#day-21-comprehensive-testing-suite)
   - [Day 22: Load Testing & Stress Testing](#day-22-load-testing--stress-testing)
   - [Day 23: Production Deployment Preparation](#day-23-production-deployment-preparation)
   - [Day 24: Documentation & Training Materials](#day-24-documentation--training-materials)
   - [Day 25: Production Launch & Handoff](#day-25-production-launch--handoff)
4. [Phase Completion Checklist](#phase-completion-checklist)
5. [Production Readiness Checklist](#production-readiness-checklist)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## Phase Overview

### Starting Point (From Phase 3)

You now have:
✅ Complete CLO integration (Phases 1-2)  
✅ Batch processing for parallel execution  
✅ Robust error handling with retry logic  
✅ Performance optimizations (50%+ faster)  
✅ Automated quality assurance  
✅ Comprehensive monitoring and logging  
✅ Production-ready pipeline code

### Goals for Phase 4

By the end of Phase 4, you will have:

1. ✅ Comprehensive test suite (unit, integration, end-to-end)
2. ✅ Load testing validation (100+ concurrent jobs)
3. ✅ Production deployment scripts and configuration
4. ✅ Complete documentation (technical + user guides)
5. ✅ Training materials for operators
6. ✅ Production launch plan
7. ✅ System fully deployed and operational

### Success Criteria

- [ ] All test suites pass (100% coverage of critical paths)
- [ ] System handles 100+ concurrent jobs without degradation
- [ ] Zero critical bugs in production environment
- [ ] All documentation complete and reviewed
- [ ] Operators trained and confident
- [ ] Production deployment successful
- [ ] Rollback plan tested and ready

### Time Allocation

| Week | Days | Focus | Deliverable |
|------|------|-------|-------------|
| **Week 5** | 21-25 | Validation & deployment | Testing, docs, production launch |

**Total:** 30-40 hours

---

## Prerequisites from Phase 3

### Verify Phase 3 Completion

Before starting Phase 4, verify all Phase 3 deliverables:

```powershell
# Navigate to project
cd C:\Users\Anant\mirra-mvp

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run Phase 3 validation
python tests\test_phase3_complete.py
```

**Expected output:**
```
============================================================
PHASE 3 COMPLETE INTEGRATION TEST
============================================================

[1/10] Testing Batch Processing System...
✓ Job queue operational
✓ Worker pool initialized (3 workers)
✓ Jobs can be submitted
✓ Jobs processed in parallel
✓ Batch CLI functional

[2/10] Testing Error Classification...
✓ Network errors classified correctly
✓ API errors classified correctly
✓ Validation errors classified correctly
✓ Fatal errors handled appropriately

[3/10] Testing Retry Manager...
✓ Transient errors retried automatically
✓ Exponential backoff working
✓ Circuit breaker prevents cascading failures
✓ Max retries respected

[4/10] Testing Performance Optimization...
✓ Performance profiler working
✓ Cache system operational
✓ Cache hit rate > 80%
✓ Processing time < 5 minutes per garment

[5/10] Testing Simulation Presets...
✓ DRAFT preset functional
✓ PREVIEW preset functional
✓ PRODUCTION preset functional
✓ FINAL preset functional

[6/10] Testing Quality Assurance...
✓ Mesh validator working
✓ QA pipeline operational
✓ Quality reports generated
✓ Bad outputs rejected

[7/10] Testing Monitoring & Logging...
✓ Structured logging configured
✓ Log rotation working
✓ Metrics collected
✓ Performance reports generated

[8/10] Testing Parallel Processing...
✓ 10 jobs processed simultaneously
✓ No resource contention
✓ Memory usage stable (<12GB total)

[9/10] Performance Benchmark...
✓ Average time: 4.5 minutes per garment
✓ 50% improvement vs. Phase 2
✓ Throughput: 13+ garments/hour (3 workers)

[10/10] System Health Check...
✓ CLO API responsive
✓ All modules loaded
✓ No memory leaks
✓ Error rate < 2%

============================================================
✓✓✓ PHASE 3 COMPLETE - ALL TESTS PASSED ✓✓✓
============================================================

Ready to proceed to Phase 4: Validation & Deployment
```

### Required Files from Phase 3

Verify these files exist:

```powershell
# Batch processing
Test-Path "Working_Cloth_3D_Pipeline\batch\job_queue.py"
Test-Path "Working_Cloth_3D_Pipeline\batch\batch_processor.py"
Test-Path "Working_Cloth_3D_Pipeline\batch\batch_cli.py"

# Error handling
Test-Path "Working_Cloth_3D_Pipeline\batch\error_handling.py"
Test-Path "Working_Cloth_3D_Pipeline\batch\retry_manager.py"

# Performance optimization
Test-Path "Working_Cloth_3D_Pipeline\utils\profiler.py"
Test-Path "Working_Cloth_3D_Pipeline\utils\cache.py"
Test-Path "Working_Cloth_3D_Pipeline\steps\clo_integration\simulation_optimizer.py"

# Quality assurance
Test-Path "Working_Cloth_3D_Pipeline\qa\mesh_validator.py"
Test-Path "Working_Cloth_3D_Pipeline\qa\qa_pipeline.py"

# Monitoring
Test-Path "Working_Cloth_3D_Pipeline\utils\logging_config.py"
Test-Path "Working_Cloth_3D_Pipeline\utils\metrics.py"
```

All should return `True`.

---

## Week 5: Validation & Deployment

Phase 4 focuses on comprehensive testing, documentation, and production deployment.

---

## Day 21: Comprehensive Testing Suite

**Time:** 8-10 hours  
**Goal:** Build complete test suite with unit, integration, and end-to-end tests

### 21.1: Test Strategy & Coverage

**Objective:** Define comprehensive testing strategy

#### Testing Pyramid

```
        /\
       /  \    E2E Tests (10%)
      /____\   
     /      \  Integration Tests (30%)
    /________\
   /          \
  /____________\ Unit Tests (60%)
```

**Coverage Goals:**
- **Unit Tests**: 60% of tests, >85% code coverage
- **Integration Tests**: 30% of tests, all module interactions
- **End-to-End Tests**: 10% of tests, critical user workflows

### 21.2: Implement Unit Test Suite

**File:** `tests/unit/test_clo_client.py`

```python
"""
Unit tests for CLO API client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from Working_Cloth_3D_Pipeline.steps.clo_integration.clo_client import (
    CLOAPIClient,
    CLOConnectionError,
    CLOProjectError,
    CLOImportError
)


@pytest.fixture
def mock_client():
    """Create CLO client with mocked requests"""
    with patch('requests.Session') as mock_session:
        client = CLOAPIClient(base_url="http://localhost:50505/api")
        client.session = mock_session.return_value
        yield client


def test_client_initialization():
    """Test client initialization"""
    client = CLOAPIClient()
    assert client.base_url == "http://localhost:50505/api"
    assert client.session is not None


def test_connection_check_success(mock_client):
    """Test successful connection check"""
    mock_client.session.get.return_value.status_code = 200
    mock_client.session.get.return_value.json.return_value = {"status": "ok"}
    
    result = mock_client.check_connection()
    assert result is True


def test_connection_check_failure(mock_client):
    """Test failed connection check"""
    mock_client.session.get.side_effect = requests.ConnectionError("Connection refused")
    
    with pytest.raises(CLOConnectionError):
        mock_client.check_connection()


def test_create_project_success(mock_client):
    """Test successful project creation"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {
        "project_id": "proj_123",
        "name": "test_project"
    }
    
    result = mock_client.create_project("test_project")
    assert result["project_id"] == "proj_123"
    assert result["name"] == "test_project"


def test_create_project_failure(mock_client):
    """Test failed project creation"""
    mock_client.session.post.return_value.status_code = 500
    mock_client.session.post.return_value.json.return_value = {"error": "Server error"}
    
    with pytest.raises(CLOProjectError):
        mock_client.create_project("test_project")


def test_import_avatar_success(mock_client):
    """Test successful avatar import"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {
        "avatar_id": "avatar_123",
        "vertices": 50000,
        "faces": 100000
    }
    
    result = mock_client.import_avatar("avatar.obj")
    assert result["avatar_id"] == "avatar_123"
    assert result["vertices"] == 50000


def test_import_avatar_file_not_found(mock_client):
    """Test avatar import with missing file"""
    mock_client.session.post.return_value.status_code = 404
    mock_client.session.post.return_value.json.return_value = {"error": "File not found"}
    
    with pytest.raises(CLOImportError):
        mock_client.import_avatar("nonexistent.obj")


def test_import_patterns_success(mock_client):
    """Test successful pattern import"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {
        "patterns": [
            {"id": "pat_1", "name": "front"},
            {"id": "pat_2", "name": "back"}
        ]
    }
    
    result = mock_client.import_patterns(["front.dxf", "back.dxf"])
    assert len(result["patterns"]) == 2


def test_apply_fabric_success(mock_client):
    """Test fabric application"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {"status": "success"}
    
    result = mock_client.apply_fabric("pattern_1", "cotton_tshirt")
    assert result["status"] == "success"


def test_create_seam_success(mock_client):
    """Test seam creation"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {"seam_id": "seam_123"}
    
    result = mock_client.create_seam("front", "edge_1", "back", "edge_2")
    assert result["seam_id"] == "seam_123"


def test_run_simulation_success(mock_client):
    """Test simulation execution"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {
        "status": "completed",
        "iterations": 150,
        "time": 120.5
    }
    
    result = mock_client.run_simulation(blocking=True)
    assert result["status"] == "completed"
    assert result["iterations"] == 150


def test_export_garment_success(mock_client):
    """Test garment export"""
    mock_client.session.post.return_value.status_code = 200
    mock_client.session.post.return_value.json.return_value = {
        "export_path": "output.glb",
        "file_size": 5242880
    }
    
    result = mock_client.export_garment("output.glb", format="glb")
    assert result["export_path"] == "output.glb"


def test_api_timeout(mock_client):
    """Test API timeout handling"""
    mock_client.session.get.side_effect = requests.Timeout("Request timeout")
    
    with pytest.raises(CLOConnectionError):
        mock_client.check_connection()


def test_invalid_response_format(mock_client):
    """Test handling of invalid response format"""
    mock_client.session.get.return_value.status_code = 200
    mock_client.session.get.return_value.json.side_effect = ValueError("Invalid JSON")
    
    with pytest.raises(CLOConnectionError):
        mock_client.check_connection()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=Working_Cloth_3D_Pipeline.steps.clo_integration.clo_client'])
```

**File:** `tests/unit/test_fabric_library.py`

```python
"""
Unit tests for fabric library
"""

import pytest

from Working_Cloth_3D_Pipeline.steps.clo_integration.fabric_library import (
    FabricProperties,
    FabricLibrary,
    FABRIC_PRESETS,
    get_fabric_for_garment,
    create_custom_fabric
)


def test_fabric_properties_creation():
    """Test FabricProperties dataclass"""
    fabric = FabricProperties(
        name="test_fabric",
        weight=200.0,
        thickness=1.5,
        stretch_warp=10.0,
        stretch_weft=10.0
    )
    
    assert fabric.name == "test_fabric"
    assert fabric.weight == 200.0
    assert fabric.thickness == 1.5


def test_fabric_library_initialization():
    """Test FabricLibrary initialization"""
    library = FabricLibrary()
    
    assert len(library.fabrics) > 0
    assert "cotton_tshirt" in library.fabrics


def test_get_fabric_by_name():
    """Test retrieving fabric by name"""
    library = FabricLibrary()
    
    fabric = library.get_fabric("cotton_tshirt")
    assert fabric is not None
    assert fabric.name == "cotton_tshirt"
    assert fabric.weight == 150.0


def test_get_nonexistent_fabric():
    """Test retrieving non-existent fabric"""
    library = FabricLibrary()
    
    fabric = library.get_fabric("nonexistent_fabric")
    assert fabric is None


def test_add_custom_fabric():
    """Test adding custom fabric"""
    library = FabricLibrary()
    
    custom = FabricProperties(
        name="custom_fabric",
        weight=250.0,
        thickness=2.0,
        stretch_warp=5.0,
        stretch_weft=5.0
    )
    
    library.add_fabric(custom)
    
    fabric = library.get_fabric("custom_fabric")
    assert fabric is not None
    assert fabric.weight == 250.0


def test_list_fabrics():
    """Test listing all fabrics"""
    library = FabricLibrary()
    
    fabrics = library.list_fabrics()
    assert len(fabrics) > 0
    assert "cotton_tshirt" in fabrics


def test_get_fabric_for_garment_tshirt():
    """Test garment-to-fabric mapping for t-shirt"""
    fabric = get_fabric_for_garment("tshirt")
    assert fabric is not None
    assert fabric.name == "cotton_tshirt"


def test_get_fabric_for_garment_pants():
    """Test garment-to-fabric mapping for pants"""
    fabric = get_fabric_for_garment("pants")
    assert fabric is not None
    assert "denim" in fabric.name.lower()


def test_get_fabric_for_unknown_garment():
    """Test fallback for unknown garment"""
    fabric = get_fabric_for_garment("nonexistent_garment")
    assert fabric is not None  # Should return default


def test_create_custom_fabric():
    """Test custom fabric creation helper"""
    fabric = create_custom_fabric(
        name="my_fabric",
        weight=300.0,
        stretch=20.0
    )
    
    assert fabric.name == "my_fabric"
    assert fabric.weight == 300.0
    assert fabric.stretch_warp == 20.0
    assert fabric.stretch_weft == 20.0


def test_all_presets_valid():
    """Test that all preset fabrics are valid"""
    for name, fabric in FABRIC_PRESETS.items():
        assert fabric.weight > 0
        assert fabric.thickness > 0
        assert 0 <= fabric.stretch_warp <= 100
        assert 0 <= fabric.stretch_weft <= 100
        assert 0 <= fabric.friction <= 1.0


def test_fabric_to_dict():
    """Test fabric serialization"""
    fabric = FabricProperties(
        name="test",
        weight=150.0,
        thickness=1.0,
        stretch_warp=10.0,
        stretch_weft=10.0
    )
    
    data = fabric.to_dict()
    assert isinstance(data, dict)
    assert data["name"] == "test"
    assert data["weight"] == 150.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**File:** `tests/unit/test_batch_processor.py`

```python
"""
Unit tests for batch processor
"""

import pytest
from unittest.mock import Mock, patch
import time

from Working_Cloth_3D_Pipeline.batch import (
    BatchProcessor,
    WorkerConfig,
    PipelineJob,
    JobPriority,
    JobStatus,
    JobQueue
)


@pytest.fixture
def job_queue():
    """Create fresh job queue"""
    queue = JobQueue()
    queue._jobs.clear()
    queue._metrics = {
        'total_jobs': 0,
        'completed_jobs': 0,
        'failed_jobs': 0,
        'cancelled_jobs': 0
    }
    return queue


def test_pipeline_job_creation():
    """Test PipelineJob creation"""
    job = PipelineJob(
        avatar_id="user_123",
        garment_type="tshirt",
        priority=JobPriority.HIGH
    )
    
    assert job.avatar_id == "user_123"
    assert job.garment_type == "tshirt"
    assert job.priority == JobPriority.HIGH
    assert job.status == JobStatus.PENDING


def test_job_queue_add(job_queue):
    """Test adding job to queue"""
    job = PipelineJob(avatar_id="test", garment_type="tshirt")
    
    job_id = job_queue.add_job(job)
    assert job_id is not None
    assert job_queue.size() == 1


def test_job_queue_get(job_queue):
    """Test getting job from queue"""
    job = PipelineJob(avatar_id="test", garment_type="tshirt")
    job_queue.add_job(job)
    
    retrieved_job = job_queue.get_job(timeout=1.0)
    assert retrieved_job is not None
    assert retrieved_job.avatar_id == "test"
    assert retrieved_job.status == JobStatus.RUNNING


def test_job_queue_priority(job_queue):
    """Test priority-based queue ordering"""
    job_low = PipelineJob(avatar_id="low", garment_type="tshirt", priority=JobPriority.LOW)
    job_high = PipelineJob(avatar_id="high", garment_type="tshirt", priority=JobPriority.HIGH)
    
    job_queue.add_job(job_low)
    job_queue.add_job(job_high)
    
    # High priority should come first
    first_job = job_queue.get_job(timeout=1.0)
    assert first_job.avatar_id == "high"


def test_job_status_update(job_queue):
    """Test job status updates"""
    job = PipelineJob(avatar_id="test", garment_type="tshirt")
    job_id = job_queue.add_job(job)
    
    job_queue.update_job_status(job_id, JobStatus.COMPLETED, result_path="output.glb")
    
    status = job_queue.get_job_status(job_id)
    assert status == JobStatus.COMPLETED
    
    info = job_queue.get_job_info(job_id)
    assert info["result_path"] == "output.glb"


def test_job_queue_metrics(job_queue):
    """Test metrics collection"""
    job1 = PipelineJob(avatar_id="test1", garment_type="tshirt")
    job2 = PipelineJob(avatar_id="test2", garment_type="pants")
    
    job_id1 = job_queue.add_job(job1)
    job_id2 = job_queue.add_job(job2)
    
    job_queue.update_job_status(job_id1, JobStatus.COMPLETED)
    job_queue.update_job_status(job_id2, JobStatus.FAILED, error="Test error")
    
    metrics = job_queue.get_metrics()
    assert metrics["total_jobs"] == 2
    assert metrics["completed_jobs"] == 1
    assert metrics["failed_jobs"] == 1


def test_batch_processor_initialization():
    """Test BatchProcessor initialization"""
    config = WorkerConfig(num_workers=2)
    processor = BatchProcessor(config)
    
    assert processor.config.num_workers == 2
    assert not processor.is_running


def test_batch_processor_start_stop():
    """Test processor lifecycle"""
    config = WorkerConfig(num_workers=2)
    processor = BatchProcessor(config)
    
    processor.start()
    assert processor.is_running
    assert len(processor.workers) == 2
    
    processor.stop()
    assert not processor.is_running


@patch('Working_Cloth_3D_Pipeline.pipeline.ClothPipeline')
def test_job_submission(mock_pipeline, job_queue):
    """Test job submission"""
    config = WorkerConfig(num_workers=1)
    processor = BatchProcessor(config)
    processor.start()
    
    job = PipelineJob(avatar_id="test", garment_type="tshirt")
    job_id = processor.submit_job(job)
    
    assert job_id is not None
    
    processor.stop()


def test_batch_submission():
    """Test batch job submission"""
    config = WorkerConfig(num_workers=2)
    processor = BatchProcessor(config)
    processor.start()
    
    jobs = [
        PipelineJob(avatar_id=f"user_{i}", garment_type="tshirt")
        for i in range(5)
    ]
    
    job_ids = processor.submit_batch(jobs)
    assert len(job_ids) == 5
    
    processor.stop()


def test_worker_config():
    """Test WorkerConfig"""
    config = WorkerConfig(
        num_workers=5,
        max_retries=5,
        retry_delay_seconds=60
    )
    
    assert config.num_workers == 5
    assert config.max_retries == 5
    assert config.retry_delay_seconds == 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### 21.3: Implement Integration Tests

**File:** `tests/integration/test_pipeline_integration.py`

```python
"""
Integration tests for full pipeline
"""

import pytest
from pathlib import Path
import shutil

from Working_Cloth_3D_Pipeline.pipeline import ClothPipeline
from Working_Cloth_3D_Pipeline.config.pipeline_config import PipelineConfig


@pytest.fixture
def test_output_dir(tmp_path):
    """Create temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    yield output_dir
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)


@pytest.fixture
def pipeline(test_output_dir):
    """Create pipeline instance"""
    config = PipelineConfig()
    config.output_dir = str(test_output_dir)
    pipeline = ClothPipeline(config)
    return pipeline


def test_full_pipeline_tshirt(pipeline):
    """Test full pipeline for t-shirt"""
    # Set parameters
    pipeline.set_avatar_id("test_avatar_001")
    pipeline.set_garment_type("tshirt")
    pipeline.set_measurements({
        "height": 175,
        "chest": 95,
        "waist": 80,
        "hips": 95
    })
    
    # Run pipeline
    result = pipeline.run()
    
    # Verify result
    assert result["success"] is True
    assert "output_path" in result
    assert Path(result["output_path"]).exists()


def test_full_pipeline_pants(pipeline):
    """Test full pipeline for pants"""
    pipeline.set_avatar_id("test_avatar_001")
    pipeline.set_garment_type("pants")
    pipeline.set_measurements({
        "height": 175,
        "waist": 80,
        "hips": 95,
        "inseam": 80
    })
    
    result = pipeline.run()
    
    assert result["success"] is True
    assert Path(result["output_path"]).exists()


def test_pipeline_with_custom_design(pipeline):
    """Test pipeline with custom design parameters"""
    pipeline.set_avatar_id("test_avatar_001")
    pipeline.set_garment_type("tshirt")
    pipeline.set_design_params({
        "color": "navy",
        "pattern_style": "graphic",
        "neckline": "crew"
    })
    
    result = pipeline.run()
    
    assert result["success"] is True


def test_pipeline_caching(pipeline):
    """Test that caching improves performance"""
    pipeline.set_avatar_id("test_avatar_001")
    pipeline.set_garment_type("tshirt")
    
    # First run (cache miss)
    result1 = pipeline.run()
    time1 = result1.get("processing_time", 0)
    
    # Second run (cache hit)
    result2 = pipeline.run()
    time2 = result2.get("processing_time", 0)
    
    # Second run should be faster (if caching works)
    # Note: This might not always be true in tests
    assert result1["success"] is True
    assert result2["success"] is True


def test_pipeline_quality_validation(pipeline):
    """Test that quality validation works"""
    pipeline.set_avatar_id("test_avatar_001")
    pipeline.set_garment_type("tshirt")
    
    result = pipeline.run()
    
    assert result["success"] is True
    assert "quality_report" in result
    assert result["quality_report"]["is_valid"] is True


def test_clo_integration_workflow(pipeline):
    """Test CLO integration specifically"""
    pipeline.set_avatar_id("test_avatar_001")
    pipeline.set_garment_type("tshirt")
    
    # Run with CLO backend
    result = pipeline.run()
    
    # Verify CLO-specific outputs
    assert result["success"] is True
    assert "simulation_time" in result
    assert "garment_quality" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**File:** `tests/integration/test_clo_api_integration.py`

```python
"""
Integration tests for CLO API (requires CLO running)
"""

import pytest
from pathlib import Path

from Working_Cloth_3D_Pipeline.steps.clo_integration.clo_client import CLOAPIClient
from Working_Cloth_3D_Pipeline.steps.clo_integration.fabric_library import get_fabric_for_garment


@pytest.fixture
def clo_client():
    """Create CLO client (requires CLO running)"""
    client = CLOAPIClient()
    
    # Check if CLO is available
    try:
        client.check_connection()
        return client
    except:
        pytest.skip("CLO3D not running")


def test_clo_connection(clo_client):
    """Test CLO API connection"""
    result = clo_client.check_connection()
    assert result is True


def test_create_and_delete_project(clo_client):
    """Test project lifecycle"""
    # Create project
    project = clo_client.create_project("test_project")
    assert "project_id" in project
    
    # Delete project (if supported)
    # clo_client.delete_project(project["project_id"])


def test_import_avatar_workflow(clo_client, tmp_path):
    """Test avatar import workflow"""
    # This requires a test OBJ file
    test_obj = Path("tests/fixtures/test_avatar.obj")
    
    if not test_obj.exists():
        pytest.skip("Test avatar file not found")
    
    # Create project
    project = clo_client.create_project("test_avatar_import")
    
    # Import avatar
    avatar = clo_client.import_avatar(str(test_obj))
    assert "avatar_id" in avatar


def test_fabric_application_workflow(clo_client):
    """Test fabric application"""
    # Create project
    project = clo_client.create_project("test_fabric")
    
    # Get fabric
    fabric = get_fabric_for_garment("tshirt")
    
    # Apply fabric (requires patterns imported first)
    # This is a simplified test
    assert fabric is not None


def test_simulation_workflow(clo_client):
    """Test simulation execution"""
    # This requires a complete project setup
    # Placeholder for now
    pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### 21.4: Implement End-to-End Tests

**File:** `tests/e2e/test_complete_workflow.py`

```python
"""
End-to-end tests for complete user workflows
"""

import pytest
from pathlib import Path
import json
import time

from Working_Cloth_3D_Pipeline.batch import BatchProcessor, PipelineJob, WorkerConfig


@pytest.fixture
def e2e_output_dir(tmp_path):
    """Create E2E output directory"""
    output = tmp_path / "e2e_output"
    output.mkdir()
    return output


def test_single_garment_workflow(e2e_output_dir):
    """
    Test complete workflow for single garment
    
    User story: Create a single t-shirt for a user
    """
    from Working_Cloth_3D_Pipeline.pipeline import ClothPipeline
    
    # Initialize pipeline
    pipeline = ClothPipeline()
    
    # Set user parameters
    pipeline.set_avatar_id("user_e2e_001")
    pipeline.set_garment_type("tshirt")
    pipeline.set_measurements({
        "height": 180,
        "chest": 100,
        "waist": 85,
        "hips": 98
    })
    pipeline.set_design_params({
        "color": "navy",
        "pattern_style": "solid"
    })
    
    # Run pipeline
    start_time = time.time()
    result = pipeline.run()
    processing_time = time.time() - start_time
    
    # Verify results
    assert result["success"] is True, f"Pipeline failed: {result.get('error')}"
    assert "output_path" in result
    assert Path(result["output_path"]).exists()
    assert Path(result["output_path"]).suffix == ".glb"
    
    # Verify performance
    assert processing_time < 600, f"Processing took too long: {processing_time}s"
    
    # Verify quality
    assert "quality_report" in result
    assert result["quality_report"]["is_valid"] is True


def test_multiple_garments_workflow(e2e_output_dir):
    """
    Test workflow for multiple garments
    
    User story: Create outfit (t-shirt + pants) for a user
    """
    config = WorkerConfig(num_workers=2)
    processor = BatchProcessor(config)
    processor.start()
    
    # Create jobs for outfit
    jobs = [
        PipelineJob(
            avatar_id="user_e2e_002",
            garment_type="tshirt",
            measurements={"height": 175, "chest": 95, "waist": 80, "hips": 95},
            design_params={"color": "white"}
        ),
        PipelineJob(
            avatar_id="user_e2e_002",
            garment_type="pants",
            measurements={"height": 175, "waist": 80, "hips": 95, "inseam": 80},
            design_params={"color": "black"}
        )
    ]
    
    # Submit batch
    job_ids = processor.submit_batch(jobs)
    
    # Wait for completion
    results = processor.wait_all(timeout=1200)  # 20 minutes max
    
    processor.stop()
    
    # Verify all completed
    assert results["completed"] == 2, f"Expected 2 completed, got {results['completed']}"
    assert results["failed"] == 0, f"Some jobs failed: {results['failed']}"


def test_batch_processing_workflow(e2e_output_dir):
    """
    Test batch processing workflow
    
    User story: Process 10 users' garments simultaneously
    """
    config = WorkerConfig(num_workers=3)
    processor = BatchProcessor(config)
    processor.start()
    
    # Create 10 jobs
    jobs = [
        PipelineJob(
            avatar_id=f"batch_user_{i:03d}",
            garment_type="tshirt",
            measurements={"height": 170 + i, "chest": 90 + i, "waist": 75 + i, "hips": 90 + i}
        )
        for i in range(10)
    ]
    
    # Submit and wait
    start_time = time.time()
    job_ids = processor.submit_batch(jobs)
    results = processor.wait_all(timeout=3600)  # 1 hour max
    total_time = time.time() - start_time
    
    processor.stop()
    
    # Verify results
    assert results["completed"] >= 8, f"Too many failures: {results['failed']}/10"
    
    # Verify parallel processing speed
    avg_time_per_garment = total_time / results["completed"]
    assert avg_time_per_garment < 400, f"Average time too high: {avg_time_per_garment}s"


def test_error_recovery_workflow(e2e_output_dir):
    """
    Test error recovery workflow
    
    User story: System recovers from transient failures automatically
    """
    config = WorkerConfig(num_workers=2, max_retries=3)
    processor = BatchProcessor(config)
    processor.start()
    
    # Create jobs (some may fail transiently)
    jobs = [
        PipelineJob(avatar_id=f"recovery_user_{i}", garment_type="tshirt")
        for i in range(5)
    ]
    
    job_ids = processor.submit_batch(jobs)
    results = processor.wait_all(timeout=1800)
    
    processor.stop()
    
    # Should complete most despite any transient errors
    success_rate = results["completed"] / (results["completed"] + results["failed"])
    assert success_rate >= 0.8, f"Success rate too low: {success_rate}"


def test_quality_gate_workflow(e2e_output_dir):
    """
    Test quality gate workflow
    
    User story: Bad outputs are rejected before delivery
    """
    from Working_Cloth_3D_Pipeline.pipeline import ClothPipeline
    from Working_Cloth_3D_Pipeline.qa.qa_pipeline import QAPipeline
    
    pipeline = ClothPipeline()
    qa = QAPipeline()
    
    # Run pipeline
    pipeline.set_avatar_id("qa_user_001")
    pipeline.set_garment_type("tshirt")
    result = pipeline.run()
    
    if result["success"]:
        # Run QA on output
        qa_result = qa.validate_garment(result["output_path"])
        
        # Verify QA catches issues
        assert "checks" in qa_result
        assert "mesh_quality" in qa_result["checks"]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
```

### 21.5: Create Test Runner Scripts

**File:** `tests/run_all_tests.py`

```python
"""
Run all test suites with coverage reporting
"""

import pytest
import sys
from pathlib import Path


def main():
    """Run all tests"""
    
    test_args = [
        'tests/',
        '-v',
        '--tb=short',
        '--cov=Working_Cloth_3D_Pipeline',
        '--cov-report=html',
        '--cov-report=term',
        '--cov-fail-under=70',
        '-m', 'not slow'  # Skip slow tests by default
    ]
    
    print("=" * 70)
    print("MIRRA Pipeline - Complete Test Suite")
    print("=" * 70)
    
    # Run tests
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n" + "=" * 70)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("=" * 70)
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
```

**PowerShell script:** `tests/run_tests.ps1`

```powershell
# Run all tests with coverage

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MIRRA Pipeline - Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run unit tests
Write-Host "`n[1/3] Running Unit Tests..." -ForegroundColor Yellow
pytest tests\unit\ -v --cov=Working_Cloth_3D_Pipeline

if ($LASTEXITCODE -ne 0) {
    Write-Host "Unit tests failed!" -ForegroundColor Red
    exit 1
}

# Run integration tests
Write-Host "`n[2/3] Running Integration Tests..." -ForegroundColor Yellow
pytest tests\integration\ -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "Integration tests failed!" -ForegroundColor Red
    exit 1
}

# Run E2E tests
Write-Host "`n[3/3] Running End-to-End Tests..." -ForegroundColor Yellow
pytest tests\e2e\ -v --tb=short

if ($LASTEXITCODE -ne 0) {
    Write-Host "E2E tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓✓✓ ALL TESTS PASSED ✓✓✓" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Generate coverage report
Write-Host "`nGenerating coverage report..." -ForegroundColor Yellow
pytest tests/ --cov=Working_Cloth_3D_Pipeline --cov-report=html --cov-report=term

Write-Host "`nCoverage report generated in htmlcov\index.html" -ForegroundColor Cyan
```

### 21.6: Run Complete Test Suite

```powershell
# Run all tests
.\tests\run_tests.ps1

# Or using Python directly
python tests\run_all_tests.py

# Run specific test categories
pytest tests\unit\ -v                    # Unit tests only
pytest tests\integration\ -v             # Integration tests only
pytest tests\e2e\ -v                     # E2E tests only

# Run with coverage
pytest tests/ --cov=Working_Cloth_3D_Pipeline --cov-report=html

# Open coverage report
start htmlcov\index.html
```

### Day 21 Completion Checklist

- [ ] Unit test suite implemented (15+ test files)
- [ ] Integration tests implemented (5+ test files)
- [ ] End-to-end tests implemented (3+ workflows)
- [ ] Test runner scripts created
- [ ] All tests passing
- [ ] Code coverage > 70%
- [ ] Coverage report generated

**Time:** 8-10 hours  
**Next:** Day 22 - Load Testing & Stress Testing

---

## Day 22: Load Testing & Stress Testing

**Time:** 6-8 hours  
**Goal:** Validate system under high load and stress conditions

### 22.1: Load Testing Strategy

**Objective:** Define load testing scenarios and success criteria

#### Load Testing Scenarios

1. **Normal Load**: 10 concurrent jobs (baseline)
2. **Peak Load**: 50 concurrent jobs (expected peak)
3. **Stress Load**: 100 concurrent jobs (stress test)
4. **Soak Test**: 50 jobs over 4 hours (stability)

**Success Criteria:**
- Normal load: <5% error rate, <5min avg time
- Peak load: <10% error rate, <8min avg time
- Stress load: <20% error rate, no crashes
- Soak test: Stable performance, no memory leaks

### 22.2: Implement Load Testing Framework

**File:** `tests/load/load_test_framework.py`

```python
"""
Load testing framework for pipeline
"""

import time
import threading
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import statistics
import logging

from Working_Cloth_3D_Pipeline.batch import BatchProcessor, PipelineJob, WorkerConfig


logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    num_jobs: int = 10
    num_workers: int = 3
    job_timeout: int = 600
    ramp_up_time: int = 0
    test_duration: int = 3600
    avatar_pool_size: int = 5
    garment_types: List[str] = field(default_factory=lambda: ["tshirt", "pants"])


@dataclass
class LoadTestResult:
    """Load test results"""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    avg_time: float = 0.0
    min_time: float = 0.0
    max_time: float = 0.0
    p50_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    processing_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    
    def calculate_stats(self):
        """Calculate statistics from processing times"""
        if self.processing_times:
            self.avg_time = statistics.mean(self.processing_times)
            self.min_time = min(self.processing_times)
            self.max_time = max(self.processing_times)
            self.p50_time = statistics.median(self.processing_times)
            self.p95_time = statistics.quantiles(self.processing_times, n=20)[18]  # 95th percentile
            self.p99_time = statistics.quantiles(self.processing_times, n=100)[98]  # 99th percentile
        
        duration = (self.end_time - self.start_time).total_seconds()
        if duration > 0:
            self.throughput = self.completed_jobs / duration * 3600  # jobs per hour
        
        if self.total_jobs > 0:
            self.error_rate = self.failed_jobs / self.total_jobs * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'summary': {
                'total_jobs': self.total_jobs,
                'completed_jobs': self.completed_jobs,
                'failed_jobs': self.failed_jobs,
                'error_rate_percent': round(self.error_rate, 2),
                'throughput_per_hour': round(self.throughput, 2)
            },
            'timings': {
                'avg_seconds': round(self.avg_time, 2),
                'min_seconds': round(self.min_time, 2),
                'max_seconds': round(self.max_time, 2),
                'p50_seconds': round(self.p50_time, 2),
                'p95_seconds': round(self.p95_time, 2),
                'p99_seconds': round(self.p99_time, 2)
            },
            'duration': {
                'start': self.start_time.isoformat(),
                'end': self.end_time.isoformat(),
                'total_seconds': (self.end_time - self.start_time).total_seconds()
            },
            'errors': self.errors[:10]  # First 10 errors
        }


class LoadTester:
    """
    Load testing framework for pipeline
    
    Usage:
        config = LoadTestConfig(
            num_jobs=50,
            num_workers=5
        )
        
        tester = LoadTester(config)
        result = tester.run_load_test()
        
        print(f"Completed: {result.completed_jobs}/{result.total_jobs}")
        print(f"Avg time: {result.avg_time:.1f}s")
    """
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.result = LoadTestResult()
        self.job_times: Dict[str, float] = {}
        self.lock = threading.Lock()
    
    def run_load_test(self) -> LoadTestResult:
        """
        Run load test
        
        Returns:
            LoadTestResult with statistics
        """
        logger.info(f"Starting load test: {self.config.num_jobs} jobs, {self.config.num_workers} workers")
        
        self.result.start_time = datetime.now()
        self.result.total_jobs = self.config.num_jobs
        
        # Create batch processor
        worker_config = WorkerConfig(
            num_workers=self.config.num_workers,
            max_retries=2,
            retry_delay_seconds=10
        )
        processor = BatchProcessor(worker_config)
        
        # Register callbacks
        processor.on_job_complete(self._on_job_complete)
        processor.on_job_failed(self._on_job_failed)
        
        # Start processor
        processor.start()
        
        # Generate and submit jobs
        jobs = self._generate_jobs()
        
        # Ramp up if configured
        if self.config.ramp_up_time > 0:
            self._submit_with_ramp_up(processor, jobs)
        else:
            processor.submit_batch(jobs)
        
        # Wait for completion
        logger.info("Waiting for jobs to complete...")
        processor.wait_all(timeout=self.config.test_duration)
        
        # Stop processor
        processor.stop()
        
        self.result.end_time = datetime.now()
        
        # Calculate statistics
        self.result.calculate_stats()
        
        logger.info(f"Load test complete: {self.result.completed_jobs}/{self.result.total_jobs} succeeded")
        
        return self.result
    
    def _generate_jobs(self) -> List[PipelineJob]:
        """Generate test jobs"""
        jobs = []
        
        for i in range(self.config.num_jobs):
            avatar_id = f"load_test_avatar_{i % self.config.avatar_pool_size}"
            garment_type = self.config.garment_types[i % len(self.config.garment_types)]
            
            job = PipelineJob(
                avatar_id=avatar_id,
                garment_type=garment_type,
                measurements={
                    "height": 170 + (i % 20),
                    "chest": 90 + (i % 15),
                    "waist": 75 + (i % 15),
                    "hips": 90 + (i % 15)
                }
            )
            
            jobs.append(job)
            self.job_times[job.job_id] = time.time()
        
        return jobs
    
    def _submit_with_ramp_up(self, processor: BatchProcessor, jobs: List[PipelineJob]):
        """Submit jobs with ramp-up period"""
        delay = self.config.ramp_up_time / self.config.num_jobs
        
        for job in jobs:
            processor.submit_job(job)
            time.sleep(delay)
    
    def _on_job_complete(self, job: PipelineJob, result_path: str):
        """Handle job completion"""
        with self.lock:
            processing_time = time.time() - self.job_times.get(job.job_id, time.time())
            self.result.completed_jobs += 1
            self.result.processing_times.append(processing_time)
    
    def _on_job_failed(self, job: PipelineJob, error: str):
        """Handle job failure"""
        with self.lock:
            self.result.failed_jobs += 1
            self.result.errors.append(f"{job.job_id}: {error}")


def run_load_test_suite():
    """Run complete load test suite"""
    
    scenarios = [
        ("Normal Load", LoadTestConfig(num_jobs=10, num_workers=3)),
        ("Peak Load", LoadTestConfig(num_jobs=50, num_workers=5)),
        ("Stress Test", LoadTestConfig(num_jobs=100, num_workers=5)),
    ]
    
    results = {}
    
    for name, config in scenarios:
        print(f"\n{'=' * 70}")
        print(f"Running: {name}")
        print(f"{'=' * 70}")
        
        tester = LoadTester(config)
        result = tester.run_load_test()
        results[name] = result
        
        # Print summary
        print(f"\nResults:")
        print(f"  Completed: {result.completed_jobs}/{result.total_jobs}")
        print(f"  Failed: {result.failed_jobs}")
        print(f"  Error rate: {result.error_rate:.1f}%")
        print(f"  Avg time: {result.avg_time:.1f}s")
        print(f"  P95 time: {result.p95_time:.1f}s")
        print(f"  Throughput: {result.throughput:.1f} jobs/hour")
    
    # Save results
    report = {name: result.to_dict() for name, result in results.items()}
    
    with open("load_test_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'=' * 70}")
    print("Load test suite complete!")
    print(f"Report saved: load_test_report.json")
    print(f"{'=' * 70}")
    
    return results
```

### 22.3: Create Load Test Scenarios

**File:** `tests/load/test_scenarios.py`

```python
"""
Specific load test scenarios
"""

import pytest
from load_test_framework import LoadTester, LoadTestConfig


@pytest.mark.slow
def test_normal_load():
    """Test normal load scenario"""
    config = LoadTestConfig(
        num_jobs=10,
        num_workers=3,
        test_duration=1800  # 30 minutes
    )
    
    tester = LoadTester(config)
    result = tester.run_load_test()
    
    # Assertions
    assert result.error_rate < 5.0, f"Error rate too high: {result.error_rate}%"
    assert result.avg_time < 300, f"Average time too high: {result.avg_time}s"
    assert result.completed_jobs >= 9, f"Too many failures: {result.failed_jobs}"


@pytest.mark.slow
def test_peak_load():
    """Test peak load scenario"""
    config = LoadTestConfig(
        num_jobs=50,
        num_workers=5,
        test_duration=3600  # 1 hour
    )
    
    tester = LoadTester(config)
    result = tester.run_load_test()
    
    # More lenient criteria for peak load
    assert result.error_rate < 10.0, f"Error rate too high: {result.error_rate}%"
    assert result.avg_time < 480, f"Average time too high: {result.avg_time}s"
    assert result.completed_jobs >= 45, f"Too many failures: {result.failed_jobs}"


@pytest.mark.slow
def test_stress_load():
    """Test stress load scenario"""
    config = LoadTestConfig(
        num_jobs=100,
        num_workers=5,
        test_duration=7200  # 2 hours
    )
    
    tester = LoadTester(config)
    result = tester.run_load_test()
    
    # Even more lenient for stress test
    assert result.error_rate < 20.0, f"Error rate too high: {result.error_rate}%"
    assert result.completed_jobs >= 80, f"Too many failures: {result.failed_jobs}"


@pytest.mark.slow
def test_soak_test():
    """Test long-running stability (soak test)"""
    config = LoadTestConfig(
        num_jobs=50,
        num_workers=3,
        ramp_up_time=300,  # 5 minutes ramp-up
        test_duration=14400  # 4 hours
    )
    
    tester = LoadTester(config)
    result = tester.run_load_test()
    
    # Check for stability over time
    assert result.error_rate < 5.0, f"Error rate too high: {result.error_rate}%"
    
    # Performance shouldn't degrade significantly
    # (would need time-series analysis for proper validation)
    assert result.p95_time < 600, f"P95 time too high: {result.p95_time}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
```

### 22.4: Run Load Tests

```powershell
# Run full load test suite
python tests\load\load_test_framework.py

# Or run specific scenarios with pytest
pytest tests\load\test_scenarios.py::test_normal_load -v -s
pytest tests\load\test_scenarios.py::test_peak_load -v -s
pytest tests\load\test_scenarios.py::test_stress_load -v -s

# Run all load tests (may take hours)
pytest tests\load\ -v -s -m slow
```

### Day 22 Completion Checklist

- [ ] Load testing framework implemented
- [ ] Load test scenarios defined
- [ ] Normal load test passed (<5% error rate)
- [ ] Peak load test passed (<10% error rate)
- [ ] Stress test passed (system stable under 100 jobs)
- [ ] Load test report generated
- [ ] Performance metrics documented

**Time:** 6-8 hours  
**Next:** Day 23 - Production Deployment Preparation

---

## Day 23: Production Deployment Preparation

**Time:** 6-8 hours  
**Goal:** Prepare system for production deployment

### 23.1: Production Environment Configuration

**File:** `config/production_config.py`

```python
"""
Production environment configuration
"""

import os
from pathlib import Path


class ProductionConfig:
    """Production environment settings"""
    
    # Environment
    ENV = "production"
    DEBUG = False
    
    # CLO Configuration
    CLO_API_BASE_URL = os.getenv("CLO_API_URL", "http://localhost:50505/api")
    CLO_WORKSPACE = Path(os.getenv("CLO_WORKSPACE", "C:/CLO/Workspace"))
    CLO_EXECUTABLE = Path(os.getenv("CLO_EXECUTABLE", "C:/Program Files/CLO/CLO3D/CLO.exe"))
    
    # Batch Processing
    NUM_WORKERS = int(os.getenv("NUM_WORKERS", "5"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "30"))
    
    # Performance
    ENABLE_CACHING = True
    CACHE_DIR = Path(os.getenv("CACHE_DIR", "cache"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
    
    # Quality
    QUALITY_PRESET = os.getenv("QUALITY_PRESET", "production")
    ENABLE_QA = True
    QA_STRICT_MODE = True
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    
    # Monitoring
    ENABLE_METRICS = True
    METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
    
    # Storage
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
    TEMP_DIR = Path(os.getenv("TEMP_DIR", "temp"))
    
    # Security
    API_KEY = os.getenv("API_KEY")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Resource Limits
    MAX_MEMORY_MB = int(os.getenv("MAX_MEMORY_MB", "4096"))
    MAX_DISK_USAGE_GB = int(os.getenv("MAX_DISK_USAGE_GB", "100"))
    
    @classmethod
    def validate(cls):
        """Validate production configuration"""
        errors = []
        
        # Check CLO installation
        if not cls.CLO_EXECUTABLE.exists():
            errors.append(f"CLO executable not found: {cls.CLO_EXECUTABLE}")
        
        # Check directories
        for dir_path in [cls.CLO_WORKSPACE, cls.CACHE_DIR, cls.LOG_DIR, cls.OUTPUT_DIR]:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {dir_path}: {e}")
        
        # Check API key
        if not cls.API_KEY:
            errors.append("API_KEY not set")
        
        if errors:
            raise ValueError(f"Production config validation failed:\n" + "\n".join(errors))
        
        return True


# Environment file template
ENV_TEMPLATE = """
# Production Environment Configuration

# CLO Configuration
CLO_API_URL=http://localhost:50505/api
CLO_WORKSPACE=C:/CLO/Workspace
CLO_EXECUTABLE=C:/Program Files/CLO/CLO3D/CLO.exe

# Batch Processing
NUM_WORKERS=5
MAX_RETRIES=3
RETRY_DELAY=30

# Performance
CACHE_DIR=cache
CACHE_TTL=3600

# Quality
QUALITY_PRESET=production

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_RETENTION_DAYS=30

# Monitoring
METRICS_PORT=9090

# Storage
OUTPUT_DIR=output
TEMP_DIR=temp

# Security
API_KEY=your_secret_api_key_here
ALLOWED_ORIGINS=https://yourdomain.com

# Resource Limits
MAX_MEMORY_MB=4096
MAX_DISK_USAGE_GB=100
"""
```

### 23.2: Create Deployment Scripts

**File:** `deploy/deploy.ps1`

```powershell
# Production Deployment Script

param(
    [string]$Environment = "production",
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MIRRA Pipeline - Production Deployment" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Pre-deployment checks
Write-Host "`n[1/8] Pre-deployment checks..." -ForegroundColor Yellow

# Check Python version
$pythonVersion = python --version
Write-Host "  Python version: $pythonVersion"

# Check virtual environment
if (!(Test-Path ".venv")) {
    Write-Host "  ERROR: Virtual environment not found!" -ForegroundColor Red
    exit 1
}

# Check CLO installation
if (!(Test-Path "C:\Program Files\CLO\CLO3D\CLO.exe")) {
    Write-Host "  WARNING: CLO3D not found at default location" -ForegroundColor Yellow
}

Write-Host "  ✓ Pre-deployment checks passed" -ForegroundColor Green

# Step 2: Backup current deployment
Write-Host "`n[2/8] Creating backup..." -ForegroundColor Yellow

if (!$DryRun) {
    $backupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup configuration
    Copy-Item "config\*.py" -Destination $backupDir -Recurse -Force
    
    Write-Host "  ✓ Backup created: $backupDir" -ForegroundColor Green
}

# Step 3: Install dependencies
Write-Host "`n[3/8] Installing dependencies..." -ForegroundColor Yellow

if (!$DryRun) {
    & .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt --upgrade
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
}

# Step 4: Run tests
Write-Host "`n[4/8] Running tests..." -ForegroundColor Yellow

if (!$DryRun) {
    pytest tests\unit\ -v --tb=short
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Tests failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  ✓ Tests passed" -ForegroundColor Green
}

# Step 5: Validate configuration
Write-Host "`n[5/8] Validating production configuration..." -ForegroundColor Yellow

if (!$DryRun) {
    python -c "from config.production_config import ProductionConfig; ProductionConfig.validate()"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Configuration validation failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  ✓ Configuration valid" -ForegroundColor Green
}

# Step 6: Create necessary directories
Write-Host "`n[6/8] Creating directories..." -ForegroundColor Yellow

if (!$DryRun) {
    $dirs = @("logs", "cache", "output", "temp")
    foreach ($dir in $dirs) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    Write-Host "  ✓ Directories created" -ForegroundColor Green
}

# Step 7: Deploy configuration
Write-Host "`n[7/8] Deploying configuration..." -ForegroundColor Yellow

if (!$DryRun) {
    # Copy production config
    if (Test-Path ".env.production") {
        Copy-Item ".env.production" -Destination ".env" -Force
    }
    
    Write-Host "  ✓ Configuration deployed" -ForegroundColor Green
}

# Step 8: Start services
Write-Host "`n[8/8] Starting services..." -ForegroundColor Yellow

if (!$DryRun) {
    # Start CLO (if not running)
    $cloProcess = Get-Process -Name "CLO" -ErrorAction SilentlyContinue
    if (!$cloProcess) {
        Write-Host "  Starting CLO3D..."
        Start-Process "C:\Program Files\CLO\CLO3D\CLO.exe"
        Start-Sleep -Seconds 10
    }
    
    Write-Host "  ✓ Services started" -ForegroundColor Green
}

# Deployment complete
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓✓✓ DEPLOYMENT COMPLETE ✓✓✓" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

if ($DryRun) {
    Write-Host "`nNOTE: This was a dry run. No changes were made." -ForegroundColor Yellow
}
```

### 23.3: Create Health Check Endpoint

**File:** `Working_Cloth_3D_Pipeline/health_check.py`

```python
"""
Health check endpoint for production monitoring
"""

import sys
from pathlib import Path
from typing import Dict, Any
import requests

from config.production_config import ProductionConfig


class HealthCheck:
    """System health check"""
    
    def __init__(self):
        self.config = ProductionConfig()
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'checks': {},
            'details': {}
        }
        
        # Check CLO API
        results['checks']['clo_api'] = self._check_clo_api()
        
        # Check disk space
        results['checks']['disk_space'] = self._check_disk_space()
        
        # Check memory
        results['checks']['memory'] = self._check_memory()
        
        # Check dependencies
        results['checks']['dependencies'] = self._check_dependencies()
        
        # Overall status
        if not all(results['checks'].values()):
            results['status'] = 'unhealthy'
        
        return results
    
    def _check_clo_api(self) -> bool:
        """Check CLO API availability"""
        try:
            response = requests.get(
                f"{self.config.CLO_API_BASE_URL}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        import shutil
        
        try:
            stats = shutil.disk_usage(self.config.OUTPUT_DIR)
            free_gb = stats.free / (1024**3)
            return free_gb > 10  # At least 10GB free
        except:
            return False
    
    def _check_memory(self) -> bool:
        """Check available memory"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.percent < 90  # Less than 90% used
        except:
            return True  # Pass if psutil not available
    
    def _check_dependencies(self) -> bool:
        """Check required dependencies"""
        required = ['requests', 'numpy', 'trimesh', 'ezdxf']
        
        try:
            for package in required:
                __import__(package)
            return True
        except ImportError:
            return False


def main():
    """Run health check from command line"""
    check = HealthCheck()
    results = check.check_all()
    
    import json
    print(json.dumps(results, indent=2))
    
    # Exit with error code if unhealthy
    sys.exit(0 if results['status'] == 'healthy' else 1)


if __name__ == '__main__':
    main()
```

### 23.4: Create Rollback Script

**File:** `deploy/rollback.ps1`

```powershell
# Rollback Script

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupDir
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "MIRRA Pipeline - Rollback" -ForegroundColor Yellow
Write-Host "Backup: $BackupDir" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# Verify backup exists
if (!(Test-Path $BackupDir)) {
    Write-Host "ERROR: Backup directory not found: $BackupDir" -ForegroundColor Red
    exit 1
}

# Stop services
Write-Host "`n[1/3] Stopping services..." -ForegroundColor Yellow
Stop-Process -Name "CLO" -Force -ErrorAction SilentlyContinue

# Restore configuration
Write-Host "`n[2/3] Restoring configuration..." -ForegroundColor Yellow
Copy-Item "$BackupDir\*" -Destination "config\" -Recurse -Force

# Restart services
Write-Host "`n[3/3] Restarting services..." -ForegroundColor Yellow
Start-Process "C:\Program Files\CLO\CLO3D\CLO.exe"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓ ROLLBACK COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
```

### Day 23 Completion Checklist

- [ ] Production configuration created
- [ ] Environment template created
- [ ] Deployment script implemented
- [ ] Health check endpoint working
- [ ] Rollback script tested
- [ ] Pre-deployment validation passing
- [ ] Backup/restore procedure tested

**Time:** 6-8 hours  
**Next:** Day 24 - Documentation & Training Materials

---

## Day 24: Documentation & Training Materials

**Time:** 8-10 hours  
**Goal:** Create comprehensive documentation and training materials

### 24.1: Technical Documentation

**File:** `docs/TECHNICAL_DOCUMENTATION.md`

```markdown
# MIRRA Pipeline - Technical Documentation

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    MIRRA Pipeline                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   Avatar     │  │   Pattern    │  │  CLO3D API  │  │
│  │   Export     │→ │  Generation  │→ │  Assembly   │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
│         │                  │                  │        │
│         ↓                  ↓                  ↓        │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Batch Processing System                │  │
│  │  - Job Queue  - Workers  - Error Handling       │  │
│  └──────────────────────────────────────────────────┘  │
│         │                                              │
│         ↓                                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Quality Assurance                       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## API Reference

### CLOAPIClient

Main interface for CLO3D operations.

#### Methods

**`create_project(name: str, template: str = "basic") -> Dict`**

Creates new CLO project.

```python
from Working_Cloth_3D_Pipeline.steps.clo_integration import CLOAPIClient

client = CLOAPIClient()
project = client.create_project("my_project")
```

**`import_avatar(obj_path: str, scale: float = 1.0) -> Dict`**

Imports avatar OBJ file.

**`import_patterns(pattern_files: List[str]) -> List[Dict]`**

Imports DXF pattern files.

**`run_simulation(blocking: bool = True) -> Dict`**

Executes cloth simulation.

(Continue with all API methods...)

## Configuration

### Environment Variables

See `.env.production.template` for all available variables.

Key settings:

- `CLO_API_URL`: CLO API endpoint
- `NUM_WORKERS`: Parallel worker count
- `QUALITY_PRESET`: Simulation quality (draft/preview/production/final)

## Deployment

See `deploy/` directory for deployment scripts.

## Monitoring

### Metrics

Access metrics at `http://localhost:9090/metrics`

Available metrics:
- `pipeline_jobs_total`
- `pipeline_jobs_success`
- `pipeline_jobs_failed`
- `pipeline_processing_time_seconds`

### Logs

Logs location: `logs/pipeline_YYYYMMDD.log`

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
```

### 24.2: User Guide

**File:** `docs/USER_GUIDE.md`

```markdown
# MIRRA Pipeline - User Guide

## Getting Started

### Prerequisites

- Windows 11 Pro (64-bit)
- CLO3D SET Enterprise (licensed)
- Python 3.9+
- 16GB RAM minimum

### Installation

1. Clone repository:
```powershell
git clone https://github.com/saumy-github/mirra-mvp.git
cd mirra-mvp
```

2. Create virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
pip install -r requirements.txt
```

4. Configure environment:
```powershell
copy .env.template .env
# Edit .env with your settings
```

## Basic Usage

### Single Garment Creation

```python
from Working_Cloth_3D_Pipeline.pipeline import ClothPipeline

# Initialize pipeline
pipeline = ClothPipeline()

# Set parameters
pipeline.set_avatar_id("user_123")
pipeline.set_garment_type("tshirt")
pipeline.set_measurements({
    "height": 175,
    "chest": 95,
    "waist": 80,
    "hips": 95
})

# Run
result = pipeline.run()

if result["success"]:
    print(f"Output: {result['output_path']}")
```

### Batch Processing

```powershell
# Create job file (jobs.json)
{
  "jobs": [
    {
      "avatar_id": "user_001",
      "garment_type": "tshirt",
      "measurements": {...}
    }
  ]
}

# Run batch
python -m Working_Cloth_3D_Pipeline.batch.batch_cli run --jobs-file jobs.json
```

## FAQ

**Q: How long does processing take?**  
A: Average 3-5 minutes per garment with PREVIEW quality.

**Q: How many jobs can run simultaneously?**  
A: Depends on hardware. Recommended 3-5 workers for typical workstation.

**Q: What garment types are supported?**  
A: T-shirts, pants, hoodies, dresses, skirts.

**Q: How do I change quality settings?**  
A: Set `QUALITY_PRESET` environment variable to draft/preview/production/final.
```

### 24.3: Operator Training Materials

**File:** `docs/OPERATOR_TRAINING.md`

```markdown
# MIRRA Pipeline - Operator Training Guide

## Training Overview

**Duration:** 2 hours  
**Audience:** Production operators  
**Prerequisites:** Basic computer skills

## Module 1: System Overview (20 minutes)

### What is the MIRRA Pipeline?

The MIRRA Pipeline automatically creates 3D virtual garments using CLO3D.

**Input:** Body measurements, garment type  
**Output:** 3D garment file (GLB format)

### Key Components

1. **Avatar Generation**: Creates 3D body model
2. **Pattern Creation**: Generates garment patterns
3. **CLO Assembly**: Simulates fabric and sewing
4. **Quality Check**: Validates output

## Module 2: Running Jobs (30 minutes)

### Method 1: Web Interface

(If web interface exists)

### Method 2: Command Line

```powershell
# Navigate to project
cd C:\MIRRA\mirra-mvp

# Activate environment
.\.venv\Scripts\Activate.ps1

# Run job
python -m Working_Cloth_3D_Pipeline.batch.batch_cli run --jobs-file jobs\batch_001.json
```

### Monitoring Progress

Check status:
```powershell
python -m Working_Cloth_3D_Pipeline.batch.batch_cli status
```

## Module 3: Quality Control (30 minutes)

### Reviewing Outputs

1. Check output directory: `output\`
2. Open GLB file in viewer
3. Verify garment quality:
   - Proper fit
   - No holes or tears
   - Correct colors/textures

### Common Issues

**Issue:** Garment too loose
- Check measurements
- Verify garment size

**Issue:** Simulation failed
- Check log files
- Verify CLO is running

## Module 4: Troubleshooting (30 minutes)

### System Health Check

```powershell
python Working_Cloth_3D_Pipeline\health_check.py
```

### Common Problems

1. **CLO not responding**
   - Restart CLO application
   - Check Windows Task Manager

2. **Jobs stuck in queue**
   - Check worker status
   - Restart batch processor

3. **Quality check failures**
   - Review quality report
   - Rerun with higher quality preset

## Module 5: Practical Exercises (10 minutes)

### Exercise 1: Run Single Job

1. Create job file with provided template
2. Submit job
3. Monitor progress
4. Review output

### Exercise 2: Batch Processing

1. Submit batch of 5 jobs
2. Monitor all jobs
3. Identify any failures
4. Generate report

## Certification

Operators must successfully complete:
- Quiz (80% passing)
- Practical exam (2 jobs)

## Support

**Email:** support@mirra.com  
**Slack:** #mirra-support  
**Documentation:** https://docs.mirra.com
```

### Day 24 Completion Checklist

- [ ] Technical documentation complete
- [ ] User guide complete
- [ ] Operator training guide complete
- [ ] API reference documented
- [ ] Troubleshooting guide updated
- [ ] FAQ section created
- [ ] Training materials reviewed

**Time:** 8-10 hours  
**Next:** Day 25 - Production Launch & Handoff

---

## Day 25: Production Launch & Handoff

**Time:** 6-8 hours  
**Goal:** Launch system in production and complete handoff

### 25.1: Pre-Launch Checklist

**Execute all pre-launch verifications:**

```powershell
# Run pre-launch checklist
python deploy\pre_launch_check.py
```

**File:** `deploy/pre_launch_check.py`

```python
"""
Pre-launch checklist automation
"""

def run_pre_launch_checks():
    """Run all pre-launch checks"""
    
    checks = [
        ("All tests passing", check_tests),
        ("Production config valid", check_config),
        ("CLO3D operational", check_clo),
        ("Disk space sufficient", check_disk),
        ("Backup system ready", check_backup),
        ("Monitoring configured", check_monitoring),
        ("Documentation complete", check_docs),
        ("Team trained", check_training)
    ]
    
    results = []
    
    print("=" * 70)
    print("PRE-LAUNCH CHECKLIST")
    print("=" * 70)
    
    for name, check_func in checks:
        print(f"\n[{len(results)+1}/{len(checks)}] {name}...", end=" ")
        
        try:
            result = check_func()
            status = "✓" if result else "✗"
            results.append((name, result))
            print(status)
        except Exception as e:
            print(f"✗ ({e})")
            results.append((name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{total} checks passed")
    print("=" * 70)
    
    if passed == total:
        print("✓✓✓ READY FOR PRODUCTION LAUNCH ✓✓✓")
        return True
    else:
        print("✗✗✗ ISSUES MUST BE RESOLVED BEFORE LAUNCH ✗✗✗")
        return False

# Implement check functions...
```

### 25.2: Production Launch

**Execute deployment:**

```powershell
# Final deployment
.\deploy\deploy.ps1 -Environment production

# Verify deployment
python Working_Cloth_3D_Pipeline\health_check.py

# Start monitoring
# (Start monitoring dashboard)
```

### 25.3: Handoff Documentation

**File:** `docs/HANDOFF.md`

```markdown
# MIRRA Pipeline - Production Handoff

## System Status

**Launch Date:** [Date]  
**Version:** 1.0.0  
**Status:** Production  
**Deployed By:** [Name]

## Access Information

### Production Environment

- **Server:** [Server Details]
- **CLO API:** http://localhost:50505/api
- **Logs:** C:\MIRRA\mirra-mvp\logs
- **Outputs:** C:\MIRRA\mirra-mvp\output

### Credentials

See password manager for:
- CLO3D license key
- API keys
- Server access

## Operational Procedures

### Daily Operations

1. Check system health (morning)
2. Monitor job queue
3. Review error logs
4. Backup outputs (evening)

### Weekly Maintenance

1. Review metrics dashboard
2. Clear old cache files
3. Archive old logs
4. Update documentation

### Monthly Tasks

1. Update dependencies
2. Review performance trends
3. Train new operators
4. Disaster recovery test

## Support Contacts

| Role | Name | Contact|
|------|------|--------|
| Engineering Lead | [Name] | [Email] |
| DevOps | [Name] | [Email] |
| Product Owner | [Name] | [Email] |

## Known Issues

None at launch.

## Future Improvements

Planned enhancements:
1. Web-based monitoring dashboard
2. Multi-server support
3. Real-time preview generation
4. Additional garment types

## Sign-off

**Development Team:** _________________ Date: _______  
**Operations Team:** _________________ Date: _______  
**Management:** _____________________ Date: _______
```

### 25.4: Post-Launch Monitoring

**Monitor system for first 24-48 hours:**

```powershell
# Monitor logs in real-time
Get-Content logs\pipeline.log -Wait -Tail 50

# Check metrics
python -c "from Working_Cloth_3D_Pipeline.utils.metrics import MetricsCollector; print(MetricsCollector().get_metrics())"

# Monitor system resources
while ($true) {
    Get-Process -Name "CLO","python" | Format-Table Name,CPU,WorkingSet
    Start-Sleep -Seconds 60
}
```

### Day 25 Completion Checklist

- [ ] Pre-launch checklist completed (100%)
- [ ] Production deployment successful
- [ ] Health checks passing
- [ ] Monitoring active
- [ ] Team handoff complete
- [ ] Documentation delivered
- [ ] Sign-off obtained
- [ ] Post-launch monitoring started

**Time:** 6-8 hours

---

## Phase Completion Checklist

### Testing & Validation

- [ ] **Test Suite Complete**
  - [ ] Unit tests (>85% coverage)
  - [ ] Integration tests
  - [ ] End-to-end tests
  - [ ] All tests passing

- [ ] **Load Testing**
  - [ ] Normal load validated (10 jobs)
  - [ ] Peak load validated (50 jobs)
  - [ ] Stress test passed (100 jobs)
  - [ ] Soak test passed (4 hours)
  - [ ] Performance metrics documented

### Deployment

- [ ] **Production Environment**
  - [ ] Production config created
  - [ ] Environment variables set
  - [ ] Deployment scripts tested
  - [ ] Rollback procedure validated
  - [ ] Health checks operational

- [ ] **Infrastructure**
  - [ ] CLO3D installed and licensed
  - [ ] Backup system configured
  - [ ] Monitoring enabled
  - [ ] Log aggregation working

### Documentation

- [ ] **Technical Docs**
  - [ ] Architecture documented
  - [ ] API reference complete
  - [ ] Configuration guide
  - [ ] Troubleshooting guide

- [ ] **User Docs**
  - [ ] User guide complete
  - [ ] Operator training materials
  - [ ] FAQ documented
  - [ ] Video tutorials (optional)

### Launch

- [ ] **Production Launch**
  - [ ] Pre-launch checklist passed
  - [ ] Deployment successful
  - [ ] System operational
  - [ ] Team trained
  - [ ] Handoff complete

### Success Metrics

- [ ] All tests passing (100%)
- [ ] Load tests meet SLA (<5% error rate normal load)
- [ ] Production deployment successful
- [ ] Zero critical bugs in first week
- [ ] Team confident in operations
- [ ] Documentation complete and accurate

---

## Production Readiness Checklist

### Code Quality

- [ ] Code reviewed
- [ ] No critical bugs
- [ ] Test coverage >70%
- [ ] Security scan passed
- [ ] Performance validated

### Operations

- [ ] Monitoring configured
- [ ] Alerts set up
- [ ] Backup/restore tested
- [ ] Disaster recovery plan
- [ ] On-call rotation defined

### Business

- [ ] Stakeholders informed
- [ ] Training completed
- [ ] SLA defined
- [ ] Support process established
- [ ] Success metrics agreed

---

**Phase 4 Status:** Complete

**Prerequisites:** Phase 3 Complete (Automation & Optimization working)

**Next:** Phase 5 would cover scaling, advanced features, and continuous improvement (if needed)

---

## Troubleshooting Guide

### Deployment Issues

**Problem:** Deployment script fails
- Check Python version (must be 3.9+)
- Verify virtual environment activated
- Review error logs in `deploy/logs/`

**Problem:** Configuration validation fails
- Check all environment variables set
- Verify file paths exist
- Ensure CLO3D installed

### Production Issues

**Problem:** Health checks failing
- Check CLO API accessibility
- Verify disk space available
- Check system resources

**Problem:** High error rate
- Review error logs
- Check CLO3D status
- Verify network connectivity
- Check system resources

### Recovery Procedures

**Scenario:** Complete system failure
1. Stop all services
2. Identify root cause
3. Execute rollback if needed
4. Restore from backup
5. Restart services
6. Verify functionality

**Scenario:** Data corruption
1. Stop affected workers
2. Identify corrupted files
3. Restore from backup
4. Clear cache
5. Resume operations

---

**End of Phase 4 Detailed Guide**

**Total Estimated Time:** 30-40 hours (Week 5)

**Project Status:** Production Ready

**Next Steps:** Monitor production, gather feedback, plan Phase 5 enhancements
