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

struct APICommand {
    std::string type;  // "import-pattern", "import-avatar", etc.
    std::string param1;
    std::string param2;
    int param3;
    int param4;
};

std::queue<APICommand> g_commandQueue;
std::mutex g_queueMutex;
std::vector<std::string> g_commandResults;

// Global flag to keep server running
bool g_serverRunning = false;
std::thread g_serverThread;

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
            
            APICommand cmd;
            cmd.type = "import-pattern";
            cmd.param1 = filePath;
            
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }
            
            json response = {
                {"success", true},
                {"message", "Pattern import queued. Call /execute to process."},
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

    // Execute queued commands (call from main thread via menu)
    svr.Post("/execute", [](const Request& req, Response& res) {
        try {
            json response;
            response["executed"] = json::array();
        response["queue_size_before"] = g_commandQueue.size();
            
            // Note: This endpoint just reports queue status
            // Actual execution happens when user clicks "Execute Commands" menu in CLO
            if (g_commandQueue.empty()) {
                response["success"] = true;
                response["message"] = "No commands in queue";
                response["queue_size_after"] = 0;
            } else {
                response["success"] = true;
                response["message"] = "Commands queued. Click 'Execute Commands' in CLO Plugins menu to process.";
                response["queue_size_after"] = g_commandQueue.size();
            }
            
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Create Seam between two patterns
    svr.Post("/create-seam", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            int patternA = j["patternA_index"];
            int lineA = j["lineA_index"];
            int patternB = j["patternB_index"];
            int lineB = j["lineB_index"];
            bool directionA = j.value("directionA", true);
            bool directionB = j.value("directionB", true);
            
            bool success = PATTERN_API->AddSeamlinePairGroup(
                patternA, lineA, patternB, lineB, directionA, directionB
            );
            
            json response = {
                {"success", success},
                {"message", success ? "Seam created successfully" : "Failed to create seam"}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Run Simulation
    svr.Post("/simulate", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            unsigned int steps = j.value("steps", 100);  // Default 100 steps
            
            bool success = UTILITY_API->Simulate(steps);
            
            json response = {
                {"success", success},
                {"message", success ? "Simulation completed" : "Simulation failed"},
                {"steps", steps}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Export Garment (GLB/GLTF) - SIMPLIFIED
    svr.Post("/export", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string filePath = j["path"];
            bool asGLB = j.value("format", "glb") == "glb";  // true for GLB, false for GLTF
            
            Marvelous::ImportExportOption options;
            options.scale = 1.0f;
            options.bExportGarment = true;
            options.bExportAvatar = true;
            options.bEmbedded = asGLB;  // GLB is embedded format
            
            std::vector<std::string> outputPaths = EXPORT_API->ExportGLTF(filePath, options, asGLB);
            
            bool success = !outputPaths.empty();
            json response = {
                {"success", success},
                {"message", success ? "Export successful" : "Export failed"},
                {"output_paths", outputPaths}
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

    // Start listening (blocking call) - keep trying if it fails
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

// Process command queue from main thread
void ProcessCommandQueue()
{
    std::lock_guard<std::mutex> lock(g_queueMutex);
    
    if (g_commandQueue.empty()) {
        UTILITY_API->DisplayMessageBox("No commands to execute.");
        return;
    }
    
    std::string results = "Executing " + std::to_string(g_commandQueue.size()) + " commands:\n\n";
    int success_count = 0;
    int fail_count = 0;
    
    while (!g_commandQueue.empty()) {
        APICommand cmd = g_commandQueue.front();
        g_commandQueue.pop();
        
        try {
            if (cmd.type == "import-avatar") {
                Marvelous::ImportExportOption options;
                options.scale = 1.0f;
                options.ImportObjectType = 0;  // Avatar
                options.bAutoTranslate = true;
                
                bool success = IMPORT_API->ImportOBJ(cmd.param1, options);
                if (success) {
                    results += "✓ Imported avatar: " + cmd.param1 + "\n";
                    success_count++;
                } else {
                    results += "✗ Failed to import avatar: " + cmd.param1 + "\n";
                    fail_count++;
                }
            }
            else if (cmd.type == "import-pattern") {
                Marvelous::ImportDxfOption options;
                options.m_Scale = 1.0f;
                options.m_bAppend = true;
                
                bool success = IMPORT_API->ImportDXF(cmd.param1, options);
                if (success) {
                    results += "✓ Imported pattern: " + cmd.param1 + "\n";
                    success_count++;
                } else {
                    results += "✗ Failed to import pattern: " + cmd.param1 + "\n";
                    fail_count++;
                }
            }
        }
        catch (const std::exception& e) {
            results += "✗ Error: " + std::string(e.what()) + "\n";
            fail_count++;
        }
    }
    
    results += "\n" + std::to_string(success_count) + " succeeded, " + std::to_string(fail_count) + " failed.";
    UTILITY_API->DisplayMessageBox(results.c_str());
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
            UTILITY_API->DisplayMessageBox("Starting REST server on http://localhost:50505\n\nServer will run in background.\n\nTest with: curl http://localhost:50505/health");
            
            g_serverRunning = true;
            g_serverThread = std::thread(StartRESTServer);
            g_serverThread.detach();
            
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
    // Not used for this plugin
}
