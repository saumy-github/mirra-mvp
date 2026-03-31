# **macOS CLO REST Plugin - Complete Build & Implementation Guide**

## **Overview**

This is the **active planning document** for building a **full embedded REST server inside CLO3D on macOS**.

Before implementation begins, also read:

* `.agent/plans/critical.md`

The target is **functional parity with the existing Windows REST plug-in**, while also making the architecture safer and more explicit where the Windows implementation currently relies on assumptions that may not hold on macOS.

This project is **not**:

* converting a `.dll` into a `.dylib`
* reusing a built-in CLO inbound REST service
* exposing only a few test endpoints

This project **is**:

* building a real macOS plug-in that loads inside CLO
* starting an embedded HTTP server inside the CLO process
* accepting requests from external tools on `localhost`
* dispatching all CLO SDK work onto the CLO main thread
* returning structured JSON responses to external callers

The intended control loop is:

1. External automation calls `http://127.0.0.1:50505/...`
2. The plug-in validates and normalizes the request
3. The plug-in converts the request into a typed command
4. The command is scheduled for main-thread execution
5. CLO SDK APIs execute on the main thread only
6. Results are stored and returned through the REST layer

---

## **1. Facts Confirmed from Official CLO Docs**

### **1.1 Build and packaging facts**

The current official CLO developer docs confirm:

* macOS C++ plug-ins use **`.dylib`**
* the normal output naming pattern is `build/Release/libYourPlugin.dylib`
* plug-ins must be built in **Release** mode
* CLO documents **Qt 5.15.16** as the required Qt version for C++ plug-ins

### **1.2 Installation and loading facts**

The docs also confirm:

* the default macOS plug-in directory is **`$HOME/Documents/CLO/Plugins`**
* CLO supports extra plug-in search paths through `defaultPlugInFolders.txt`
* plug-ins can also be added through **Plugin Manager**
* macOS General API plug-ins can use arbitrary file names
* Library and Event plug-ins are stricter about file names and are case-sensitive on macOS

### **1.3 Plug-in types available on macOS**

CLO currently supports:

* **`.dylib`** plug-ins
* **`.py`** plug-ins

Python plug-ins matter because they provide a fallback option for an internal control bridge, but they do **not** remove the need for a proper embedded REST server if we want external tools to call CLO directly over HTTP.

### **1.4 REST-specific fact**

CLO exposes a built-in **`REST_API`**, but it is an **outbound HTTP client API**.

It provides helpers such as:

* `CallRESTGet`
* `CallRESTPost`
* multipart upload helpers
* async callback request helpers
* PUT helpers

This means:

* CLO can call **out** to external services
* CLO does **not** ship an inbound REST server that exposes CLO to external callers

### **1.5 Final conclusion from docs**

There is **no official prebuilt inbound REST server** on `developer.clo3d.com` that can replace this project.

We still need to build our own embedded server inside the macOS plug-in.

---

## **2. Goal, Scope, and Compatibility Target**

### **2.1 Primary goal**

Build a macOS plug-in that exposes the same practical REST surface as the current Windows plug-in and allows a client to automate:

* project reset
* avatar import
* DXF pattern import
* pattern inspection
* arrangement discovery
* pattern arrangement
* fabric assignment
* seam creation
* simulation
* export
* project save
* queue status tracking

### **2.2 External contract target**

The macOS server should preserve the existing Windows route structure wherever feasible:

* `GET /health`
* `GET /status`
* `GET /patterns/count`
* `GET /patterns/{index}`
* `GET /arrangement-list`
* `GET /pattern-arrangements`
* `POST /new-project`
* `POST /import-avatar`
* `POST /import-pattern`
* `POST /arrange-pattern`
* `POST /set-fabric`
* `POST /create-seam`
* `POST /simulate`
* `POST /export`
* `POST /save-project`
* `POST /execute`

### **2.3 Scope that is in**

This plan includes:

* the macOS plug-in binary
* embedded HTTP server lifecycle
* main-thread dispatch design
* route validation and error handling
* command queue and result store
* build/install/runtime debugging steps
* acceptance criteria for each phase

### **2.4 Scope that is out**

This plan does not assume:

* UI redesign inside CLO
* remote network exposure beyond `localhost`
* cloud deployment
* authentication for external untrusted networks
* replacing the Windows plug-in

### **2.5 Compatibility rule**

The macOS plug-in should remain **client-compatible** with the Windows plug-in as far as possible:

* same route names
* same HTTP methods
* same request JSON field names
* same high-level success and error structure

Any necessary platform-specific deviation must be documented explicitly.

### **2.6 Canonical compatibility target: the current `vto/` pipeline**

For this project, the real source of truth is **not** an old README or a generic plug-in idea.

The real compatibility target is the current Windows-side orchestration code under:

* `vto/run_vto.py`
* `vto/clo_automation_client.py`
* `vto/clo_automation_steps/client.py`
* `vto/clo_automation_steps/pipeline.py`
* `vto/clo_automation_steps/step_*.py`

The macOS REST plug-in must be designed so that these existing Python flows can run against it with **no workflow rewrite** and ideally **no client code change**.

That means the macOS server is considered successful only if it can drive the same pipeline sequence that Windows drives today.

### **2.7 Practical execution target**

The intended compatibility bar is:

* `python vto/clo_automation_client.py`
* `python vto/clo_automation_client.py test`
* `python vto/clo_automation_client.py status`
* `python vto/run_vto.py`

must all remain viable client entrypoints for the macOS server.

`vto/run_vto.py` is especially important because it is the canonical orchestrator for selecting an avatar run, selecting a product run, creating a VTO run folder, and then launching CLO automation using resolved asset paths.

### **2.8 What this changes in the plan**

The plan must now guarantee:

* the exact route names used by `vto/clo_automation_steps/client.py`
* the exact JSON field names used by that client
* the queue polling semantics used by `wait_for_queue()`
* the same assumptions around avatar import, pattern import order, arrangement discovery, seam creation, and simulation timing
* the same behavior when avatar input is missing or when arrangement slots are unavailable

---

## **2A. Canonical Windows VTO Pipeline Contract**

### **2A.1 Fixed pipeline order**

The macOS REST server must support this exact logical order from the current Windows VTO pipeline:

1. Health check
2. New project
3. Import avatar
4. Import patterns
5. Verify pattern count
6. Read pattern info
7. Read arrangement slots
8. Arrange patterns
9. Apply fabric
10. Create seams
11. Simulate
12. Export/save note stage

### **2A.2 Current step-by-step behavior in `vto/`**

The current orchestration expects the following behavior:

* **Step 1**: `GET /health`
  * success is determined by `status == "ok"`
* **Step 2**: `POST /new-project`
  * then `wait_for_queue(timeout=15)`
* **Step 3**: `POST /import-avatar`
  * only if avatar exists
  * then `wait_for_queue(timeout=30)`
  * if avatar is missing, the pipeline continues but simulation is later skipped
* **Step 4**: `POST /import-pattern` for each pattern in a fixed order
  * `front_panel.dxf`
  * `back_panel.dxf`
  * `sleeve_left.dxf`
  * `sleeve_right.dxf`
  * then `wait_for_queue(timeout=60)`
* **Step 5**: `GET /status`
  * pipeline reads `patterns_loaded`
  * if `patterns_loaded == 0`, pipeline aborts
* **Step 6**: `GET /patterns/{index}` and `GET /arrangement-list`
* **Step 7**: `POST /arrange-pattern` for indices `0..3`
  * uses slot ids when available
  * uses `-1` if no slot was found
  * uses `offset_z = 100`
  * uses `orientation = 0`
  * then `wait_for_queue(timeout=15)`
* **Step 8**: `POST /set-fabric`
  * fabric index `0` for every loaded pattern
  * then `wait_for_queue(timeout=15)`
* **Step 9**: `POST /create-seam`
  * uses a seam map, currently defaulting to the 26-entry `DEFAULT_SEAMS`
  * then `wait_for_queue(timeout=60)`
* **Step 10**: `POST /simulate` with `steps = 150`
  * only if avatar was loaded
  * then `wait_for_queue(timeout=300)`
* **Step 11**: export/save is currently manual in the `vto` pipeline
  * however the REST server should still implement `/export` and `/save-project` so the pipeline can later re-enable them without server redesign

### **2A.3 Fixed pattern import order**

The server must preserve the expected pattern index mapping created by import order:

* `0` = `front_panel.dxf`
* `1` = `back_panel.dxf`
* `2` = `sleeve_left.dxf`
* `3` = `sleeve_right.dxf`

This is critical because the seam map and arrangement logic depend on those indices.

### **2A.4 Arrangement assumptions used by the current pipeline**

The current Windows-side `vto` pipeline:

* queries `/arrangement-list`
* searches for keywords in slot metadata
* maps to:
  * `front`
  * `back`
  * `left sleeve`
  * `right sleeve`
* falls back to `-1` if no slot match is found

Therefore the macOS server must support:

* returning arrangement slot data with stable `index` fields
* allowing `arrangement_index = -1` in `/arrange-pattern`
* allowing position-only arrangement when no slot is available

### **2A.5 Queue semantics expected by the current client**

The current client behavior is not generic; it expects specific queue semantics:

* `GET /status` returns:
  * `queue_size`
  * `queue_processing`
  * `patterns_loaded`
  * `last_results`
* `wait_for_queue()` treats the queue as drained only when:
  * `queue_size == 0`
  * `queue_processing == false`
* if the queue is non-empty and not processing for more than about 3 seconds,
  the client sends:
  * `POST /execute`

This means the macOS server must support **both**:

* automatic queue draining
* a compatible `/execute` route for queue nudge / compatibility behavior

### **2A.6 Path handling expected by the current client**

The current Python client converts file paths to POSIX-style strings before sending them.

So the macOS server should assume request paths arrive as:

* absolute POSIX paths
* UTF-8 JSON strings

and should normalize them safely before use.

### **2A.7 Status behavior expected at pipeline end**

At the end of the pipeline, `run_pipeline()` calls `/status` again and expects:

* `last_results` to contain the most recent executed command results
* each result to expose at least:
  * `type`
  * `success`
  * `message`

This means status reporting is not optional; it is part of the execution contract.

---

## **3. Core Architectural Principles**

### **3.1 Thread-safety principle**

The most important rule in this project is:

**The HTTP server thread must never call CLO SDK APIs directly.**

That includes:

* `IMPORT_API`
* `PATTERN_API`
* `UTILITY_API`
* `EXPORT_API`

The safe pattern is:

1. HTTP thread receives request
2. HTTP thread validates request
3. HTTP thread converts request to a typed command
4. Main-thread dispatcher executes the command
5. Result is returned to the HTTP layer

### **3.2 Treat reads as main-thread work**

Even if a CLO API call looks read-only, the macOS implementation should assume it still belongs on the main thread unless the macOS SDK sample clearly proves otherwise.

This means endpoints like:

* `/patterns/count`
* `/patterns/{index}`
* `/arrangement-list`
* `/pattern-arrangements`

should also be routed through the main-thread dispatcher.

### **3.3 Localhost-only server**

The server should bind to:

* `127.0.0.1` by default

and should **not** expose itself on all interfaces unless there is a later explicit requirement.

### **3.4 Production shape**

The server should be designed from the start as a real automation service, not a demo:

* deterministic command execution
* explicit lifecycle
* clear result tracking
* explicit timeouts
* clean shutdown behavior
* crash-resistant request handling

---

## **4. Suggested Internal Source Layout**

To keep the macOS port maintainable, the implementation should be split into platform-neutral and platform-specific pieces.

### **4.1 Suggested high-level split**

* `plugin_core/`
  * route definitions
  * JSON parsing helpers
  * command structures
  * result structures
  * queue manager
  * status serialization
* `platform_macos/`
  * plug-in entrypoints
  * Qt / lifecycle integration
  * timer hookup
  * startup / shutdown glue
* `sdk_bridge/`
  * one function per CLO action
  * import helpers
  * arrangement helpers
  * seam helpers
  * export helpers

### **4.2 Why this split helps**

This separation makes it easier to:

* preserve route parity with Windows
* test queue and route logic without touching macOS lifecycle code
* keep macOS-specific timer and unload behavior isolated
* add a future Linux or other platform variant if CLO ever supports it

---

## **5. Command Queue and Result Model**

### **5.1 What not to do**

Do **not** use:

* `std::queue<std::function<void()>>`
* a closure-only queue with no typed payload
* processing while holding the queue mutex
* fire-and-forget actions with no result id

That approach makes debugging and reliable HTTP responses much harder.

### **5.2 Recommended command structure**

Use a typed `APICommand` structure similar to the Windows design, but make it stricter.

Each command should contain:

* `request_id`
* `command_type`
* `is_sync`
* typed parameters for the relevant endpoint
* enqueue timestamp
* optional timeout budget

### **5.3 Recommended result structure**

Each command result should contain:

* `request_id`
* `command_type`
* `success`
* `message`
* optional payload object
* start timestamp
* end timestamp
* duration

### **5.4 Queue processing rules**

The queue should follow these rules:

1. Lock only long enough to inspect or move queued commands
2. Move commands into a local batch
3. Release the queue mutex
4. Execute batch items on the main thread
5. Store results separately
6. Signal sync waiters if needed

### **5.5 Sync vs async commands**

The queue must support both execution styles:

* **async commands**
  * used by most write endpoints
  * return quickly after queueing
  * later visible through `/status`
* **sync commands**
  * used by read endpoints that must reply immediately
  * HTTP thread waits for the main-thread result
  * wait must have a timeout

### **5.6 Timeout behavior**

Recommended behavior:

* sync read wait timeout: start with `2-5 seconds`
* if a sync command times out:
  * return `500` or `503`
  * include a structured timeout message
  * do not leave the caller hanging indefinitely

---

## **6. Main-Thread Dispatch Strategy**

### **6.1 Why this section matters**

The queue is only half the solution. The harder macOS problem is:

**How do we guarantee queued work actually runs on the CLO main thread reliably?**

### **6.2 Windows reference**

The existing Windows plug-in uses a timer-based queue drain after startup.

### **6.3 macOS candidate approach**

The leading macOS approach is:

* start the server from the plug-in
* create a main-thread-owned Qt timer
* periodically drain queued commands on the main thread

### **6.4 Validation checklist for the timer**

The timer must be proven to:

* be created on the right thread
* keep firing while CLO is idle
* not depend on repeated manual menu clicks
* survive repeated requests
* shut down cleanly when CLO exits or the plug-in unloads

### **6.5 Recommended initial interval**

Start with:

* `100 ms` to `250 ms`

Do **not** start at `16 ms` unless later performance testing shows that is needed.

The queue does not need a game-loop-grade refresh rate.

### **6.6 If QTimer fails**

If QTimer does not behave reliably inside the macOS General API plug-in:

1. verify the SDK sample for any startup or periodic callback
2. verify whether another Qt-hosted lifecycle hook is more reliable
3. only then consider a fallback host model

The fallback should preserve the same external REST contract.

---

## **7. REST Route Design**

### **7.1 General response shape**

Prefer a consistent response shape:

```json
{
  "success": true,
  "message": "human-readable summary",
  "request_id": "optional-id",
  "data": {}
}
```

For errors:

```json
{
  "success": false,
  "error": "machine-usable summary",
  "message": "human-readable explanation"
}
```

### **7.1A Route compatibility rule for `vto/clo_automation_steps/client.py`**

The macOS server must accept the exact payload shapes sent today by the Windows VTO client.

The minimum route contract is:

* `GET /health`
* `GET /status`
* `GET /patterns/count`
* `GET /patterns/{index}`
* `GET /arrangement-list`
* `GET /pattern-arrangements`
* `POST /new-project` with body `{}`
* `POST /import-avatar` with `{"path": "..."}`
* `POST /import-pattern` with `{"path": "..."}`
* `POST /arrange-pattern` with:
  * `pattern_index`
  * `arrangement_index`
  * `position.x`
  * `position.y`
  * `position.offset`
  * `orientation`
* `POST /set-fabric` with:
  * `pattern_index`
  * `fabric_index`
* `POST /create-seam` with:
  * `patternA_index`
  * `lineA_index`
  * `patternB_index`
  * `lineB_index`
  * `directionA`
  * `directionB`
* `POST /simulate` with `{"steps": N}`
* `POST /export` with:
  * `path`
  * `format`
* `POST /save-project` with:
  * `path`
  * `thumbnail`
* `POST /execute` with `{}`

If the macOS server changes any of these field names, the existing `vto` pipeline will break.

### **7.2 Route categories**

Group routes internally into three categories:

* **health/status**
* **read-only CLO scene inspection**
* **mutating CLO operations**

### **7.3 Health and status routes**

#### `GET /health`

Purpose:

* prove server is running
* return plug-in identity and version

Suggested response fields:

* server name
* version
* platform
* plugin_loaded
* `status: "ok"`

#### `GET /status`

Purpose:

* expose queue state
* expose last results
* expose current server state

Suggested response fields:

* `queue_size`
* `queue_processing`
* `server_running`
* `patterns_loaded`
* `last_results`
* `last_error`

Minimum compatibility fields required by the current client:

* `queue_size`
* `queue_processing`
* `patterns_loaded`
* `last_results`

### **7.4 Read routes**

#### `GET /patterns/count`

Main-thread sync call.

Return:

* count
* success
* request id

Minimum compatibility field:

* `count`

#### `GET /patterns/{index}`

Main-thread sync call.

Return:

* requested index
* parsed pattern info
* clear error if index is invalid

Minimum compatibility field:

* `info`

#### `GET /arrangement-list`

Main-thread sync call.

Return:

* list of arrangement slots
* slot indices
* raw CLO keys if available

Minimum compatibility fields:

* `slots`
* each slot should expose `index`

#### `GET /pattern-arrangements`

Main-thread sync call.

Return:

* each pattern index
* arrangement info returned by CLO

### **7.5 Mutating routes**

#### `POST /new-project`

Queue:

* project reset command

Validate:

* no request body required

Return immediately:

* queued status
* request id
* success boolean

#### `POST /import-avatar`

Request body:

```json
{ "path": "/absolute/path/to/avatar.obj" }
```

Validate:

* path exists
* extension is expected
* path is normalized before queueing

Execution:

* import avatar on main thread
* apply expected import options

Compatibility note:

* the current Windows behavior scales the avatar appropriately for CLO
* the macOS implementation must preserve the same avatar-import semantics so the `vto` simulation step behaves the same way

#### `POST /import-pattern`

Request body:

```json
{ "path": "/absolute/path/to/pattern.dxf" }
```

Validate:

* path exists
* extension is `.dxf`

Execution:

* append import via CLO import API

Compatibility note:

* import order must be preserved because the seam map depends on pattern indices

#### `POST /arrange-pattern`

Validate:

* pattern index is non-negative
* arrangement index is valid if provided
* numeric position values are sane

Execution:

* optional arrangement assignment
* optional position update
* optional orientation update

Compatibility note:

* the current `vto` client sends `position.offset`, not `position.z`
* the macOS server must accept exactly that field name
* `arrangement_index = -1` must be treated as valid fallback behavior

#### `POST /set-fabric`

Validate:

* pattern index
* fabric index

Execution:

* assign project fabric index to the target pattern

Compatibility note:

* the current pipeline always uses `fabric_index = 0`
* the server should treat this as the first project fabric and keep behavior aligned with Windows

#### `POST /create-seam`

Validate:

* both pattern indices exist or are at least non-negative
* line indices are provided
* directions default sensibly

Execution:

* call seam pair creation on main thread

Compatibility note:

* the current VTO pipeline can submit 26 seam commands in sequence
* the macOS queue and result reporting must remain stable under that burst

#### `POST /simulate`

Validate:

* steps provided or default
* steps are in a sane range

Execution:

* queue simulation command

Compatibility note:

* the current pipeline sends `steps = 150`
* the queue must tolerate a longer drain time here, because `wait_for_queue(timeout=300)` is the expected client behavior

#### `POST /export`

Validate:

* output path provided
* format is allowed

Execution:

* queue export command
* preserve options for GLB vs GLTF

Compatibility note:

* export is currently not executed by the default `vto` step list
* it must still be implemented so the pipeline can re-enable it later without server redesign

#### `POST /save-project`

Validate:

* output path provided
* save destination directory is valid

Execution:

* queue save command

Compatibility note:

* save is currently not executed by the default `vto` step list
* it must still be implemented for parity with the Windows server and future VTO re-enablement

#### `POST /execute`

Purpose:

* optional compatibility route
* returns queue state
* may be kept as a no-op status helper if timer-based drain is automatic

Compatibility note:

* the current `wait_for_queue()` actively uses this route as a fallback nudge
* therefore `/execute` must remain present even if automatic draining works perfectly

---

## **8. CLO API Mapping for This Server**

### **8.1 IMPORT_API**

Confirmed useful APIs:

* `ImportOBJ`
* `ImportDXF`
* `ImportAvatar`

Planned endpoint mapping:

* `/import-avatar` -> avatar import
* `/import-pattern` -> DXF import

### **8.2 PATTERN_API**

Confirmed useful APIs:

* `GetPatternCount`
* `GetPatternInformation`
* `GetArrangementList`
* `SetArrangementPosition`
* `SetArrangementOrientation`
* `AddSeamlinePairGroup`

Planned endpoint mapping:

* `/patterns/count`
* `/patterns/{index}`
* `/arrangement-list`
* `/pattern-arrangements`
* `/arrange-pattern`
* `/create-seam`

### **8.3 UTILITY_API**

Confirmed useful APIs:

* `NewProject`
* `Simulate`

Planned endpoint mapping:

* `/new-project`
* `/simulate`

### **8.4 EXPORT_API**

Confirmed useful APIs:

* `ExportGLTF`
* `ExportZPrj`

Planned endpoint mapping:

* `/export`
* `/save-project`

### **8.5 REST_API**

Useful only if the plug-in later needs to call an external service from inside CLO.

Examples:

* upload status to external service
* call a remote manifest service
* notify an orchestrator

It is **not** part of the inbound REST server implementation.

---

## **9. Build Requirements and Toolchain Setup**

### **9.1 Required software**

Install and verify:

* CLO3D macOS build
* matching CLO SDK version
* Xcode Command Line Tools
* CMake
* Qt **5.15.16**

### **9.2 Architecture plan**

Start with:

* `arm64`

Reason:

* simpler first target
* most likely current production macOS environment
* fewer mixed-architecture surprises

After stability:

* add universal build support if truly needed

### **9.3 Configure example**

```bash
mkdir -p build
cd build

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCLO_SDK_PATH="/Users/Shared/CLO_SDK_v2025..." \
  -DQt5_DIR="/path/to/Qt/5.15.16/macos/lib/cmake/Qt5"

cmake --build . --config Release
```

### **9.4 CMake requirements**

The macOS CMake config should explicitly handle:

* `CMAKE_MACOSX_RPATH ON`
* correct Qt discovery
* correct CLO include directories
* correct CLO library directories
* correct output directory
* correct exported symbol setup for macOS

### **9.5 RPATH and loader strategy**

Prefer:

* imported Qt targets
* correct `@rpath`
* minimal manual path surgery

Use `install_name_tool` only as a repair step when debugging a loader issue.

### **9.6 Verify build artifacts**

After build, verify:

* the `.dylib` exists
* architecture matches target
* required libraries resolve cleanly

Useful commands:

```bash
file build/Release/libRestPlugin.dylib
otool -L build/Release/libRestPlugin.dylib
```

---

## **10. Install, Registration, and Startup**

### **10.1 Preferred install path**

```bash
mkdir -p "$HOME/Documents/CLO/Plugins"
cp build/Release/libRestPlugin.dylib "$HOME/Documents/CLO/Plugins/"
```

### **10.2 Alternative registration path**

Use **Plugin Manager** if:

* auto-loading from the default plug-in folder does not occur
* you need to test a plug-in outside the default folder

### **10.3 Avoid as the default plan**

Do not build the normal workflow around copying into the app bundle at:

* `/Applications/CLO3D_OnlineAuth.app/Contents/PlugIns/`

unless later testing proves it is required for a specific deployment case.

### **10.4 Expected startup flow**

The ideal startup sequence is:

1. CLO loads plug-in
2. plug-in is visible in CLO
3. user triggers plug-in once to start server
4. server starts background listener
5. main-thread drain mechanism starts
6. later requests are processed without repeated manual clicks

---

## **11. Lifecycle and Shutdown Design**

### **11.1 Startup requirements**

The plug-in must:

* start the server only once
* avoid duplicate timers
* avoid duplicate listener threads
* expose clean startup diagnostics

### **11.2 Runtime requirements**

The plug-in must track:

* whether server is running
* whether queue is currently processing
* how many commands are queued
* the last result batch
* whether the timer is active

### **11.3 Shutdown requirements**

On CLO quit or plug-in unload:

* stop accepting new work
* stop the server
* stop the timer
* allow the listener thread to exit
* avoid dangling callbacks
* avoid detached-thread shutdown surprises

### **11.4 Logging requirements**

At minimum, log:

* server start
* server stop
* port bind failure
* queue start
* queue finish
* command failure
* shutdown path entered

---

## **12. Detailed Development Phases**

### **Phase 1 - macOS ABI and minimal plug-in load**

#### Goal

Prove the smallest possible macOS CLO plug-in can load successfully.

#### Work in this phase

1. Build a minimal macOS General API plug-in from the SDK-compatible structure
2. Confirm exported entrypoints and naming are correct
3. Confirm the plug-in appears in CLO
4. Add minimal logging or visible proof of execution

#### Deliverable

* a `.dylib` that CLO loads and can invoke

#### Acceptance criteria

* no dyld crash on startup
* no Qt loader error
* plug-in visible in CLO
* user can invoke the plug-in once

#### Failure signals

* plug-in not listed
* immediate crash on launch
* unresolved Qt or CLO library dependencies

---

### **Phase 2 - proven main-thread dispatch**

#### Goal

Prove a background-originated task can be executed reliably on the CLO main thread.

#### Work in this phase

1. Create queue structure
2. Add a trivial command type such as message display or no-op marker
3. Trigger the command from a background thread
4. Execute it on the main thread using the candidate dispatch mechanism
5. Repeat multiple times to verify stability

#### Deliverable

* a repeatable main-thread dispatch path

#### Acceptance criteria

* no direct CLO call from background thread
* repeated dispatch works
* no reliance on manual repeated clicking

#### Failure signals

* timer fires only once
* timer never fires while CLO is idle
* queued work executes only after another UI action

---

### **Phase 3 - embedded HTTP server and health route**

#### Goal

Start the HTTP server inside CLO and expose `/health`.

#### Work in this phase

1. Embed the HTTP server library
2. Create server startup logic
3. Bind to `127.0.0.1:50505`
4. Add `/health`
5. Add duplicate-start protection

#### Deliverable

* running local HTTP server inside CLO

#### Acceptance criteria

* `GET /health` responds successfully
* server survives repeated requests
* repeated startup attempts do not spawn duplicate listeners
* the route returns `status == "ok"` so the existing `vto` client health check passes

#### Failure signals

* port bind failure not surfaced clearly
* server thread keeps spawning on repeated clicks
* health route blocks or hangs

---

### **Phase 4 - sync read endpoints**

#### Goal

Implement read endpoints through main-thread sync jobs.

#### Work in this phase

1. Add request id generation
2. Add promise/future or equivalent waiting mechanism
3. Implement:
   * `/patterns/count`
   * `/patterns/{index}`
   * `/arrangement-list`
   * `/pattern-arrangements`
4. Add timeout handling
5. Add structured error JSON

#### Deliverable

* safe immediate-response inspection endpoints

#### Acceptance criteria

* each read route works without HTTP-thread CLO calls
* invalid index produces a clear error
* timeout path returns structured failure
* `/status` returns the fields expected by `vto/clo_automation_steps/client.py`
* `/arrangement-list` returns slot objects with stable `index` fields

#### Failure signals

* deadlock between HTTP thread and main thread
* sync request hangs forever
* route only works after unrelated UI interaction

---

### **Phase 5 - queued mutating endpoints**

#### Goal

Implement the write routes with result tracking.

#### Work in this phase

1. Implement `/new-project`
2. Implement `/import-avatar`
3. Implement `/import-pattern`
4. Implement `/arrange-pattern`
5. Implement `/set-fabric`
6. Implement `/create-seam`
7. Implement `/simulate`
8. Implement `/export`
9. Implement `/save-project`
10. Keep `/execute` as a compatibility status helper if automatic draining is already active

#### Deliverable

* macOS write-path parity with the Windows server

#### Acceptance criteria

* commands queue correctly
* commands execute on main thread
* `/status` reflects queue and result updates
* failures are visible per command
* the request bodies sent by `vto/clo_automation_steps/client.py` are accepted unchanged
* the 4-pattern import order is preserved
* the 26-seam burst from `DEFAULT_SEAMS` executes without queue corruption
* simulation with `steps=150` works with the current polling and timeout model

#### Failure signals

* silent command drop
* command executes but status never updates
* exports or saves happen on the HTTP thread

---

### **Phase 6 - status and diagnostics**

#### Goal

Make the server debuggable and observable.

#### Work in this phase

1. Add `/status`
2. expose queue size
3. expose processing flag
4. expose recent results
5. expose loaded pattern count if available
6. log startup and shutdown events

#### Deliverable

* usable operational visibility for clients

#### Acceptance criteria

* clients can poll status between operations
* recent failures are visible without attaching a debugger

---

### **Phase 7 - hardening and shutdown stability**

#### Goal

Make the server production-safe for repeated CLO sessions.

#### Work in this phase

1. test malformed JSON
2. test missing files
3. test invalid indices
4. test port in use
5. test CLO quit while idle
6. test CLO quit while queue is non-empty
7. test repeated startup and shutdown cycles

#### Deliverable

* a server that fails cleanly instead of crashing the host

#### Acceptance criteria

* all tested failure paths return diagnostics
* CLO remains stable
* shutdown path is clean and repeatable
* `python vto/clo_automation_client.py test` works unchanged
* `python vto/clo_automation_client.py status` works unchanged
* the full `vto` pipeline can run through the current step list without client code changes

---

## **12A. VTO-Driven Acceptance Criteria**

The macOS REST server should not be considered complete until it passes the existing VTO automation flow as it exists today.

### **12A.1 Mandatory compatibility runs**

The following must work against the macOS server:

* `python vto/clo_automation_client.py test`
* `python vto/clo_automation_client.py status`
* `python vto/clo_automation_client.py`
* `python vto/run_vto.py`

### **12A.2 Pipeline-specific success conditions**

The following behavior must hold:

* the health check succeeds without client modification
* `new-project` queues and drains within the current timeout budget
* avatar import works with the path format sent by the client
* all 4 DXF imports work in the expected order
* `patterns_loaded` becomes non-zero and ideally equals `4`
* each pattern can be queried by index
* arrangement slots can be read, or the pipeline can continue using slot `-1`
* pattern arrangement commands accept `position.offset`
* `set-fabric` with `fabric_index=0` works across all loaded patterns
* the default 26-seam map can be queued and processed
* simulation with `steps=150` works under the existing timeout budget
* final `/status` reports meaningful `last_results`

### **12A.3 Current export/save expectation**

The current `vto` pipeline prints a manual export/save note instead of invoking the endpoints.

Even so, the macOS plug-in should still implement:

* `/export`
* `/save-project`

because they are part of Windows parity and may be re-enabled by the pipeline later.

---

## **13. Validation Matrix**

### **13.1 Build validation**

Verify:

* Release build succeeds
* `.dylib` exists
* target architecture is correct
* no missing Qt or CLO references

### **13.2 Load validation**

Verify:

* CLO discovers plug-in from the default plug-in folder
* plug-in appears in UI or Plug-in Manager
* plug-in can be invoked

### **13.3 Server validation**

Verify:

* `/health` works
* repeated requests work
* duplicate startup is blocked
* port binding failure is surfaced clearly

### **13.4 Read-route validation**

Verify:

* pattern count works
* pattern info works
* arrangement list works
* invalid inputs fail cleanly

### **13.5 Write-route validation**

Verify:

* project reset
* avatar import
* pattern import
* arrangement
* seam creation
* simulation
* export
* save

Also verify specifically against the VTO client contract:

* `arrange-pattern` accepts `position.offset`
* `set-fabric` accepts `fabric_index`
* `create-seam` accepts `patternA_index`, `lineA_index`, `patternB_index`, `lineB_index`, `directionA`, `directionB`
* `/execute` can still be called during queue waiting

### **13.6 Shutdown validation**

Verify:

* idle shutdown is clean
* active queue shutdown is clean
* no crash on next restart

---

## **14. Common Failure Modes and What They Mean**

### **Plug-in not visible**

Likely causes:

* wrong build mode
* wrong plug-in type assumptions
* incorrect install location
* wrong SDK or Qt linkage

### **CLO crashes on launch**

Likely causes:

* dyld loader failure
* architecture mismatch
* startup code running too early
* unresolved dependency

### **Server starts but CLO crashes after request**

Likely causes:

* HTTP thread calling CLO API directly
* timer dispatching on wrong thread
* invalid object lifetime in callback

### **Route hangs**

Likely causes:

* deadlock in sync result waiting
* queue drain not actually firing
* main thread blocked by modal UI

### **Server works once then breaks**

Likely causes:

* duplicate listener or timer
* detached thread lifetime issue
* timer ownership issue

---

## **15. Changelog Items That Matter**

The following official CLO changelog items improve confidence in this plan:

* **V9.1.1 (March 2026)**: `ImportAvatar` improved to avoid the Size and Pose dialog
* **V9.1.0 (December 2025)**: macOS Python script menu registration issue fixed
* **V9.1.0 (December 2025)**: plug-ins from `defaultPluginFolders.txt` now load correctly
* **V8.0.6 (November 2025)**: `ExportGLTF/GLB` UV issue fixed
* **V8.0.3 (August 2025)**: widget lifecycle helpers added and Python scripts can be loaded as plug-ins

These matter because they reduce friction in:

* avatar import automation
* macOS plug-in loading
* export reliability
* fallback prototyping paths

---

## **16. Recommendation and Final Direction**

### **What we should do**

* build a custom embedded REST server inside a macOS CLO plug-in
* keep the external route contract aligned with Windows
* treat the existing `vto/` pipeline as the canonical compatibility target
* make all CLO SDK work main-thread-only
* build with Qt 5.15.16 in Release mode
* install through the official macOS plug-in path or Plugin Manager
* treat the built-in `REST_API` only as an outbound helper

### **What we should not assume**

* that CLO already includes an inbound REST server
* that app-bundle copying is the standard deployment path
* that read-only CLO SDK calls are safe on the HTTP thread
* that timer behavior is correct until validated in the real host

### **Fallback strategy**

If the C++ macOS plug-in lifecycle or timer integration becomes the blocker, the best fallback prototype is:

* a Python plug-in inside CLO that hosts the same localhost REST contract

That fallback is only for early prototyping or risk reduction, not the preferred final architecture.

---

## **17. Official Sources Reviewed**

* `https://developer.clo3d.com/`
* `https://developer.clo3d.com/environment.html`
* `https://developer.clo3d.com/placement.html`
* `https://developer.clo3d.com/register.html`
* `https://developer.clo3d.com/list.html`
* `https://developer.clo3d.com/python.html`
* `https://developer.clo3d.com/library.html`
* `https://developer.clo3d.com/eventplugin.html`
* `https://developer.clo3d.com/changelog.html`

---

**End of Document**
