#include "stdafx.h"
#include "CLOAPIInterface.h"
#include "httplib.h"
#include <string>
#include <json.hpp>  // nlohmann json library

using json = nlohmann::json;
using namespace httplib;

// Command queue system for thread-safe API calls
#include <queue>
#include <mutex>
#include <condition_variable>
#include <cstdlib>
#include <cstring>
#include <windows.h>  // SetTimer / KillTimer

// ─── Command payload ────────────────────────────────────────────────────────
// All CLO API calls MUST run on the main thread.
// The background HTTP thread writes APICommand objects here; the main thread
// drains the queue in ProcessCommandQueue() / DoFunctionContinuously().
struct APICommand {
    std::string type;         // command type identifier
    std::string param1;       // file path, fabric preset name
    std::string param2;       // export format ("glb" / "gltf")
    int  param3 = 0;          // patternA_index | simulation steps | pattern_index
    int  param4 = 0;          // lineA_index
    int  param5 = 0;          // patternB_index
    int  param6 = 0;          // lineB_index
    bool boolParam1 = true;   // directionA (seam stitching direction)
    bool boolParam2 = true;   // directionB
    float floatParam1 = 0.0f; // position.x | color R
    float floatParam2 = 0.0f; // position.y | color G
    float floatParam3 = 0.0f; // position.z | color B
    float floatParam4 = 0.0f; // rotation.rx
    float floatParam5 = 0.0f; // rotation.ry
    float floatParam6 = 0.0f; // rotation.rz
};

// ─── Result tracking ────────────────────────────────────────────────────────
struct CommandResult {
    std::string type;
    bool        success = false;
    std::string message;
};

std::queue<APICommand>       g_commandQueue;
std::mutex                   g_queueMutex;
std::vector<CommandResult>   g_lastResults;
std::mutex                   g_resultsMutex;
bool                         g_queueProcessing = false;

// Global flag to keep server running
bool g_serverRunning = false;
std::thread g_serverThread;

// Forward declaration — defined later in this file.
void ProcessCommandQueue();

// Windows timer used to drain the command queue on CLO's main thread.
// SetTimer is called once from DoFunction(); the callback fires every 500 ms
// via CLO's Win32 message pump — no menu click needed after the first one.
UINT_PTR g_timerId = 0;

VOID CALLBACK QueueDrainTimer(HWND, UINT, UINT_PTR, DWORD)
{
    if (!g_serverRunning || g_queueProcessing) return;
    bool hasCommands;
    {
        std::lock_guard<std::mutex> lock(g_queueMutex);
        hasCommands = !g_commandQueue.empty();
    }
    if (hasCommands) {
        ProcessCommandQueue();
    }
}

// HTTP Server Implementation
void StartRESTServer()
{
    try {
        Server svr;

        // Health check endpoint
        svr.Get("/health", [](const Request&, Response& res) {
            json response = {
                {"status", "ok"},
                {"plugin", "CLO REST Automation"},
                {"version", "1.0"}
            };
            res.set_content(response.dump(), "application/json");
        });

        // Version endpoint with build identity
        svr.Get("/version", [](const Request&, Response& res) {
            json response = {
                {"plugin", "CLO REST Automation"},
                {"version", "1.0"},
                {"build_date", __DATE__},
                {"build_time", __TIME__},
                {"api_status", "ok"}
            };
            res.set_content(response.dump(), "application/json");
        });

    // Import Avatar (OBJ file) - QUEUED
    svr.Post("/import-avatar", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string filePath = j["path"];
            
            APICommand cmd;
            cmd.type = "import-avatar";
            cmd.param1 = filePath;
            
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }
            
            json response = {
                {"success", true},
                {"message", "Avatar import queued. Call /execute to process."},
                {"path", filePath},
                {"queue_size", g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Import Pattern (DXF file) - QUEUED
    svr.Post("/import-pattern", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string filePath = j["path"];
            float requestScale = 0.0f;
            if (j.contains("scale")) {
                try {
                    requestScale = j["scale"].get<float>();
                }
                catch (...) {
                    requestScale = 0.0f;
                }
            }
            
            APICommand cmd;
            cmd.type = "import-pattern";
            cmd.param1 = filePath;
            cmd.floatParam1 = requestScale;
            
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }
            
            json response = {
                {"success", true},
                {"message", "Pattern import queued. Call /execute to process."},
                {"path", filePath},
                {"scale", requestScale},
                {"queue_size", g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Execute queued commands — DoFunctionContinuously drains the queue
    // automatically on the main thread every frame, so this endpoint just
    // returns the current queue status without touching the queue itself.
    svr.Post("/execute", [](const Request& req, Response& res) {
        try {
            int qsize;
            bool processing;
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                qsize = (int)g_commandQueue.size();
                processing = g_queueProcessing;
            }
            json response = {
                {"success",          true},
                {"queue_size",       qsize},
                {"queue_processing", processing},
                {"message",          qsize > 0 ? "Queue pending (DoFunctionContinuously will drain it)" : "Queue empty"}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Create Seam between two patterns - QUEUED (main-thread safe)
    svr.Post("/create-seam", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type       = "create-seam";
            cmd.param3     = j["patternA_index"];
            cmd.param4     = j["lineA_index"];
            cmd.param5     = j["patternB_index"];
            cmd.param6     = j["lineB_index"];
            cmd.boolParam1 = j.value("directionA", true);
            cmd.boolParam2 = j.value("directionB", true);

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",    true},
                {"message",    "Seam queued"},
                {"patternA",   cmd.param3},
                {"lineA",      cmd.param4},
                {"patternB",   cmd.param5},
                {"lineB",      cmd.param6},
                {"queue_size", (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Run Simulation - QUEUED (main-thread safe)
    svr.Post("/simulate", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type   = "simulate";
            cmd.param3 = j.value("steps", 100);

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",    true},
                {"message",    "Simulation queued"},
                {"steps",      cmd.param3},
                {"queue_size", (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Export Garment (GLB/GLTF) - QUEUED (main-thread safe)
    svr.Post("/export", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type   = "export";
            cmd.param1 = j["path"];
            cmd.param2 = j.value("format", "glb");

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",    true},
                {"message",    "Export queued"},
                {"path",       cmd.param1},
                {"format",     cmd.param2},
                {"queue_size", (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Get Pattern Count
    svr.Get("/patterns/count", [](const Request&, Response& res) {
        try {
            int count = PATTERN_API->GetPatternCount();
            json response = {
                {"success", true},
                {"count", count}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Get Pattern Information
    svr.Get("/patterns/(\\d+)", [](const Request& req, Response& res) {
        try {
            int patternIndex = std::stoi(req.matches[1]);
            std::string info = PATTERN_API->GetPatternInformation(patternIndex);
            
            json response = {
                {"success", true},
                {"pattern_index", patternIndex},
                {"info", json::parse(info)}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Save Project as ZPRJ
    svr.Post("/save-project", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string filePath = j["path"];
            bool createThumbnail = j.value("thumbnail", true);
            
            std::string output = EXPORT_API->ExportZPrj(filePath, createThumbnail);
            bool success = !output.empty();
            
            json response = {
                {"success", success},
                {"message", success ? "Project saved" : "Save failed"},
                {"output_path", output}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── New Project / Clear Scene ────────────────────────────────────────────
    svr.Post("/new-project", [](const Request&, Response& res) {
        try {
            APICommand cmd;
            cmd.type = "new-project";
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }
            json response = {
                {"success",    true},
                {"message",    "New project queued"},
                {"queue_size", (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── Arrange Pattern in 3D space around the avatar ────────────────────────
    // Must be called AFTER import and BEFORE simulation.
    // Coordinates are in CLO centimetres; Y is the up-axis.
    svr.Post("/arrange-pattern", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type   = "arrange-pattern";
            cmd.param3 = j["pattern_index"];
            cmd.param4 = j.value("arrangement_index", 0);  // slot index from GetArrangementList
            cmd.param5 = j.value("orientation", 0);         // CLO orientation enum
            cmd.boolParam1 = j.value("position_only", false); // skip slot binding, apply offsets only

            // Fine-tune 2D offset within the arrangement slot (CLO mm units, ints)
            if (j.contains("position")) {
                cmd.floatParam1 = j["position"].value("x", 0.0f);
                cmd.floatParam2 = j["position"].value("y", 0.0f);
                cmd.floatParam3 = j["position"].value("offset", 0.0f);
            }

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",       true},
                {"message",       "Pattern arrangement queued"},
                {"pattern_index", cmd.param3},
                {"queue_size",    (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── Set Fabric properties on a pattern ───────────────────────────────────
    // preset: CLO fabric name e.g. "Cotton_Medium", "Denim_Heavy", "Silk_Light"
    svr.Post("/set-fabric", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type   = "set-fabric";
            cmd.param3 = j["pattern_index"];
            cmd.param4 = j.value("fabric_index", 0);  // index into CLO's fabric library

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",       true},
                {"message",       "Fabric assignment queued"},
                {"pattern_index", cmd.param3},
                {"preset",        cmd.param1},
                {"queue_size",    (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── Arrangement list — read CLO's avatar arrangement slots (read-only) ──────
    svr.Get("/arrangement-list", [](const Request&, Response& res) {
        try {
            json slots = json::array();
            auto list = PATTERN_API->GetArrangementList();
            for (int i = 0; i < (int)list.size(); i++) {
                json entry = {{"index", i}};
                for (auto& kv : list[i])
                    entry[kv.first] = kv.second;
                slots.push_back(entry);
            }
            json response = {{"success", true}, {"count", (int)slots.size()}, {"slots", slots}};
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── Arrangement of loaded patterns — read current arrangement per pattern ──
    svr.Get("/pattern-arrangements", [](const Request&, Response& res) {
        try {
            json patterns = json::array();
            int count = 0;
            try { count = PATTERN_API->GetPatternCount(); } catch (...) {}
            for (int i = 0; i < count; i++) {
                json entry = {{"pattern_index", i}};
                auto info = PATTERN_API->GetArrangementOfPattern(i);
                for (auto& kv : info)
                    entry[kv.first] = kv.second;
                patterns.push_back(entry);
            }
            json response = {{"success", true}, {"patterns", patterns}};
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── Status — queue state + last batch results (read-only, no queue) ──────
    svr.Get("/status", [](const Request&, Response& res) {
        try {
            int  queueSize      = 0;
            int  patternsLoaded = 0;
            bool processing     = g_queueProcessing;

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                queueSize = (int)g_commandQueue.size();
            }

            // GetPatternCount is a lightweight read — safe to call here
            try { patternsLoaded = PATTERN_API->GetPatternCount(); } catch (...) {}

            json lastResults = json::array();
            {
                std::lock_guard<std::mutex> rlock(g_resultsMutex);
                for (const auto& r : g_lastResults) {
                    lastResults.push_back({
                        {"type",    r.type},
                        {"success", r.success},
                        {"message", r.message}
                    });
                }
            }

            json response = {
                {"success",          true},
                {"queue_size",       queueSize},
                {"queue_processing", processing},
                {"patterns_loaded",  patternsLoaded},
                {"last_results",     lastResults}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // ── Start listening (blocking, retries on failure) ────────────────────────
    svr.set_keep_alive_max_count(100);
    svr.set_read_timeout(5, 0);  // 5 seconds
    svr.set_write_timeout(5, 0); // 5 seconds
    
    while (g_serverRunning) {
        bool success = svr.listen("0.0.0.0", 50505);
        if (!success && g_serverRunning) {
            // Server failed - wait and retry
            std::this_thread::sleep_for(std::chrono::seconds(2));
        }
        else {
            break; // Server stopped cleanly or we're shutting down
        }
    }
    
    } // end try
    catch (const std::exception& e) {
        g_serverRunning = false;
        // Exception during server operation
    }
    catch (...) {
        g_serverRunning = false;
        // Unknown exception
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ProcessCommandQueue — MUST be called from CLO's main thread.
// Called automatically every frame by DoFunctionContinuously().
// Also called manually when the user clicks Plugins → REST Server & Execute.
// ─────────────────────────────────────────────────────────────────────────────
void ProcessCommandQueue()
{
    // Drain the queue under the mutex, swap to a local list so we don't hold
    // the lock while executing (CLO API calls can be slow).
    std::vector<APICommand> batch;
    {
        std::lock_guard<std::mutex> lock(g_queueMutex);
        if (g_commandQueue.empty()) return;
        while (!g_commandQueue.empty()) {
            batch.push_back(g_commandQueue.front());
            g_commandQueue.pop();
        }
    }

    g_queueProcessing = true;

    // Clear previous results
    {
        std::lock_guard<std::mutex> rlock(g_resultsMutex);
        g_lastResults.clear();
    }

    for (const auto& cmd : batch) {
        CommandResult result;
        result.type    = cmd.type;
        result.success = false;

        try {
            // ── Avatar import ─────────────────────────────────────────────
            if (cmd.type == "import-avatar") {
                Marvelous::ImportExportOption options;
                // Avatar OBJ is exported by pipeline_star in metres.
                // CLO works in centimetres, so scale by 100.
                options.scale           = 100.0f;
                options.ImportObjectType = 0;   // Avatar
                options.bAutoTranslate  = true; // moves feet to Y=0 (ground)
                result.success  = IMPORT_API->ImportOBJ(cmd.param1, options);
                result.message  = result.success
                    ? "Imported avatar: " + cmd.param1
                    : "Failed to import avatar: " + cmd.param1;
            }
            // ── Pattern import ────────────────────────────────────────────
            else if (cmd.type == "import-pattern") {
                Marvelous::ImportDxfOption options;
                // Priority: request scale > env var > default.
                float patternScale = (cmd.floatParam1 > 0.0f) ? cmd.floatParam1 : 1.0f;
                const char* scaleEnv = std::getenv("CLO_PATTERN_IMPORT_SCALE");
                if (cmd.floatParam1 <= 0.0f && scaleEnv && std::strlen(scaleEnv) > 0) {
                    try {
                        float parsed = std::stof(scaleEnv);
                        if (parsed > 0.0f) {
                            patternScale = parsed;
                        }
                    }
                    catch (...) {
                        // Ignore invalid env var values and keep default scale.
                    }
                }

                options.m_Scale   = patternScale;
                options.m_bAppend = true;
                result.success = IMPORT_API->ImportDXF(cmd.param1, options);
                result.message = result.success
                    ? "Imported pattern: " + cmd.param1 +
                      " (scale=" + std::to_string(patternScale) + ")"
                                        : "Failed to import pattern: " + cmd.param1 +
                                            " (check DXF units/scale; expected centimeter-sized panels)";
            }
            // ── Create seam ───────────────────────────────────────────────
            else if (cmd.type == "create-seam") {
                result.success = PATTERN_API->AddSeamlinePairGroup(
                    cmd.param3, cmd.param4,
                    cmd.param5, cmd.param6,
                    cmd.boolParam1, cmd.boolParam2
                );
                result.message = result.success
                    ? "Seam: pattern " + std::to_string(cmd.param3) +
                      " edge " + std::to_string(cmd.param4) +
                      " <-> pattern " + std::to_string(cmd.param5) +
                      " edge " + std::to_string(cmd.param6)
                    : "Failed to create seam";
            }
            // ── Simulation ────────────────────────────────────────────────
            else if (cmd.type == "simulate") {
                result.success = UTILITY_API->Simulate((unsigned int)cmd.param3);
                result.message = result.success
                    ? "Simulation complete (" + std::to_string(cmd.param3) + " steps)"
                    : "Simulation failed";
            }
            // ── Export GLB/GLTF ───────────────────────────────────────────
            else if (cmd.type == "export") {
                bool asGLB = (cmd.param2 == "glb");
                Marvelous::ImportExportOption options;
                options.scale          = 1.0f;
                options.bExportGarment = true;
                options.bExportAvatar  = true;
                options.bEmbedded      = asGLB;
                std::vector<std::string> out =
                    EXPORT_API->ExportGLTF(cmd.param1, options, asGLB);
                result.success = !out.empty();
                result.message = result.success
                    ? "Exported to: " + cmd.param1
                    : "Export failed";
            }
            // ── New project ───────────────────────────────────────────────
            else if (cmd.type == "new-project") {
                UTILITY_API->NewProject();
                result.success = true;
                result.message = "New project created";
            }
            // ── Arrange pattern in 3D space ───────────────────────────────
            // SetArrangement assigns the pattern to a named avatar slot (front/back/sleeve).
            // SetArrangementPosition then fine-tunes with mm offsets from that slot centre.
            // param3 = patternIndex, param4 = arrangementIndex (-1 = skip SetArrangement)
            // floatParam1/2/3 = X/Y/Z offset in mm, param5 = orientation enum
            else if (cmd.type == "arrange-pattern") {
                bool positionOnly = cmd.boolParam1;
                if (cmd.param4 < 0 && !positionOnly) {
                    result.success = false;
                    result.message = "Invalid arrangement slot for pattern " + std::to_string(cmd.param3) +
                        " (slot=" + std::to_string(cmd.param4) + ")";
                }
                else {
                    if (!positionOnly)
                        PATTERN_API->SetArrangement(cmd.param3, cmd.param4);

                    // Curved style for avatar-slot draping, flat for position-only fallback.
                    PATTERN_API->SetArrangementShapeStyle(cmd.param3, positionOnly ? "Flat" : "Curved");
                    PATTERN_API->SetArrangementPosition(
                        cmd.param3,
                        (int)cmd.floatParam1,
                        (int)cmd.floatParam2,
                        (int)cmd.floatParam3
                    );
                    PATTERN_API->SetArrangementOrientation(cmd.param3, cmd.param5);

                    result.success = true;
                    result.message = "Pattern " + std::to_string(cmd.param3) +
                        (positionOnly
                            ? " position-only [Flat]"
                            : " -> arrangement slot " + std::to_string(cmd.param4) + " [Curved]") +
                        " pos=(" + std::to_string((int)cmd.floatParam1) +
                        "," + std::to_string((int)cmd.floatParam2) +
                        "," + std::to_string((int)cmd.floatParam3) + ")";
                }
            }
            // ── Set fabric preset + colour ─────────────────────────────────
            else if (cmd.type == "set-fabric") {
                // Assigns a fabric from CLO's internal fabric list to a pattern piece.
                // fabric_index 0 = first fabric in the project (add fabrics via CLO UI first).
                PATTERN_API->SetPatternPieceFabricIndex(cmd.param3, cmd.param4);
                result.success = true;
                result.message = "Fabric index " + std::to_string(cmd.param4) +
                    " applied to pattern " + std::to_string(cmd.param3);
            }
            // ── Save project ──────────────────────────────────────────────
            else if (cmd.type == "save-project") {
                bool thumb  = (cmd.param3 != 0);
                std::string out = EXPORT_API->ExportZPrj(cmd.param1, thumb);
                result.success  = !out.empty();
                result.message  = result.success
                    ? "Project saved: " + out
                    : "Save failed";
            }
            else {
                result.message = "Unknown command type: " + cmd.type;
            }
        }
        catch (const std::exception& e) {
            result.success = false;
            result.message = "Exception in '" + cmd.type + "': " + std::string(e.what());
        }

        {
            std::lock_guard<std::mutex> rlock(g_resultsMutex);
            g_lastResults.push_back(result);
        }
    }

    g_queueProcessing = false;
}

// CLO Plugin Callbacks - Required by CLO
#define CLO_PLUGIN_SPECIFIER extern "C" __declspec(dllexport)

CLO_PLUGIN_SPECIFIER const char* GetActionName()
{
    return "REST Server & Execute";
}

CLO_PLUGIN_SPECIFIER const char* GetObjectNameTreeToAddAction()
{
    return "Plugins";
}

CLO_PLUGIN_SPECIFIER int GetPositionIndexToAddAction()
{
    return 0;
}

CLO_PLUGIN_SPECIFIER void DoFunction()
{
    try {
        // First, start server if not running
        if (!g_serverRunning) {
            UTILITY_API->DisplayMessageBox("Starting REST server on http://localhost:50505\n\nQueue drains automatically every 500 ms — no further menu clicks needed.");
            
            g_serverRunning = true;
            g_serverThread = std::thread(StartRESTServer);
            g_serverThread.detach();

            // Register a 500 ms Windows timer so the queue is drained on the
            // main thread automatically (CLO v2025 has no DoFunctionContinuously).
            if (g_timerId == 0) {
                g_timerId = SetTimer(NULL, 0, 500, QueueDrainTimer);
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            return;
        }
        
        // Server is running - process any queued commands
        int queue_size;
        {
            std::lock_guard<std::mutex> lock(g_queueMutex);
            queue_size = g_commandQueue.size();
        }
        
        if (queue_size > 0) {
            ProcessCommandQueue();
        }
        else {
            UTILITY_API->DisplayMessageBox("REST server is running on http://localhost:50505\n\nNo commands in queue.\n\nQueue commands via REST API, then click this menu item again to execute them.");
        }
    }
    catch (const std::exception& e) {
        g_serverRunning = false;
        std::string msg = "Error: ";
        msg += e.what();
        UTILITY_API->DisplayMessageBox(msg.c_str());
    }
    catch (...) {
        g_serverRunning = false;
        UTILITY_API->DisplayMessageBox("Unknown error occurred");
    }
}

CLO_PLUGIN_SPECIFIER void DoFunctionAfterLoadingCLOFile(const char* fileExtension)
{
    // Not used
}

// DoFunctionContinuously is NOT called by CLO v2025 (not in SDK).
// Queue draining is handled by QueueDrainTimer (SetTimer, 500 ms).
CLO_PLUGIN_SPECIFIER void DoFunctionContinuously() { }
