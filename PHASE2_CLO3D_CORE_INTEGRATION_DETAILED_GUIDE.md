# Phase 2: CLO3D Core Integration - Detailed Implementation Guide

**Project:** MIRRA MVP - CLO3D Migration  
**Phase:** 2 of 4 - Core Integration  
**Duration:** Week 2-3 (10 working days)  
**Status:** Ready for Implementation  
**Branch:** `clo3danant`  
**Prerequisites:** Phase 1 Complete

---

## Table of Contents

1. [Phase Overview](#phase-overview)
2. [Prerequisites from Phase 1](#prerequisites-from-phase-1)
3. [Week 2: Foundation Modules](#week-2-foundation-modules)
   - [Day 6: CLO API Client Wrapper](#day-6-clo-api-client-wrapper)
   - [Day 7: Fabric Library System](#day-7-fabric-library-system)
   - [Day 8: Seam Builder Module](#day-8-seam-builder-module)
   - [Day 9: Pattern Integration Testing](#day-9-pattern-integration-testing)
   - [Day 10: Simulation Configuration](#day-10-simulation-configuration)
4. [Week 3: Core Assembly Implementation](#week-3-core-assembly-implementation)
   - [Day 11: Step 5 Assembly Module (Part 1)](#day-11-step-5-assembly-module-part-1)
   - [Day 12: Step 5 Assembly Module (Part 2)](#day-12-step-5-assembly-module-part-2)
   - [Day 13: Color & Texture Application](#day-13-color--texture-application)
   - [Day 14: Pipeline Integration](#day-14-pipeline-integration)
   - [Day 15: End-to-End Testing](#day-15-end-to-end-testing)
5. [Phase Completion Checklist](#phase-completion-checklist)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## Phase Overview

### Starting Point (From Phase 1)

You now have:
✅ CLO3D SET Enterprise installed and licensed  
✅ Avatar export to OBJ format working  
✅ DXF pattern export working  
✅ Test avatars and patterns created  
✅ CLO API accessible and tested  
✅ Basic configuration system in place

### Goals for Phase 2

By the end of Phase 2, you will have:

1. ✅ Complete CLO API wrapper (`clo_client.py`)
2. ✅ Fabric property management system
3. ✅ Automated seam creation system
4. ✅ Full Step 5 replacement (CLO assembly)
5. ✅ Color/texture application
6. ✅ Integrated into main pipeline
7. ✅ End-to-end workflow functional

### Success Criteria

- [ ] Can programmatically create CLO projects
- [ ] Can import avatars and patterns via API
- [ ] Can define and create seams automatically
- [ ] Can apply fabric properties
- [ ] Can run cloth simulation via API
- [ ] Can export final garment (GLB)
- [ ] Full pipeline runs without manual intervention
- [ ] Quality matches or exceeds Blender output

### Time Allocation

| Week | Days | Focus | Deliverable |
|------|------|-------|-------------|
| **Week 2** | 6-10 | Foundation modules | API wrapper, fabric system, seam builder |
| **Week 3** | 11-15 | Assembly implementation | Step 5 replacement, integration |

**Total:** 50-60 hours

---

## Prerequisites from Phase 1

### Verify Phase 1 Completion

Before starting Phase 2, verify all Phase 1 deliverables:

```powershell
# Navigate to project
cd C:\Users\Anant\mirra-mvp

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run Phase 1 validation
python tests\test_phase1_complete.py
```

**Expected output:**
```
============================================================
PHASE 1 COMPLETE INTEGRATION TEST
============================================================

TEST 1: Avatar Generation
✓ PASS: Avatar generated and exported to OBJ

TEST 2: Pattern Generation (DXF)
✓ PASS: 5 pattern files generated

TEST 3: CLO Connection
✓ PASS: CLO API responding

============================================================
TEST SUMMARY
============================================================
✓ PASS: Avatar Generation
✓ PASS: Pattern Generation
✓ PASS: CLO Connection

Total: 3/3 passed
============================================================

🎉 Phase 1 Complete - Ready for Phase 2!
```

### Required Files from Phase 1

Verify these files exist:

```powershell
# Configuration
Test-Path config\clo_config.py
# Should return: True

# Avatar exporter
Test-Path pipeline_star\avatar_exporter_clo.py
# Should return: True

# Pattern exporter
Test-Path Working_Cloth_3D_Pipeline\steps\exporters\dxf_exporter.py
# Should return: True

# Test data
Test-Path test_output\avatars\
Test-Path test_output\patterns\tshirt_test\
# Should return: True for both
```

### Environment Check

```powershell
# Check Python packages
pip list | Select-String -Pattern "ezdxf|trimesh|numpy|requests"

# Expected:
# ezdxf       1.x.x
# trimesh     3.x.x
# numpy       1.x.x
# requests    2.x.x

# Check CLO installation
Test-Path "C:\Program Files\CLO\CLO_SET\CLO.exe"
# Should return: True

# Check branch
git branch
# Should show: * clo3danant
```

---

## Week 2: Foundation Modules

### Week 2 Overview

**Goal:** Build the foundational modules that Phase 3 will use

**Modules to Build:**
1. CLO API Client (high-level wrapper)
2. Fabric Library (property management)
3. Seam Builder (automatic seam generation)
4. Pattern Integration (DXF → CLO workflow)
5. Simulation Configuration (settings management)

---

## Day 6: CLO API Client Wrapper

**Goal:** Create high-level CLO API wrapper for all operations  
**Duration:** 8-10 hours  
**Deliverable:** Complete `clo_client.py` module with full functionality

### Step 6.1: Understanding CLO API Architecture

#### CLO API Overview

CLO3D provides a REST API with these endpoints:

```
Base URL: http://localhost:50505/api

Key Endpoints:
├── /version                    GET    - Get CLO version
├── /project/new               POST   - Create new project
├── /project/{id}              GET    - Get project info
├── /project/{id}/save         POST   - Save project
├── /avatar/import             POST   - Import avatar
├── /avatar/{id}               GET    - Get avatar info
├── /pattern/import            POST   - Import patterns
├── /pattern/{id}              GET    - Get pattern info
├── /fabric/presets            GET    - List fabric presets
├── /fabric/apply              POST   - Apply fabric to pattern
├── /seam/create               POST   - Create seam
├── /simulation/configure      POST   - Set simulation params
├── /simulation/run            POST   - Run simulation
├── /export                    POST   - Export garment
└── /status                    GET    - Get current status
```

#### API Request/Response Format

**Request:**
```json
POST /api/project/new
Content-Type: application/json

{
  "name": "test_project",
  "template": "empty"
}
```

**Response:**
```json
{
  "success": true,
  "project_id": "proj_123abc",
  "name": "test_project",
  "created_at": "2026-02-27T10:00:00Z"
}
```

### Step 6.2: Create CLO Integration Package

#### Package Structure

First, create the package structure:

```powershell
# Create package directory
New-Item -ItemType Directory -Force -Path Working_Cloth_3D_Pipeline\steps\clo_integration

# Create package files
New-Item -ItemType File -Path Working_Cloth_3D_Pipeline\steps\clo_integration\__init__.py
New-Item -ItemType File -Path Working_Cloth_3D_Pipeline\steps\clo_integration\clo_client.py
New-Item -ItemType File -Path Working_Cloth_3D_Pipeline\steps\clo_integration\fabric_library.py
New-Item -ItemType File -Path Working_Cloth_3D_Pipeline\steps\clo_integration\seam_builder.py
New-Item -ItemType File -Path Working_Cloth_3D_Pipeline\steps\clo_integration\simulation_runner.py
New-Item -ItemType File -Path Working_Cloth_3D_Pipeline\steps\clo_integration\exceptions.py

# Verify creation
Get-ChildItem Working_Cloth_3D_Pipeline\steps\clo_integration\
```

**Expected output:**
```
    Directory: C:\Users\Anant\mirra-mvp\Working_Cloth_3D_Pipeline\steps\clo_integration

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a---          2/27/2026  10:00 AM              0 __init__.py
-a---          2/27/2026  10:00 AM              0 clo_client.py
-a---          2/27/2026  10:00 AM              0 exceptions.py
-a---          2/27/2026  10:00 AM              0 fabric_library.py
-a---          2/27/2026  10:00 AM              0 seam_builder.py
-a---          2/27/2026  10:00 AM              0 simulation_runner.py
```

### Step 6.3: Implement Custom Exceptions

**File:** `Working_Cloth_3D_Pipeline\steps\clo_integration\exceptions.py`

```python
"""
CLO3D Integration Exceptions

Custom exception classes for CLO API operations.
"""


class CLOIntegrationError(Exception):
    """Base exception for CLO integration errors."""
    pass


class CLOConnectionError(CLOIntegrationError):
    """Raised when cannot connect to CLO API."""
    
    def __init__(self, message="Cannot connect to CLO API server", url=None):
        self.url = url
        super().__init__(
            f"{message}" + (f" at {url}" if url else "") +
            "\n\nTroubleshooting:\n"
            "1. Ensure CLO3D is running\n"
            "2. Check API is enabled in CLO Preferences\n"
            "3. Verify port 50505 is not blocked\n"
            "4. Try restarting CLO3D"
        )


class CLOProjectError(CLOIntegrationError):
    """Raised when project operation fails."""
    pass


class CLOImportError(CLOIntegrationError):
    """Raised when import operation fails."""
    pass


class CLOSimulationError(CLOIntegrationError):
    """Raised when simulation fails."""
    pass


class CLOExportError(CLOIntegrationError):
    """Raised when export operation fails."""
    pass


class CLOAPIError(CLOIntegrationError):
    """Raised when API returns an error response."""
    
    def __init__(self, message, status_code=None, response_data=None):
        self.status_code = status_code
        self.response_data = response_data
        
        error_msg = f"CLO API Error: {message}"
        if status_code:
            error_msg += f" (Status: {status_code})"
        if response_data:
            error_msg += f"\nResponse: {response_data}"
        
        super().__init__(error_msg)
```

**Test exceptions:**

```powershell
python -c "from Working_Cloth_3D_Pipeline.steps.clo_integration.exceptions import *; print('✓ Exceptions module imported')"
```

### Step 6.4: Implement CLO API Client

**File:** `Working_Cloth_3D_Pipeline\steps\clo_integration\clo_client.py`

```python
"""
CLO3D API Client Wrapper

High-level interface for CLO3D REST API operations.
Handles all communication with CLO3D for garment assembly.
"""
import os
import time
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

import sys
sys.path.append('../../..')
from config.clo_config import (
    CLO_API_BASE_URL,
    CLO_API_HOST,
    CLO_API_PORT,
    CLO_WORKSPACE,
    DEFAULT_SIMULATION_QUALITY,
    DEFAULT_SIMULATION_FRAMES,
    DEFAULT_EXPORT_FORMAT
)

from .exceptions import (
    CLOConnectionError,
    CLOProjectError,
    CLOImportError,
    CLOSimulationError,
    CLOExportError,
    CLOAPIError
)


@dataclass
class CLOProjectInfo:
    """Information about a CLO project."""
    project_id: str
    name: str
    path: Optional[str] = None
    created_at: Optional[str] = None
    has_avatar: bool = False
    pattern_count: int = 0


@dataclass
class CLOAvatarInfo:
    """Information about imported avatar."""
    avatar_id: str
    vertex_count: int
    face_count: int
    height_cm: float
    is_collision: bool = True


@dataclass
class CLOPatternInfo:
    """Information about imported pattern."""
    pattern_id: str
    name: str
    piece_count: int
    bounds: Optional[Dict[str, float]] = None


class CLOAPIClient:
    """
    High-level CLO3D API client.
    
    Manages all interactions with CLO3D API for garment assembly workflow.
    
    Usage:
        with CLOAPIClient() as client:
            project = client.create_project("my_project")
            avatar = client.import_avatar("avatar.obj")
            patterns = client.import_patterns(["pattern1.dxf", "pattern2.dxf"])
            client.run_simulation()
            client.export_garment("output.glb")
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        timeout: int = 30,
        verify_connection: bool = True
    ):
        """
        Initialize CLO API client.
        
        Args:
            base_url: CLO API base URL (default from config)
            workspace_dir: Workspace directory (default from config)
            timeout: Request timeout in seconds
            verify_connection: Check connection on init
        
        Raises:
            CLOConnectionError: If cannot connect to API
        """
        self.base_url = base_url or CLO_API_BASE_URL
        self.workspace = Path(workspace_dir or CLO_WORKSPACE)
        self.timeout = timeout
        
        # Current session state
        self.current_project: Optional[CLOProjectInfo] = None
        self.session = requests.Session()
        
        # Verify connection
        if verify_connection:
            self._verify_connection()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.close()
    
    def close(self):
        """Close session and cleanup."""
        if self.session:
            self.session.close()
    
    def _verify_connection(self):
        """
        Verify CLO API is accessible.
        
        Raises:
            CLOConnectionError: If cannot connect
        """
        try:
            response = self.session.get(
                f"{self.base_url}/version",
                timeout=5
            )
            
            if response.status_code != 200:
                raise CLOConnectionError(
                    f"API returned status {response.status_code}",
                    url=self.base_url
                )
            
        except requests.ConnectionError:
            raise CLOConnectionError(
                "Connection refused",
                url=self.base_url
            )
        except requests.Timeout:
            raise CLOConnectionError(
                "Connection timeout",
                url=self.base_url
            )
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make API request with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            json_data: JSON payload
            files: Files to upload
            data: Form data
            params: URL parameters
        
        Returns:
            Response data as dict
        
        Raises:
            CLOAPIError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                files=files,
                data=data,
                params=params,
                timeout=self.timeout
            )
            
            # Check for errors
            if response.status_code >= 400:
                raise CLOAPIError(
                    f"Request failed: {endpoint}",
                    status_code=response.status_code,
                    response_data=response.text
                )
            
            # Parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If response is not JSON, return empty dict
                return {'status': 'success', 'raw_response': response.text}
        
        except requests.RequestException as e:
            raise CLOAPIError(f"Request error: {e}")
    
    # ============================================================
    # PROJECT MANAGEMENT
    # ============================================================
    
    def create_project(
        self,
        name: str,
        template: str = "empty"
    ) -> CLOProjectInfo:
        """
        Create new CLO project.
        
        Args:
            name: Project name
            template: Project template ('empty', 'male', 'female')
        
        Returns:
            CLOProjectInfo object
        
        Raises:
            CLOProjectError: If creation fails
        """
        try:
            data = self._make_request(
                'POST',
                '/project/new',
                json_data={'name': name, 'template': template}
            )
            
            project_info = CLOProjectInfo(
                project_id=data.get('project_id', ''),
                name=data.get('name', name),
                path=data.get('path'),
                created_at=data.get('created_at')
            )
            
            self.current_project = project_info
            
            return project_info
        
        except CLOAPIError as e:
            raise CLOProjectError(f"Failed to create project: {e}")
    
    def save_project(self, path: Optional[str] = None) -> str:
        """
        Save current project.
        
        Args:
            path: Optional save path (uses default if None)
        
        Returns:
            Saved project path
        
        Raises:
            CLOProjectError: If no project loaded or save fails
        """
        if not self.current_project:
            raise CLOProjectError("No project loaded")
        
        try:
            save_path = path or (
                self.workspace / "projects" / 
                f"{self.current_project.name}.zprj"
            )
            
            data = self._make_request(
                'POST',
                f'/project/{self.current_project.project_id}/save',
                json_data={'path': str(save_path)}
            )
            
            return data.get('path', str(save_path))
        
        except CLOAPIError as e:
            raise CLOProjectError(f"Failed to save project: {e}")
    
    def get_project_info(self) -> CLOProjectInfo:
        """
        Get current project information.
        
        Returns:
            CLOProjectInfo object
        
        Raises:
            CLOProjectError: If no project loaded
        """
        if not self.current_project:
            raise CLOProjectError("No project loaded")
        
        try:
            data = self._make_request(
                'GET',
                f'/project/{self.current_project.project_id}'
            )
            
            # Update project info
            self.current_project.has_avatar = data.get('has_avatar', False)
            self.current_project.pattern_count = data.get('pattern_count', 0)
            
            return self.current_project
        
        except CLOAPIError as e:
            raise CLOProjectError(f"Failed to get project info: {e}")
    
    # ============================================================
    # AVATAR IMPORT
    # ============================================================
    
    def import_avatar(
        self,
        obj_file_path: str,
        scale: float = 1.0,
        units: str = "meters",
        orientation: str = "y-up",
        as_collision: bool = True
    ) -> CLOAvatarInfo:
        """
        Import avatar from OBJ file.
        
        Args:
            obj_file_path: Path to OBJ file
            scale: Scale factor
            units: Unit system ('meters', 'centimeters', 'millimeters')
            orientation: Coordinate system ('y-up' or 'z-up')
            as_collision: Set as collision object
        
        Returns:
            CLOAvatarInfo object
        
        Raises:
            CLOImportError: If import fails
        """
        obj_path = Path(obj_file_path)
        
        if not obj_path.exists():
            raise CLOImportError(f"Avatar file not found: {obj_file_path}")
        
        if not self.current_project:
            raise CLOImportError("No project loaded. Create project first.")
        
        try:
            # Upload file
            with open(obj_path, 'rb') as f:
                files = {'file': (obj_path.name, f, 'model/obj')}
                data_payload = {
                    'project_id': self.current_project.project_id,
                    'scale': str(scale),
                    'units': units,
                    'orientation': orientation,
                    'as_collision': str(as_collision).lower()
                }
                
                data = self._make_request(
                    'POST',
                    '/avatar/import',
                    files=files,
                    data=data_payload
                )
            
            avatar_info = CLOAvatarInfo(
                avatar_id=data.get('avatar_id', ''),
                vertex_count=data.get('vertex_count', 0),
                face_count=data.get('face_count', 0),
                height_cm=data.get('height_cm', 0.0),
                is_collision=as_collision
            )
            
            # Update project info
            self.current_project.has_avatar = True
            
            return avatar_info
        
        except CLOAPIError as e:
            raise CLOImportError(f"Failed to import avatar: {e}")
    
    # ============================================================
    # PATTERN IMPORT
    # ============================================================
    
    def import_patterns(
        self,
        pattern_files: List[str],
        file_format: str = "dxf",
        units: str = "millimeters"
    ) -> List[CLOPatternInfo]:
        """
        Import pattern files.
        
        Args:
            pattern_files: List of pattern file paths
            file_format: File format ('dxf', 'svg', 'ai')
            units: Unit system
        
        Returns:
            List of CLOPatternInfo objects
        
        Raises:
            CLOImportError: If import fails
        """
        if not self.current_project:
            raise CLOImportError("No project loaded")
        
        imported_patterns = []
        
        for pattern_path in pattern_files:
            path = Path(pattern_path)
            
            if not path.exists():
                raise CLOImportError(f"Pattern file not found: {pattern_path}")
            
            try:
                with open(path, 'rb') as f:
                    files = {'file': (path.name, f, f'model/{file_format}')}
                    data_payload = {
                        'project_id': self.current_project.project_id,
                        'file_format': file_format,
                        'units': units
                    }
                    
                    data = self._make_request(
                        'POST',
                        '/pattern/import',
                        files=files,
                        data=data_payload
                    )
                
                pattern_info = CLOPatternInfo(
                    pattern_id=data.get('pattern_id', ''),
                    name=data.get('name', path.stem),
                    piece_count=data.get('piece_count', 1),
                    bounds=data.get('bounds')
                )
                
                imported_patterns.append(pattern_info)
            
            except CLOAPIError as e:
                raise CLOImportError(
                    f"Failed to import pattern {path.name}: {e}"
                )
        
        # Update project info
        self.current_project.pattern_count += len(imported_patterns)
        
        return imported_patterns
    
    # ============================================================
    # FABRIC APPLICATION
    # ============================================================
    
    def get_fabric_presets(self) -> List[str]:
        """
        Get list of available fabric presets.
        
        Returns:
            List of fabric preset names
        """
        try:
            data = self._make_request('GET', '/fabric/presets')
            return data.get('presets', [])
        
        except CLOAPIError:
            # Return default list if API doesn't support this
            return [
                "Cotton Light",
                "Cotton Medium",
                "Cotton Heavy",
                "Denim 12oz",
                "Jersey",
                "Silk",
                "Polyester"
            ]
    
    def apply_fabric(
        self,
        pattern_name: str,
        fabric_preset: Optional[str] = None,
        custom_properties: Optional[Dict[str, float]] = None
    ):
        """
        Apply fabric properties to pattern.
        
        Args:
            pattern_name: Name of pattern piece
            fabric_preset: Preset name from fabric library
            custom_properties: Custom fabric properties (overrides preset)
        
        Raises:
            CLOAPIError: If application fails
        """
        if not self.current_project:
            raise CLOAPIError("No project loaded")
        
        payload = {
            'project_id': self.current_project.project_id,
            'pattern_name': pattern_name
        }
        
        if fabric_preset:
            payload['fabric_preset'] = fabric_preset
        
        if custom_properties:
            payload['custom_properties'] = custom_properties
        
        self._make_request('POST', '/fabric/apply', json_data=payload)
    
    # ============================================================
    # SEAM CREATION
    # ============================================================
    
    def create_seam(
        self,
        pattern1_name: str,
        edge1_name: str,
        pattern2_name: str,
        edge2_name: str,
        seam_type: str = "turn",
        stitch_type: str = "single",
        seam_allowance: float = 10.0
    ) -> str:
        """
        Create seam between two pattern edges.
        
        Args:
            pattern1_name: First pattern piece name
            edge1_name: Edge on first piece
            pattern2_name: Second pattern piece name
            edge2_name: Edge on second piece
            seam_type: Seam type ('turn', 'flat', 'topstitch', 'binding')
            stitch_type: Stitch type ('single', 'double', 'zigzag')
            seam_allowance: Allowance width in mm
        
        Returns:
            Seam ID
        
        Raises:
            CLOAPIError: If seam creation fails
        """
        if not self.current_project:
            raise CLOAPIError("No project loaded")
        
        payload = {
            'project_id': self.current_project.project_id,
            'pattern1_name': pattern1_name,
            'edge1_name': edge1_name,
            'pattern2_name': pattern2_name,
            'edge2_name': edge2_name,
            'seam_type': seam_type,
            'stitch_type': stitch_type,
            'seam_allowance': seam_allowance
        }
        
        data = self._make_request('POST', '/seam/create', json_data=payload)
        return data.get('seam_id', '')
    
    # ============================================================
    # SIMULATION
    # ============================================================
    
    def configure_simulation(
        self,
        quality: str = "high",
        frames: int = 120,
        gravity: float = -9.81,
        ground_plane: bool = True
    ):
        """
        Configure simulation parameters.
        
        Args:
            quality: Simulation quality ('low', 'medium', 'high', 'very_high')
            frames: Number of frames to simulate
            gravity: Gravity in m/s²
            ground_plane: Enable ground collision
        """
        if not self.current_project:
            raise CLOSimulationError("No project loaded")
        
        payload = {
            'project_id': self.current_project.project_id,
            'quality': quality,
            'frames': frames,
            'gravity': gravity,
            'ground_plane': ground_plane
        }
        
        self._make_request('POST', '/simulation/configure', json_data=payload)
    
    def run_simulation(
        self,
        blocking: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run cloth simulation.
        
        Args:
            blocking: Wait for completion
            progress_callback: Optional callback(frame, total_frames)
        
        Returns:
            Simulation result info
        
        Raises:
            CLOSimulationError: If simulation fails
        """
        if not self.current_project:
            raise CLOSimulationError("No project loaded")
        
        try:
            # Start simulation
            data = self._make_request(
                'POST',
                '/simulation/run',
                json_data={'project_id': self.current_project.project_id}
            )
            
            sim_id = data.get('simulation_id', '')
            
            if blocking:
                # Poll for completion
                while True:
                    status_data = self._make_request(
                        'GET',
                        f'/simulation/{sim_id}/status'
                    )
                    
                    status = status_data.get('status')
                    current_frame = status_data.get('current_frame', 0)
                    total_frames = status_data.get('total_frames', 0)
                    
                    if progress_callback and total_frames > 0:
                        progress_callback(current_frame, total_frames)
                    
                    if status == 'completed':
                        return status_data
                    elif status == 'failed':
                        raise CLOSimulationError(
                            f"Simulation failed: {status_data.get('error')}"
                        )
                    
                    time.sleep(0.5)  # Poll every 500ms
            
            return data
        
        except CLOAPIError as e:
            raise CLOSimulationError(f"Simulation error: {e}")
    
    # ============================================================
    # EXPORT
    # ============================================================
    
    def export_garment(
        self,
        output_path: str,
        file_format: str = "glb",
        include_avatar: bool = True,
        include_textures: bool = True,
        texture_resolution: int = 2048
    ) -> str:
        """
        Export simulated garment.
        
        Args:
            output_path: Output file path
            file_format: Export format ('glb', 'fbx', 'obj')
            include_avatar: Include avatar in export
            include_textures: Include textures
            texture_resolution: Texture size (pixels)
        
        Returns:
            Path to exported file
        
        Raises:
            CLOExportError: If export fails
        """
        if not self.current_project:
            raise CLOExportError("No project loaded")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            payload = {
                'project_id': self.current_project.project_id,
                'output_path': str(output_path),
                'file_format': file_format,
                'include_avatar': include_avatar,
                'include_textures': include_textures,
                'texture_resolution': texture_resolution,
                'apply_simulation': True
            }
            
            data = self._make_request('POST', '/export', json_data=payload)
            
            exported_path = data.get('path', str(output_path))
            
            # Verify file exists
            if not Path(exported_path).exists():
                raise CLOExportError(
                    f"Export succeeded but file not found: {exported_path}"
                )
            
            return exported_path
        
        except CLOAPIError as e:
            raise CLOExportError(f"Export failed: {e}")


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def create_clo_client(**kwargs) -> CLOAPIClient:
    """
    Create and return CLO API client.
    
    Args:
        **kwargs: Arguments for CLOAPIClient
    
    Returns:
        CLOAPIClient instance
    """
    return CLOAPIClient(**kwargs)


if __name__ == "__main__":
    # Test CLO client
    print("\n" + "=" * 60)
    print("CLO API Client Test")
    print("=" * 60)
    
    try:
        # Create client
        with CLOAPIClient() as client:
            print("✓ Connected to CLO API")
            
            # Get version
            version_data = client._make_request('GET', '/version')
            print(f"  CLO Version: {version_data.get('version', 'Unknown')}")
            
            # Test project creation
            project = client.create_project("test_client")
            print(f"✓ Created project: {project.name}")
            
            print("\n✓ All tests passed!")
    
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
```

**Test the client:**

```powershell
# Make sure CLO is running with API enabled
# Then test:

python Working_Cloth_3D_Pipeline\steps\clo_integration\clo_client.py
```

### Step 6.5: Create Package __init__.py

**File:** `Working_Cloth_3D_Pipeline\steps\clo_integration\__init__.py`

```python
"""
CLO3D Integration Package

Provides high-level interfaces for CLO3D API integration.
"""

from .clo_client import CLOAPIClient, create_clo_client
from .exceptions import (
    CLOIntegrationError,
    CLOConnectionError,
    CLOProjectError,
    CLOImportError,
    CLOSimulationError,
    CLOExportError,
    CLOAPIError
)

__all__ = [
    'CLOAPIClient',
    'create_clo_client',
    'CLOIntegrationError',
    'CLOConnectionError',
    'CLOProjectError',
    'CLOImportError',
    'CLOSimulationError',
    'CLOExportError',
    'CLOAPIError'
]

__version__ = '1.0.0'
```

### Step 6.6: Create Comprehensive Client Tests

**File:** `tests\test_clo_client.py`

```python
"""
Comprehensive tests for CLO API Client.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Working_Cloth_3D_Pipeline.steps.clo_integration import (
    CLOAPIClient,
    CLOConnectionError,
    CLOProjectError
)


def test_client_connection():
    """Test basic client connection."""
    print("\nTest 1: Client Connection")
    try:
        with CLOAPIClient() as client:
            print("  ✓ Connected to CLO API")
            return True
    except CLOConnectionError as e:
        print(f"  ✗ Connection failed: {e}")
        return False


def test_project_creation():
    """Test project creation."""
    print("\nTest 2: Project Creation")
    try:
        with CLOAPIClient() as client:
            project = client.create_project("test_project_001")
            print(f"  ✓ Created project: {project.name}")
            print(f"    Project ID: {project.project_id}")
            return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_avatar_import():
    """Test avatar import."""
    print("\nTest 3: Avatar Import")
    
    # Find test avatar
    avatar_dir = Path("pipeline_star/generated/clo_avatars")
    obj_files = list(avatar_dir.glob("*.obj"))
    
    if not obj_files:
        print("  ⚠ Skipped: No test avatar found")
        return True
    
    try:
        with CLOAPIClient() as client:
            # Create project
            project = client.create_project("test_avatar_import")
            
            # Import avatar
            avatar = client.import_avatar(str(obj_files[0]))
            print(f"  ✓ Imported avatar")
            print(f"    Vertices: {avatar.vertex_count:,}")
            print(f"    Faces: {avatar.face_count:,}")
            print(f"    Height: {avatar.height_cm:.1f} cm")
            return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_pattern_import():
    """Test pattern import."""
    print("\nTest 4: Pattern Import")
    
    # Find test patterns
    pattern_dir = Path("test_output/patterns/tshirt_test")
    dxf_files = list(pattern_dir.glob("*.dxf"))
    
    if not dxf_files:
        print("  ⚠ Skipped: No test patterns found")
        return True
    
    try:
        with CLOAPIClient() as client:
            # Create project
            project = client.create_project("test_pattern_import")
            
            # Import patterns (first 2 only for speed)
            patterns = client.import_patterns(
                [str(f) for f in dxf_files[:2]]
            )
            print(f"  ✓ Imported {len(patterns)} patterns")
            for p in patterns:
                print(f"    - {p.name}")
            return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_fabric_presets():
    """Test fabric preset listing."""
    print("\nTest 5: Fabric Presets")
    try:
        with CLOAPIClient() as client:
            presets = client.get_fabric_presets()
            print(f"  ✓ Found {len(presets)} fabric presets")
            if presets:
                print(f"    Examples: {', '.join(presets[:3])}")
            return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CLO API Client Test Suite")
    print("=" * 60)
    
    tests = [
        test_client_connection,
        test_project_creation,
        test_avatar_import,
        test_pattern_import,
        test_fabric_presets
    ]
    
    results = []
    for test in tests:
        try:
            passed = test()
            results.append(passed)
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Run client tests:**

```powershell
python tests\test_clo_client.py
```

### Day 6 Completion Checklist

- [ ] `clo_integration` package created
- [ ] Custom exceptions implemented
- [ ] `CLOAPIClient` class implemented (all methods)
- [ ] Package `__init__.py` created
- [ ] Client can connect to CLO API
- [ ] Can create projects
- [ ] Can import avatars
- [ ] Can import patterns
- [ ] Can get fabric presets
- [ ] All client tests pass

**Deliverables:**
- `clo_integration/exceptions.py` - Custom exceptions
- `clo_integration/clo_client.py` - API client (~600 lines)
- `clo_integration/__init__.py` - Package init
- `tests/test_clo_client.py` - Test suite

**Next:** Day 7 - Fabric Library System

---

## Day 7: Fabric Library System

**Goal:** Create fabric property management system  
**Duration:** 6-8 hours  
**Deliverable:** Complete fabric library with preset mappings

### Step 7.1: Understanding Fabric Properties

#### Physical Fabric Properties

CLO3D simulates fabric using these key properties:

| Property | Unit | Range | Description |
|----------|------|-------|-------------|
| **Weight** | g/m² | 50-500 | Fabric mass per area |
| **Thickness** | mm | 0.1-3.0 | Fabric thickness |
| **Stretch (Warp)** | % | 0-100 | Horizontal stretch |
| **Stretch (Weft)** | % | 0-100 | Vertical stretch |
| **Shear Stiffness** | N/m | 10-200 | Resistance to shear |
| **Bending Stiffness** | N⋅m | 0.01-10 | Resistance to bending |
| **Friction** | - | 0-1 | Surface friction |
| **Air Drag** | - | 0-5 | Air resistance |
| **Damping** | - | 1-20 | Energy dissipation |
| **Density** | kg/m³ | 0.1-1.0 | Volume density |

#### Common Fabric Types

| Fabric | Weight | Stretch | Bending | Use Case |
|--------|--------|---------|---------|----------|
| **Cotton Light** | 150 g/m² | 15% | 0.3 | T-shirts, summer wear |
| **Cotton Medium** | 200 g/m² | 15% | 0.5 | Shirts, casual wear |
| **Cotton Heavy** | 300 g/m² | 10% | 1.5 | Jackets, heavy shirts |
| **Jersey** | 180 g/m² | 40% | 0.2 | Stretchy tops, activewear |
| **Denim** | 400 g/m² | 5% | 3.0 | Jeans, denim jackets |
| **Silk** | 50 g/m² | 5% | 0.1 | Dresses, scarves |
| **Polyester** | 120 g/m² | 20% | 0.4 | Sportswear, outerwear |

### Step 7.2: Implement Fabric Library

**File:** `Working_Cloth_3D_Pipeline\steps\clo_integration\fabric_library.py`

```python
"""
Fabric Library System

Manages fabric properties and presets for CLO3D simulation.
Provides mappings between garment types and appropriate fabrics.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class FabricWeight(Enum):
    """Fabric weight categories."""
    VERY_LIGHT = "very_light"  # <100 g/m²
    LIGHT = "light"  # 100-150 g/m²
    MEDIUM = "medium"  # 150-250 g/m²
    HEAVY = "heavy"  # 250-400 g/m²
    VERY_HEAVY = "very_heavy"  # >400 g/m²


class StretchType(Enum):
    """Fabric stretch characteristics."""
    NON_STRETCH = "non_stretch"  # <5%
    LOW_STRETCH = "low_stretch"  # 5-15%
    MEDIUM_STRETCH = "medium_stretch"  # 15-30%
    HIGH_STRETCH = "high_stretch"  # 30-50%
    SUPER_STRETCH = "super_stretch"  # >50%


@dataclass
class FabricProperties:
    """
    Physical properties of fabric for CLO simulation.
    
    All properties are calibrated for realistic drape and fit.
    """
    # Identification
    name: str
    description: str = ""
    
    # CLO preset (if using built-in preset)
    clo_preset_name: Optional[str] = None
    
    # Physical properties
    weight: float = 200.0  # g/m² (grams per square meter)
    thickness: float = 0.5  # mm (millimeters)
    
    # Mechanical properties
    stretch_warp: float = 15.0  # % stretch in warp direction (horizontal)
    stretch_weft: float = 15.0  # % stretch in weft direction (vertical)
    shear_stiffness: float = 50.0  # N/m - resistance to shear deformation
    bending_stiffness: float = 0.5  # N⋅m - how stiff/flexible fabric is
    
    # Surface properties
    friction: float = 0.3  # Coefficient of friction (0-1)
    air_drag: float = 0.5  # Air resistance coefficient
    
    # Simulation properties
    damping: float = 5.0  # Energy dissipation (higher = less bouncy)
    density: float = 0.3  # kg/m³ - volume density
    
    # Material appearance (optional)
    color: Optional[tuple] = None  # RGB (0-1)
    roughness: float = 0.8  # Surface roughness (0=smooth, 1=rough)
    metallic: float = 0.0  # Metallic factor (0=non-metal, 1=metal)
    
    # Metadata
    category: Optional[str] = None  # e.g., "cotton", "synthetic", "knit"
    suitable_for: List[str] = None  # List of garment types
    
    def __post_init__(self):
        """Initialize default values."""
        if self.suitable_for is None:
            self.suitable_for = []
    
    def to_clo_format(self) -> Dict[str, Any]:
        """
        Convert to CLO API format.
        
        Returns:
            Dict suitable for CLO API
        """
        return {
            'weight': self.weight,
            'thickness': self.thickness,
            'stretch_warp': self.stretch_warp,
            'stretch_weft': self.stretch_weft,
            'shear_stiffness': self.shear_stiffness,
            'bending_stiffness': self.bending_stiffness,
            'friction': self.friction,
            'air_drag': self.air_drag,
            'damping': self.damping,
            'density': self.density
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================
# FABRIC PRESET LIBRARY
# ============================================================

FABRIC_PRESETS: Dict[str, FabricProperties] = {
    # -------------------- COTTON FAMILY --------------------
    
    "cotton_tshirt": FabricProperties(
        name="Cotton T-Shirt",
        description="Lightweight cotton jersey for T-shirts",
        clo_preset_name="Cotton Light",
        weight=150,
        thickness=0.4,
        stretch_warp=15,
        stretch_weft=15,
        shear_stiffness=40,
        bending_stiffness=0.3,
        friction=0.35,
        air_drag=0.5,
        damping=5,
        density=0.28,
        category="cotton",
        suitable_for=["tshirt", "tank_top", "underwear"]
    ),
    
    "cotton_medium": FabricProperties(
        name="Cotton Medium",
        description="Standard cotton for casual shirts",
        clo_preset_name="Cotton Medium",
        weight=200,
        thickness=0.5,
        stretch_warp=15,
        stretch_weft=15,
        shear_stiffness=50,
        bending_stiffness=0.5,
        friction=0.35,
        air_drag=0.6,
        damping=6,
        density=0.30,
        category="cotton",
        suitable_for=["shirt", "blouse", "casual_top"]
    ),
    
    "cotton_heavy": FabricProperties(
        name="Cotton Heavy",
        description="Heavy cotton for jackets and outerwear",
        clo_preset_name="Cotton Heavy",
        weight=300,
        thickness=0.8,
        stretch_warp=10,
        stretch_weft=10,
        shear_stiffness=70,
        bending_stiffness=1.5,
        friction=0.4,
        air_drag=0.8,
        damping=8,
        density=0.35,
        category="cotton",
        suitable_for=["jacket", "coat", "heavy_shirt"]
    ),
    
    # -------------------- KNIT FAMILY --------------------
    
    "jersey": FabricProperties(
        name="Jersey Knit",
        description="Stretchy jersey for activewear",
        clo_preset_name="Jersey",
        weight=180,
        thickness=0.6,
        stretch_warp=40,
        stretch_weft=30,
        shear_stiffness=30,
        bending_stiffness=0.2,
        friction=0.25,
        air_drag=0.4,
        damping=4,
        density=0.25,
        category="knit",
        suitable_for=["activewear", "stretchy_top", "bodysuit"]
    ),
    
    "rib_knit": FabricProperties(
        name="Rib Knit",
        description="Ribbed knit for fitted garments",
        weight=220,
        thickness=0.7,
        stretch_warp=50,
        stretch_weft=40,
        shear_stiffness=35,
        bending_stiffness=0.3,
        friction=0.3,
        air_drag=0.5,
        damping=5,
        density=0.27,
        category="knit",
        suitable_for=["fitted_top", "turtleneck", "cuffs"]
    ),
    
    # -------------------- DENIM FAMILY --------------------
    
    "denim_light": FabricProperties(
        name="Denim Light (8oz)",
        description="Lightweight denim for summer wear",
        weight=250,
        thickness=0.7,
        stretch_warp=8,
        stretch_weft=5,
        shear_stiffness=80,
        bending_stiffness=2.0,
        friction=0.45,
        air_drag=1.0,
        damping=10,
        density=0.38,
        category="denim",
        suitable_for=["jeans", "denim_shirt"]
    ),
    
    "denim_medium": FabricProperties(
        name="Denim Medium (12oz)",
        description="Standard denim for jeans",
        clo_preset_name="Denim 12oz",
        weight=400,
        thickness=1.0,
        stretch_warp=5,
        stretch_weft=3,
        shear_stiffness=100,
        bending_stiffness=3.0,
        friction=0.5,
        air_drag=1.2,
        damping=12,
        density=0.40,
        category="denim",
        suitable_for=["jeans", "denim_jacket"]
    ),
    
    "denim_stretch": FabricProperties(
        name="Stretch Denim",
        description="Stretch denim with elastane",
        weight=350,
        thickness=0.9,
        stretch_warp=25,
        stretch_weft=20,
        shear_stiffness=70,
        bending_stiffness=2.2,
        friction=0.45,
        air_drag=1.0,
        damping=10,
        density=0.38,
        category="denim",
        suitable_for=["jeans", "jeggings"]
    ),
    
    # -------------------- LUXURY FABRICS --------------------
    
    "silk": FabricProperties(
        name="Silk",
        description="Lightweight silk for dresses",
        clo_preset_name="Silk",
        weight=50,
        thickness=0.2,
        stretch_warp=5,
        stretch_weft=5,
        shear_stiffness=20,
        bending_stiffness=0.1,
        friction=0.15,
        air_drag=0.3,
        damping=3,
        density=0.20,
        category="luxury",
        suitable_for=["dress", "blouse", "scarf"]
    ),
    
    "satin": FabricProperties(
        name="Satin",
        description="Smooth satin with subtle sheen",
        weight=120,
        thickness=0.3,
        stretch_warp=10,
        stretch_weft=10,
        shear_stiffness=25,
        bending_stiffness=0.15,
        friction=0.1,
        air_drag=0.4,
        damping=3,
        density=0.22,
        category="luxury",
        suitable_for=["dress", "lingerie", "formal_wear"]
    ),
    
    # -------------------- SYNTHETIC FABRICS --------------------
    
    "polyester": FabricProperties(
        name="Polyester",
        description="Standard polyester for sportswear",
        clo_preset_name="Polyester",
        weight=120,
        thickness=0.4,
        stretch_warp=20,
        stretch_weft=15,
        shear_stiffness=35,
        bending_stiffness=0.4,
        friction=0.2,
        air_drag=0.3,
        damping=4,
        density=0.24,
        category="synthetic",
        suitable_for=["activewear", "windbreaker", "sportswear"]
    ),
    
    "nylon": FabricProperties(
        name="Nylon",
        description="Durable nylon for outerwear",
        weight=80,
        thickness=0.3,
        stretch_warp=25,
        stretch_weft=20,
        shear_stiffness=30,
        bending_stiffness=0.3,
        friction=0.15,
        air_drag=0.2,
        damping=3,
        density=0.22,
        category="synthetic",
        suitable_for=["windbreaker", "raincoat", "activewear"]
    ),
    
    "spandex_blend": FabricProperties(
        name="Spandex Blend",
        description="High-stretch fabric with spandex",
        weight=200,
        thickness=0.5,
        stretch_warp=60,
        stretch_weft=50,
        shear_stiffness=25,
        bending_stiffness=0.2,
        friction=0.25,
        air_drag=0.4,
        damping=4,
        density=0.26,
        category="synthetic",
        suitable_for=["activewear", "leggings", "swimwear"]
    ),
    
    # -------------------- SPECIAL PURPOSE --------------------
    
    "fleece": FabricProperties(
        name="Fleece",
        description="Soft fleece for hoodies and sweatshirts",
        weight=280,
        thickness=1.2,
        stretch_warp=20,
        stretch_weft=15,
        shear_stiffness=40,
        bending_stiffness=0.6,
        friction=0.5,
        air_drag=1.5,
        damping=8,
        density=0.32,
        category="special",
        suitable_for=["hoodie", "sweatshirt", "jacket_lining"]
    ),
    
    "canvas": FabricProperties(
        name="Canvas",
        description="Heavy canvas for bags and sturdy garments",
        weight=450,
        thickness=1.2,
        stretch_warp=3,
        stretch_weft=3,
        shear_stiffness=120,
        bending_stiffness=4.0,
        friction=0.6,
        air_drag=1.5,
        damping=15,
        density=0.45,
        category="special",
        suitable_for=["jacket", "bag", "apron"]
    ),
    
    "linen": FabricProperties(
        name="Linen",
        description="Natural linen for summer wear",
        weight=180,
        thickness=0.5,
        stretch_warp=8,
        stretch_weft=8,
        shear_stiffness=45,
        bending_stiffness=0.4,
        friction=0.4,
        air_drag=0.7,
        damping=6,
        density=0.28,
        category="natural",
        suitable_for=["summer_shirt", "dress", "pants"]
    ),
}


# ============================================================
# GARMENT TYPE TO FABRIC MAPPING
# ============================================================

GARMENT_FABRIC_MAP: Dict[str, str] = {
    # Tops
    "tshirt": "cotton_tshirt",
    "tank_top": "cotton_tshirt",
    "polo": "jersey",
    "shirt": "cotton_medium",
    "blouse": "silk",
    "sweater": "jersey",
    "hoodie": "fleece",
    "sweatshirt": "fleece",
    
    # Bottoms
    "jeans": "denim_medium",
    "pants": "cotton_medium",
    "shorts": "cotton_medium",
    "leggings": "spandex_blend",
    "skirt": "cotton_medium",
    
    # Dresses
    "dress": "silk",
    "gown": "satin",
    
    # Outerwear
    "jacket": "cotton_heavy",
    "coat": "canvas",
    "windbreaker": "nylon",
    "raincoat": "nylon",
    
    # Activewear
    "activewear": "polyester",
    "sportswear": "polyester",
    "swimwear": "spandex_blend",
    "yoga_pants": "spandex_blend",
    
    # Underwear
    "underwear": "cotton_tshirt",
    "bra": "spandex_blend",
    "lingerie": "satin",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_fabric_for_garment(garment_type: str) -> FabricProperties:
    """
    Get appropriate fabric for garment type.
    
    Args:
        garment_type: Type of garment (e.g., 'tshirt', 'jeans')
    
    Returns:
        FabricProperties object
    
    Example:
        >>> fabric = get_fabric_for_garment('tshirt')
        >>> print(fabric.name)
        Cotton T-Shirt
    """
    garment_key = garment_type.lower().replace(' ', '_').replace('-', '_')
    fabric_key = GARMENT_FABRIC_MAP.get(garment_key, 'cotton_medium')
    
    return FABRIC_PRESETS[fabric_key]


def get_fabric_by_name(fabric_name: str) -> Optional[FabricProperties]:
    """
    Get fabric by name.
    
    Args:
        fabric_name: Name of fabric preset
    
    Returns:
        FabricProperties object or None if not found
    """
    return FABRIC_PRESETS.get(fabric_name)


def list_all_fabrics() -> List[str]:
    """
    Get list of all available fabrics.
    
    Returns:
        List of fabric names
    """
    return list(FABRIC_PRESETS.keys())


def get_fabrics_by_category(category: str) -> Dict[str, FabricProperties]:
    """
    Get all fabrics in a category.
    
    Args:
        category: Category name ('cotton', 'knit', 'denim', etc.)
    
    Returns:
        Dict of fabric_name: FabricProperties
    """
    return {
        name: fabric
        for name, fabric in FABRIC_PRESETS.items()
        if fabric.category == category
    }


def get_fabrics_suitable_for(garment_type: str) -> List[FabricProperties]:
    """
    Get all fabrics suitable for a garment type.
    
    Args:
        garment_type: Type of garment
    
    Returns:
        List of suitable FabricProperties
    """
    suitable = []
    for fabric in FABRIC_PRESETS.values():
        if garment_type in fabric.suitable_for:
            suitable.append(fabric)
    return suitable


def create_custom_fabric(
    name: str,
    base_fabric: str = "cotton_medium",
    **overrides
) -> FabricProperties:
    """
    Create custom fabric based on existing preset.
    
    Args:
        name: Name for custom fabric
        base_fabric: Base fabric to start from
        **overrides: Properties to override
    
    Returns:
        New FabricProperties object
    
    Example:
        >>> custom = create_custom_fabric(
        ...     "My Cotton",
        ...     base_fabric="cotton_medium",
        ...     weight=250,
        ...     stretch_warp=20
        ... )
    """
    base = FABRIC_PRESETS.get(base_fabric)
    if not base:
        raise ValueError(f"Base fabric '{base_fabric}' not found")
    
    # Copy base properties
    props = base.to_dict()
    
    # Update with overrides
    props.update(overrides)
    props['name'] = name
    props['clo_preset_name'] = None  # Custom fabric, no preset
    
    return FabricProperties(**props)


# ============================================================
# FABRIC LIBRARY CLASS
# ============================================================

class FabricLibrary:
    """
    Fabric library manager.
    
    Provides access to fabric presets and custom fabric creation.
    """
    
    def __init__(self):
        """Initialize fabric library."""
        self.presets = FABRIC_PRESETS.copy()
        self.custom_fabrics: Dict[str, FabricProperties] = {}
    
    def get(self, name: str) -> Optional[FabricProperties]:
        """Get fabric by name (checks custom then presets)."""
        return self.custom_fabrics.get(name) or self.presets.get(name)
    
    def add_custom(self, fabric: FabricProperties):
        """Add custom fabric to library."""
        self.custom_fabrics[fabric.name] = fabric
    
    def list_all(self) -> List[str]:
        """List all fabric names."""
        return list(self.presets.keys()) + list(self.custom_fabrics.keys())
    
    def search(self, query: str) -> List[FabricProperties]:
        """Search fabrics by name or description."""
        query_lower = query.lower()
        results = []
        
        for fabric in list(self.presets.values()) + list(self.custom_fabrics.values()):
            if (query_lower in fabric.name.lower() or
                query_lower in fabric.description.lower()):
                results.append(fabric)
        
        return results


if __name__ == "__main__":
    # Test fabric library
    print("\n" + "=" * 60)
    print("Fabric Library Test")
    print("=" * 60)
    
    print(f"\nTotal fabrics: {len(FABRIC_PRESETS)}")
    
    print("\nFabric categories:")
    categories = set(f.category for f in FABRIC_PRESETS.values() if f.category)
    for cat in sorted(categories):
        count = len(get_fabrics_by_category(cat))
        print(f"  {cat}: {count} fabrics")
    
    print("\nTest: Get fabric for T-shirt")
    fabric = get_fabric_for_garment('tshirt')
    print(f"  Fabric: {fabric.name}")
    print(f"  Weight: {fabric.weight} g/m²")
    print(f"  Stretch: {fabric.stretch_warp}%")
    print(f"  Bending: {fabric.bending_stiffness}")
    
    print("\nTest: Create custom fabric")
    custom = create_custom_fabric(
        "My Custom Cotton",
        base_fabric="cotton_medium",
        weight=250,
        stretch_warp=20
    )
    print(f"  Created: {custom.name}")
    print(f"  Weight: {custom.weight} g/m²")
    print(f"  Stretch: {custom.stretch_warp}%")
    
    print("\n✓ All tests passed!")
```

### Step 7.3:Create Fabric Library Tests

**File:** `tests\test_fabric_library.py`

```python
"""
Tests for fabric library system.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Working_Cloth_3D_Pipeline.steps.clo_integration.fabric_library import (
    FabricProperties,
    FABRIC_PRESETS,
    get_fabric_for_garment,
    get_fabric_by_name,
    list_all_fabrics,
    get_fabrics_by_category,
    create_custom_fabric,
    FabricLibrary
)


def test_fabric_presets():
    """Test fabric preset availability."""
    print("\nTest 1: Fabric Presets")
    
    required_fabrics = [
        'cotton_tshirt',
        'cotton_medium',
        'jersey',
        'denim_medium',
        'silk'
    ]
    
    missing = []
    for fabric_name in required_fabrics:
        if fabric_name not in FABRIC_PRESETS:
            missing.append(fabric_name)
    
    if missing:
        print(f"  ✗ Missing fabrics: {missing}")
        return False
    
    print(f"  ✓ All required fabrics present")
    print(f"  Total fabrics: {len(FABRIC_PRESETS)}")
    return True


def test_garment_mapping():
    """Test garment to fabric mapping."""
    print("\nTest 2: Garment Mapping")
    
    test_garments = [
        ('tshirt', 'cotton_tshirt'),
        ('jeans', 'denim_medium'),
        ('dress', 'silk'),
        ('hoodie', 'fleece')
    ]
    
    for garment, expected_fabric in test_garments:
        fabric = get_fabric_for_garment(garment)
        if expected_fabric not in fabric.name.lower().replace(' ', '_'):
            print(f"  ✗ {garment} → got {fabric.name}, expected {expected_fabric}")
            return False
    
    print(f"  ✓ All garment mappings correct")
    return True


def test_fabric_properties():
    """Test fabric properties are valid."""
    print("\nTest 3: Fabric Properties")
    
    for name, fabric in FABRIC_PRESETS.items():
        # Check required fields
        if not fabric.name:
            print(f"  ✗ {name}: Missing name")
            return False
        
        # Check reasonable ranges
        if fabric.weight < 0 or fabric.weight > 1000:
            print(f"  ✗ {name}: Invalid weight {fabric.weight}")
            return False
        
        if fabric.thickness < 0 or fabric.thickness > 10:
            print(f"  ✗ {name}: Invalid thickness {fabric.thickness}")
            return False
    
    print(f"  ✓ All fabric properties valid")
    return True


def test_custom_fabric():
    """Test custom fabric creation."""
    print("\nTest 4: Custom Fabric")
    
    try:
        custom = create_custom_fabric(
            "Test Custom",
            base_fabric="cotton_medium",
            weight=250,
            stretch_warp=25
        )
        
        if custom.name != "Test Custom":
            print(f"  ✗ Name mismatch")
            return False
        
        if custom.weight != 250:
            print(f"  ✗ Weight not applied")
            return False
        
        print(f"  ✓ Custom fabric created successfully")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_fabric_library_class():
    """Test FabricLibrary class."""
    print("\nTest 5: FabricLibrary Class")
    
    try:
        library = FabricLibrary()
        
        # Test get
        fabric = library.get('cotton_tshirt')
        if not fabric:
            print(f"  ✗ Could not get fabric")
            return False
        
        # Test add custom
        custom = create_custom_fabric("Custom Test", base_fabric="cotton_medium")
        library.add_custom(custom)
        
        retrieved = library.get("Custom Test")
        if not retrieved:
            print(f"  ✗ Could not retrieve custom fabric")
            return False
        
        print(f"  ✓ FabricLibrary working correctly")
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Fabric Library Test Suite")
    print("=" * 60)
    
    tests = [
        test_fabric_presets,
        test_garment_mapping,
        test_fabric_properties,
        test_custom_fabric,
        test_fabric_library_class
    ]
    
    results = []
    for test in tests:
        try:
            passed = test()
            results.append(passed)
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Run fabric library tests:**

```powershell
python tests\test_fabric_library.py
```

### Day 7 Completion Checklist

- [ ] Fabric properties dataclass created
- [ ] 15+ fabric presets defined
- [ ] Garment-to-fabric mapping created
- [ ] Helper functions implemented
- [ ] FabricLibrary class created
- [ ] All fabric tests pass
- [ ] Documentation complete

**Deliverables:**
- `clo_integration/fabric_library.py` - Complete fabric system (~700 lines)
- `tests/test_fabric_library.py` - Test suite
- Fabric property documentation

**Next:** Day 8 - Seam Builder Module

---

*[Document continues with Days 8-15, following the same extreme detail level. Due to length constraints, I'll indicate the structure continues]*

**Remaining Days Summary:**

- **Day 8:** Seam Builder (automatic seam generation for T-shirts, pants, etc.)
- **Day 9:** Pattern Integration Testing (DXF → CLO workflow validation)
- **Day 10:** Simulation Configuration (quality presets, performance tuning)
- **Day 11-12:** Step 5 Assembly Module (main replacement, color/texture)
- **Day 13:** Color & Texture Application (from Step 3 results)
- **Day 14:** Pipeline Integration (connect all modules)
- **Day 15:** End-to-End Testing (full workflow validation)

Would you like me to continue with the remaining days (8-15) in the same extreme detail?

---

## Phase Completion Checklist

### ✅ Core Deliverables

- [ ] **CLO Integration Package**
  - [ ] `clo_client.py` - API wrapper (complete)
  - [ ] `fabric_library.py` - Fabric management (complete)
  - [ ] `seam_builder.py` - Seam generation
  - [ ] `simulation_runner.py` - Simulation control
  - [ ] `exceptions.py` - Custom exceptions (complete)

- [ ] **Step 5 Replacement**
  - [ ] `step5_clo_assembly.py` - Main assembly module
  - [ ] Color/texture application
  - [ ] Pattern positioning
  - [ ] Automated sewing

- [ ] **Pipeline Integration**
  - [ ] Modified `pipeline.py`
  - [ ] Configuration updates
  - [ ] Backward compatibility

- [ ] **Testing**
  - [ ] Unit tests for all modules
  - [ ] Integration tests
  - [ ] End-to-end workflow test
  - [ ] Performance benchmarks

---

**Phase 2 Status:** In Progress (Days 6-7 Complete)

**Branch:** `clo3danant`

**Next:** Continue with Days 8-15
