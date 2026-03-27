# CLO REST Plugin Server Explained

## Purpose of the REST plugin server

The REST plugin server is the control bridge between external Python automation and the CLO3D application runtime.

Without it:

1. Python scripts cannot call CLO operations directly from outside CLO process.
2. Step 3 cannot be automated as a repeatable pipeline.

With it:

1. Python sends HTTP commands.
2. Plugin queues those commands.
3. CLO main thread executes SDK calls safely.

## Where it is implemented

Primary file:

clo_workspace/plugins/RestPlugin.cpp

Related components:

1. clo_workspace/plugins/httplib.h for embedded HTTP server.
2. clo_workspace/plugins/json.hpp for JSON parsing.
3. clo_workspace/plugins/dllmain.cpp and build files for plugin packaging.

## Core architecture

The server uses a two-thread model with explicit queue handoff.

### Thread model

1. Background HTTP thread:
Accepts REST requests, parses JSON, and enqueues command payloads.

2. CLO main thread:
Dequeues and executes CLO SDK operations through ProcessCommandQueue.

Why this design is required:
CLO SDK operations are main-thread sensitive. Calling them directly from HTTP thread can crash or corrupt execution state.

## Command queue mechanism

Main structures in plugin:

1. APICommand:
Holds normalized command type and parameters for all supported operations.

2. CommandResult:
Stores per-command success and message for status reporting.

3. g_commandQueue:
Global queue protected by mutex.

4. g_lastResults:
Result snapshot for recent batch.

Queue flow:

1. Endpoint receives call.
2. Endpoint validates and pushes APICommand into queue.
3. Timer or manual trigger calls ProcessCommandQueue on main thread.
4. Main thread executes command, records result.
5. Status endpoint returns queue and result state.

## How queue draining is triggered

The plugin starts queue draining timer after server startup.

Mechanism:

1. DoFunction menu action starts server and registers Win32 timer.
2. Timer callback runs periodically and checks queue.
3. If commands exist and queue is not already processing, main-thread drain is executed.

Practical effect:
After starting server once in CLO session, Python can keep queuing commands and polling status without repeated menu clicks.

## Main REST endpoints and what they do

### Health and status

1. GET /health
Confirms plugin server availability and version identity.

2. GET /status
Returns queue size, processing flag, loaded pattern count, and last batch results.

### Asset import and scene control

3. POST /new-project
Queues fresh CLO project creation.

4. POST /import-avatar
Queues avatar OBJ import.

5. POST /import-pattern
Queues pattern DXF import.

### Pattern inspection and arrangement

6. GET /patterns/count
Returns loaded pattern count.

7. GET /patterns/{index}
Returns pattern information for index.

8. GET /arrangement-list
Returns arrangement slots reported by CLO.

9. GET /pattern-arrangements
Returns arrangement assignments for currently loaded patterns.

10. POST /arrange-pattern
Queues arrangement slot assignment and position offsets.

### Fabric, seam, simulation

11. POST /set-fabric
Queues fabric assignment to a pattern index.

12. POST /create-seam
Queues seam creation between two pattern edges and directions.

13. POST /simulate
Queues simulation for configured step count.

### Export and save

14. POST /export
Queues GLB or GLTF export using CLO export API options.

15. POST /save-project
Saves CLO project file output.

### Execute helper endpoint

16. POST /execute
Used as queue status or nudge endpoint depending on client behavior and queue state.

## Execution semantics inside ProcessCommandQueue

When queue is drained, each command type maps to a specific CLO API operation.

Examples of internal behavior:

1. Avatar import:
OBJ import with scale handling to reconcile avatar units with CLO expectations.

2. Pattern import:
DXF append import with import options.

3. Arrange pattern:
Set arrangement slot, then set position and orientation.

4. Seam creation:
Add seamline pair group with direction controls.

5. Simulation:
Run utility simulate for requested step count.

6. Export:
Run GLTF export with embedded option for GLB mode.

7. Save project:
Run ZPRJ export path.

## Plugin lifecycle in CLO

Menu integration callbacks:

1. Plugin appears under CLO Plugins menu.
2. First click starts REST server and timer.
3. Subsequent cycles process queued commands automatically and expose status for clients.

## Build and deployment path

Build assets are managed in:

1. clo_workspace/plugins/CMakeLists.txt
2. clo_workspace/plugins/build_rest_plugin.bat
3. clo_workspace/plugins/BUILD_GUIDE.md
4. clo_workspace/plugins/BUILD_INSTRUCTIONS.md

Deployment model:

1. Build DLL.
2. Copy DLL to CLO plugins directory.
3. Start CLO.
4. Start server from plugin menu.

## Relationship to Python automation client

Python client module:

clo_workspace/plugins/clo_automation_steps/client.py

Relationship pattern:

1. Python client wraps endpoint calls.
2. Step modules invoke client methods by pipeline stage.
3. wait_for_queue polls status endpoint until queue drains.

This is the key control loop that turns async plugin queue into deterministic automation behavior.

## Known strengths of this server design

1. Main-thread safety via explicit queue model.
2. Clear endpoint surface for automation steps.
3. Batch result visibility through status endpoint.
4. Resilient operation with queue polling and retry patterns.

## Known limitations and cautions

1. Seams depend on accurate edge indices from generated DXF topology.
2. Arrangement slot matching may vary with avatar and CLO scene state.
3. Export and save steps may require careful sequencing around simulation completion.
4. Plugin behavior can differ across CLO versions if SDK APIs change.

## Why this server is essential for MVP Step 3

Step 3 requires automated virtual try-on at application scale, not manual GUI-only operation.

The REST plugin server provides that automation foundation by:

1. Exposing CLO functions through API.
2. Preserving CLO thread-safety rules.
3. Enabling Python-driven repeatable pipelines.

It is the integration backbone that makes the Step 3 virtual try-on pipeline operational.
