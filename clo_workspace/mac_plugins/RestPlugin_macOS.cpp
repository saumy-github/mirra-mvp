/**
 * RestPlugin_macOS.cpp
 * CLO3D REST Automation Plugin — macOS port
 *
 * Architecture:
 *   - Background thread runs cpp-httplib server on 127.0.0.1:50505
 *   - HTTP thread NEVER calls CLO APIs directly
 *   - Async write commands are queued; a Qt timer drains them on the CLO main thread
 *   - Sync read commands (patterns/count, patterns/{idx}, etc.) use std::promise/future
 *     so the HTTP thread waits up to 3 s for the main thread result
 *   - g_patternsLoaded is updated by the main thread after each import; /status reads
 *     it without a CLO API call so polling stays fast
 *
 * Compatibility target: vto/clo_automation_steps/client.py (unchanged)
 * Port number: 50505
 * Build: arm64 Release dylib, Qt 5.15.x, CLO SDK v2025
 */

#if __has_include("CLOAPIInterface.h")
#include "CLOAPIInterface.h"
#else
// Minimal stub to satisfy editor/clang include-path diagnostics.
// These stubs are only to remove include errors in environments where the
// real CLO SDK headers are not available; the real SDK header should be used
// for actual builds and runtime linking.

#include <string>
#include <vector>
#include <map>

namespace Marvelous {
struct ImportExportOption {
    float scale = 1.0f;
    bool bExportGarment = false;
    bool bExportAvatar = false;
    bool bEmbedded = false;
    int ImportObjectType = 0;
    bool bAutoTranslate = false;
};
struct ImportDxfOption {
    float m_Scale = 1.0f;
    bool m_bAppend = false;
};
} // namespace Marvelous

struct ImportAPI {
    bool ImportOBJ(const std::string&, const Marvelous::ImportExportOption&) { return false; }
    bool ImportDXF(const std::string&, const Marvelous::ImportDxfOption&) { return false; }
};
extern ImportAPI* IMPORT_API;

struct ExportAPI {
    std::string ExportGLTF(const std::string&, const Marvelous::ImportExportOption&, bool) { return std::string(); }
    std::string ExportZPrj(const std::string&, bool) { return std::string(); }
};
extern ExportAPI* EXPORT_API;

struct UtilityAPI {
    void NewProject() {}
    bool Simulate(unsigned int) { return false; }
};
extern UtilityAPI* UTILITY_API;

struct PatternAPI {
    void SetArrangement(int, int) {}
    void SetArrangementPosition(int, int, int, int) {}
    void SetArrangementOrientation(int, int) {}
    void SetPatternPieceFabricIndex(int, int) {}
    bool AddSeamlinePairGroup(int, int, int, int, bool, bool) { return false; }
    int GetPatternCount() { return 0; }
    std::string GetPatternInformation(int) { return std::string("{}"); }
    std::vector<std::map<std::string, std::string>> GetArrangementList() { return {}; }
    std::map<std::string, std::string> GetArrangementOfPattern(int) { return {}; }
};
extern PatternAPI* PATTERN_API;

#endif

// Qt – required for QTimer main-thread dispatch
#if __has_include(<QCoreApplication>) && __has_include(<QTimer>) && __has_include(<QObject>)
#include <QCoreApplication>
#include <QTimer>
#include <QObject>
#else
// Minimal Qt stubs to satisfy editor/clang include-path diagnostics.
// These stubs are only to remove include errors in environments where the
// real Qt headers are not available; the real Qt headers should be used
// for actual builds and runtime linking.

class QCoreApplication {};

class QObject {
public:
    template<typename... Args>
    static bool connect(Args...) { return true; }
};

class QTimer : public QObject {
public:
    QTimer(QObject*) {}
    void setInterval(int) {}
    void start() {}
    void stop() {}
    // Member used as a signal pointer in connect(); present to allow &QTimer::timeout.
    void timeout() {}
};

#endif

// Header-only HTTP server (cpp-httplib) and JSON (nlohmann)
#include "httplib.h"
#include "json.hpp"

// Standard library
#include <atomic>
#include <chrono>
#include <future>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

using json = nlohmann::json;

// ─── Typed command payload ────────────────────────────────────────────────────
// All CLO API calls MUST run on the main thread.
// The HTTP thread writes APICommand objects into g_commandQueue protected by
// g_queueMutex. The Qt timer calls ProcessCommandQueue() on the main thread.
struct APICommand {
    std::string type;           // command identifier
    std::string param1;         // file path (avatar, pattern, export, save)
    std::string param2;         // export format ("glb" / "gltf")
    int  param3 = 0;            // patternA_index | pattern_index | steps
    int  param4 = 0;            // lineA_index    | arrangement_index | fabric_index
    int  param5 = 0;            // patternB_index | orientation
    int  param6 = 0;            // lineB_index
    bool boolParam1 = true;     // directionA | thumbnail
    bool boolParam2 = true;     // directionB
    float floatParam1 = 0.f;   // position.x
    float floatParam2 = 0.f;   // position.y
    float floatParam3 = 0.f;   // position.offset  (sent by client as "offset", not "z")

    // Sync-read support: if isSync==true the result is delivered via syncPromise
    // instead of appended to g_lastResults.
    // shared_ptr keeps the promise alive even if the HTTP thread times out and
    // returns before the main thread processes the command (prevents use-after-free).
    bool                                   isSync      = false;
    std::shared_ptr<std::promise<json>>    syncPromise;
};

// ─── Result record (kept for /status last_results) ────────────────────────────
struct CommandResult {
    std::string type;
    bool        success = false;
    std::string message;
};

// ─── Global state ─────────────────────────────────────────────────────────────
static std::queue<APICommand>     g_commandQueue;
static std::mutex                 g_queueMutex;
static std::vector<CommandResult> g_lastResults;
static std::mutex                 g_resultsMutex;
static std::atomic<bool>          g_queueProcessing{false};
static std::atomic<bool>          g_serverRunning{false};
static std::thread                g_serverThread;
static std::atomic<int>           g_patternsLoaded{0};  // updated on main thread only

// Raw pointer to Qt timer – created and owned on the main thread.
// Stopped and deleted in the dylib destructor (also main thread on macOS).
static QTimer* g_drainTimer = nullptr;

// Raw pointer to the httplib server so the destructor can call stop().
static httplib::Server* g_server = nullptr;

// ─── Forward declaration ──────────────────────────────────────────────────────
static void ProcessCommandQueue();

// ─── Sync-read helper ─────────────────────────────────────────────────────────
// Pushes a read command and blocks up to 3 s for the main thread result.
static json dispatchSyncRead(const std::string& type, int param3 = 0)
{
    auto promisePtr = std::make_shared<std::promise<json>>();
    auto future     = promisePtr->get_future();

    APICommand cmd;
    cmd.type        = type;
    cmd.param3      = param3;
    cmd.isSync      = true;
    cmd.syncPromise = promisePtr;   // shared ownership — safe even on timeout
    {
        std::lock_guard<std::mutex> lk(g_queueMutex);
        g_commandQueue.push(cmd);
    }

    if (future.wait_for(std::chrono::seconds(3)) == std::future_status::ready)
        return future.get();

    return {
        {"success", false},
        {"error",   "timeout"},
        {"message", "Main thread did not respond within 3 s — CLO may be busy"}
    };
}

// ─── ProcessCommandQueue — called ONLY from the CLO main thread ───────────────
static void ProcessCommandQueue()
{
    // Re-entrancy guard: exchange returns previous value; if already true, bail.
    if (g_queueProcessing.exchange(true)) return;

    // Drain the queue under the mutex; release before calling any CLO API.
    std::vector<APICommand> batch;
    {
        std::lock_guard<std::mutex> lk(g_queueMutex);
        if (g_commandQueue.empty()) {
            g_queueProcessing = false;
            return;
        }
        while (!g_commandQueue.empty()) {
            batch.push_back(std::move(g_commandQueue.front()));
            g_commandQueue.pop();
        }
    }

    // Clear previous async results only when a new async batch arrives.
    bool hasAsync = false;
    for (const auto& c : batch) if (!c.isSync) { hasAsync = true; break; }
    if (hasAsync) {
        std::lock_guard<std::mutex> rl(g_resultsMutex);
        g_lastResults.clear();
    }

    for (auto& cmd : batch) {
        json       syncResult;
        CommandResult asyncResult;
        asyncResult.type    = cmd.type;
        asyncResult.success = false;

        try {
            // ── Avatar import ─────────────────────────────────────────────────
            if (cmd.type == "import-avatar") {
                Marvelous::ImportExportOption opts;
                // Avatar OBJ is in metres; CLO works in centimetres → scale ×100.
                opts.scale            = 100.0f;
                opts.ImportObjectType = 0;      // Avatar
                opts.bAutoTranslate   = true;   // move feet to Y=0
                asyncResult.success = IMPORT_API->ImportOBJ(cmd.param1, opts);
                asyncResult.message = asyncResult.success
                    ? "Imported avatar: " + cmd.param1
                    : "Failed to import avatar: " + cmd.param1;
            }
            // ── Pattern import (DXF) ──────────────────────────────────────────
            else if (cmd.type == "import-pattern") {
                Marvelous::ImportDxfOption opts;
                opts.m_Scale   = 1.0f;
                opts.m_bAppend = true;          // append — preserve import order
                asyncResult.success = IMPORT_API->ImportDXF(cmd.param1, opts);
                asyncResult.message = asyncResult.success
                    ? "Imported pattern: " + cmd.param1
                    : "Failed to import pattern: " + cmd.param1;
                if (asyncResult.success)
                    g_patternsLoaded++;
            }
            // ── New project ───────────────────────────────────────────────────
            else if (cmd.type == "new-project") {
                UTILITY_API->NewProject();
                g_patternsLoaded = 0;
                asyncResult.success = true;
                asyncResult.message = "New project created";
            }
            // ── Arrange pattern ───────────────────────────────────────────────
            // param3 = pattern_index
            // param4 = arrangement_index (-1 = skip SetArrangement slot assignment)
            // param5 = orientation enum
            // floatParam1/2/3 = position x/y/offset (mm, passed as ints to SDK)
            else if (cmd.type == "arrange-pattern") {
                if (cmd.param4 >= 0)
                    PATTERN_API->SetArrangement(cmd.param3, cmd.param4);
                PATTERN_API->SetArrangementPosition(
                    cmd.param3,
                    static_cast<int>(cmd.floatParam1),
                    static_cast<int>(cmd.floatParam2),
                    static_cast<int>(cmd.floatParam3)
                );
                if (cmd.param5 != 0)
                    PATTERN_API->SetArrangementOrientation(cmd.param3, cmd.param5);
                asyncResult.success = true;
                asyncResult.message = "Pattern " + std::to_string(cmd.param3) +
                    (cmd.param4 >= 0
                        ? " -> slot " + std::to_string(cmd.param4)
                        : " position set") +
                    " offset=(" + std::to_string(static_cast<int>(cmd.floatParam1)) +
                    "," + std::to_string(static_cast<int>(cmd.floatParam2)) +
                    "," + std::to_string(static_cast<int>(cmd.floatParam3)) + ")mm";
            }
            // ── Set fabric ────────────────────────────────────────────────────
            // param3 = pattern_index, param4 = fabric_index (0 = first project fabric)
            else if (cmd.type == "set-fabric") {
                PATTERN_API->SetPatternPieceFabricIndex(cmd.param3, cmd.param4);
                asyncResult.success = true;
                asyncResult.message = "Fabric " + std::to_string(cmd.param4) +
                    " applied to pattern " + std::to_string(cmd.param3);
            }
            // ── Create seam ───────────────────────────────────────────────────
            // param3/4 = patternA/lineA, param5/6 = patternB/lineB
            // boolParam1/2 = directionA/B
            else if (cmd.type == "create-seam") {
                asyncResult.success = PATTERN_API->AddSeamlinePairGroup(
                    cmd.param3, cmd.param4,
                    cmd.param5, cmd.param6,
                    cmd.boolParam1, cmd.boolParam2
                );
                asyncResult.message = asyncResult.success
                    ? "Seam: " + std::to_string(cmd.param3) + "/" + std::to_string(cmd.param4) +
                      " <-> " + std::to_string(cmd.param5) + "/" + std::to_string(cmd.param6)
                    : "Failed to create seam (" +
                      std::to_string(cmd.param3) + "/" + std::to_string(cmd.param4) +
                      " <-> " + std::to_string(cmd.param5) + "/" + std::to_string(cmd.param6) + ")";
            }
            // ── Simulate ──────────────────────────────────────────────────────
            else if (cmd.type == "simulate") {
                asyncResult.success = UTILITY_API->Simulate(static_cast<unsigned int>(cmd.param3));
                asyncResult.message = asyncResult.success
                    ? "Simulation complete (" + std::to_string(cmd.param3) + " steps)"
                    : "Simulation failed";
            }
            // ── Export GLB / GLTF ─────────────────────────────────────────────
            else if (cmd.type == "export") {
                bool asGLB = (cmd.param2 == "glb");
                Marvelous::ImportExportOption opts;
                opts.scale          = 1.0f;
                opts.bExportGarment = true;
                opts.bExportAvatar  = true;
                opts.bEmbedded      = asGLB;
                auto out = EXPORT_API->ExportGLTF(cmd.param1, opts, asGLB);
                asyncResult.success = !out.empty();
                asyncResult.message = asyncResult.success
                    ? "Exported to: " + cmd.param1
                    : "Export failed";
            }
            // ── Save project ──────────────────────────────────────────────────
            else if (cmd.type == "save-project") {
                auto out = EXPORT_API->ExportZPrj(cmd.param1, cmd.boolParam1);
                asyncResult.success = !out.empty();
                asyncResult.message = asyncResult.success
                    ? "Project saved: " + out
                    : "Save failed";
            }
            // ── Sync reads ────────────────────────────────────────────────────
            else if (cmd.type == "read-pattern-count") {
                int cnt = PATTERN_API->GetPatternCount();
                g_patternsLoaded = cnt;
                syncResult = {{"success", true}, {"count", cnt}};
            }
            else if (cmd.type == "read-pattern-info") {
                int total = PATTERN_API->GetPatternCount();
                int idx   = cmd.param3;
                if (idx < 0 || idx >= total) {
                    syncResult = {
                        {"success", false},
                        {"error",   "invalid index"},
                        {"message", "Pattern index " + std::to_string(idx) +
                                    " out of range (count=" + std::to_string(total) + ")"}
                    };
                } else {
                    std::string raw = PATTERN_API->GetPatternInformation(idx);
                    json parsed;
                    try { parsed = json::parse(raw); }
                    catch (...) { parsed = raw; }
                    syncResult = {
                        {"success",       true},
                        {"pattern_index", idx},
                        {"info",          parsed}
                    };
                }
            }
            else if (cmd.type == "read-arrangement-list") {
                json slotList = json::array();
                auto list = PATTERN_API->GetArrangementList();
                for (int i = 0; i < static_cast<int>(list.size()); i++) {
                    json entry;
                    entry["index"] = i;
                    for (const auto& kv : list[i])
                        entry[kv.first] = kv.second;
                    slotList.push_back(entry);
                }
                syncResult = {
                    {"success", true},
                    {"count",   static_cast<int>(slotList.size())},
                    {"slots",   slotList}
                };
            }
            else if (cmd.type == "read-pattern-arrangements") {
                json patterns = json::array();
                int  count    = PATTERN_API->GetPatternCount();
                for (int i = 0; i < count; i++) {
                    json entry;
                    entry["pattern_index"] = i;
                    auto info = PATTERN_API->GetArrangementOfPattern(i);
                    for (const auto& kv : info)
                        entry[kv.first] = kv.second;
                    patterns.push_back(entry);
                }
                syncResult = {{"success", true}, {"patterns", patterns}};
            }
            else {
                asyncResult.message = "Unknown command: " + cmd.type;
                syncResult = {{"success", false}, {"error", "unknown command: " + cmd.type}};
            }
        }
        catch (const std::exception& e) {
            asyncResult.success = false;
            asyncResult.message = "Exception in '" + cmd.type + "': " + e.what();
            syncResult = {{"success", false}, {"error", e.what()}};
        }

        if (cmd.isSync && cmd.syncPromise) {
            cmd.syncPromise->set_value(syncResult);
        } else {
            std::lock_guard<std::mutex> rl(g_resultsMutex);
            g_lastResults.push_back(asyncResult);
        }
    }

    g_queueProcessing = false;
}

// ─── HTTP server ──────────────────────────────────────────────────────────────
// Runs on a background thread. Never calls CLO APIs directly.
static void StartRESTServer()
{
    httplib::Server svr;
    {
        // Store pointer so the dylib destructor can call svr.stop() for clean exit.
        // This is safe: svr lives for the entire function duration.
        g_server = &svr;
    }

    svr.set_keep_alive_max_count(100);
    svr.set_read_timeout(5, 0);
    svr.set_write_timeout(5, 0);

    // ── GET /health ───────────────────────────────────────────────────────────
    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        json r = {
            {"status",        "ok"},
            {"plugin",        "CLO REST Automation"},
            {"version",       "1.0"},
            {"platform",      "macOS"},
            {"plugin_loaded", true}
        };
        res.set_content(r.dump(), "application/json");
    });

    // ── GET /status ───────────────────────────────────────────────────────────
    // Reads only atomic/mutex state — no CLO API call needed; fast for polling.
    svr.Get("/status", [](const httplib::Request&, httplib::Response& res) {
        int  qsize      = 0;
        bool processing = false;
        {
            std::lock_guard<std::mutex> lk(g_queueMutex);
            qsize = static_cast<int>(g_commandQueue.size());
        }
        processing = g_queueProcessing.load();

        json lastResults = json::array();
        {
            std::lock_guard<std::mutex> rl(g_resultsMutex);
            for (const auto& lr : g_lastResults)
                lastResults.push_back({
                    {"type",    lr.type},
                    {"success", lr.success},
                    {"message", lr.message}
                });
        }
        json r = {
            {"success",          true},
            {"queue_size",       qsize},
            {"queue_processing", processing},
            {"patterns_loaded",  g_patternsLoaded.load()},
            {"server_running",   g_serverRunning.load()},
            {"last_results",     lastResults}
        };
        res.set_content(r.dump(), "application/json");
    });

    // ── POST /execute — compatibility nudge endpoint ──────────────────────────
    // wait_for_queue() in client.py calls this when queue is stuck.
    // Our Qt timer already drains automatically; this just returns queue state.
    svr.Post("/execute", [](const httplib::Request&, httplib::Response& res) {
        int  qsize      = 0;
        bool processing = false;
        {
            std::lock_guard<std::mutex> lk(g_queueMutex);
            qsize = static_cast<int>(g_commandQueue.size());
        }
        processing = g_queueProcessing.load();
        json r = {
            {"success",          true},
            {"queue_size",       qsize},
            {"queue_processing", processing},
            {"message",          qsize > 0 ? "Queue pending — timer will drain it" : "Queue empty"}
        };
        res.set_content(r.dump(), "application/json");
    });

    // ── GET /patterns/count ───────────────────────────────────────────────────
    svr.Get("/patterns/count", [](const httplib::Request&, httplib::Response& res) {
        json r = dispatchSyncRead("read-pattern-count");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    // ── GET /patterns/{index} ─────────────────────────────────────────────────
    svr.Get(R"(/patterns/(\d+))", [](const httplib::Request& req, httplib::Response& res) {
        int idx = std::stoi(req.matches[1]);
        json r  = dispatchSyncRead("read-pattern-info", idx);
        res.status = r.value("success", false) ? 200 : (r.count("error") ? 400 : 503);
        res.set_content(r.dump(), "application/json");
    });

    // ── GET /arrangement-list ─────────────────────────────────────────────────
    svr.Get("/arrangement-list", [](const httplib::Request&, httplib::Response& res) {
        json r = dispatchSyncRead("read-arrangement-list");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    // ── GET /pattern-arrangements ─────────────────────────────────────────────
    svr.Get("/pattern-arrangements", [](const httplib::Request&, httplib::Response& res) {
        json r = dispatchSyncRead("read-pattern-arrangements");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    // ── POST /new-project ─────────────────────────────────────────────────────
    svr.Post("/new-project", [](const httplib::Request&, httplib::Response& res) {
        APICommand cmd;
        cmd.type = "new-project";
        int qsize = 0;
        {
            std::lock_guard<std::mutex> lk(g_queueMutex);
            g_commandQueue.push(cmd);
            qsize = static_cast<int>(g_commandQueue.size());
        }
        json r = {{"success", true}, {"message", "New project queued"}, {"queue_size", qsize}};
        res.set_content(r.dump(), "application/json");
    });

    // ── POST /import-avatar ───────────────────────────────────────────────────
    // Expects: {"path": "/absolute/posix/path/to/avatar.obj"}
    svr.Post("/import-avatar", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string path = j.at("path");
            APICommand cmd;
            cmd.type   = "import-avatar";
            cmd.param1 = path;
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Avatar import queued"},
                      {"path", path}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /import-pattern ──────────────────────────────────────────────────
    // Expects: {"path": "/absolute/posix/path/to/pattern.dxf"}
    // Import order is preserved — seam map depends on it.
    svr.Post("/import-pattern", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string path = j.at("path");
            APICommand cmd;
            cmd.type   = "import-pattern";
            cmd.param1 = path;
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Pattern import queued"},
                      {"path", path}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /arrange-pattern ─────────────────────────────────────────────────
    // Expects: {pattern_index, arrangement_index, position:{x,y,offset}, orientation}
    // Note: client sends "position.offset" not "position.z" — field name is critical.
    svr.Post("/arrange-pattern", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type   = "arrange-pattern";
            cmd.param3 = j.at("pattern_index");
            cmd.param4 = j.value("arrangement_index", -1);
            cmd.param5 = j.value("orientation", 0);
            if (j.contains("position")) {
                cmd.floatParam1 = j["position"].value("x",      0.0f);
                cmd.floatParam2 = j["position"].value("y",      0.0f);
                cmd.floatParam3 = j["position"].value("offset", 0.0f);
            }
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Pattern arrangement queued"},
                      {"pattern_index", cmd.param3}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /set-fabric ──────────────────────────────────────────────────────
    // Expects: {pattern_index, fabric_index}  (pipeline always sends fabric_index=0)
    svr.Post("/set-fabric", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type   = "set-fabric";
            cmd.param3 = j.at("pattern_index");
            cmd.param4 = j.value("fabric_index", 0);
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Fabric assignment queued"},
                      {"pattern_index", cmd.param3}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /create-seam ─────────────────────────────────────────────────────
    // Expects: {patternA_index, lineA_index, patternB_index, lineB_index, directionA, directionB}
    // Pipeline submits up to 26 seams in sequence — queue must remain stable.
    svr.Post("/create-seam", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type       = "create-seam";
            cmd.param3     = j.at("patternA_index");
            cmd.param4     = j.at("lineA_index");
            cmd.param5     = j.at("patternB_index");
            cmd.param6     = j.at("lineB_index");
            cmd.boolParam1 = j.value("directionA", true);
            cmd.boolParam2 = j.value("directionB", true);
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Seam queued"},
                      {"patternA", cmd.param3}, {"lineA", cmd.param4},
                      {"patternB", cmd.param5}, {"lineB", cmd.param6},
                      {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /simulate ────────────────────────────────────────────────────────
    // Expects: {"steps": N}  — pipeline sends steps=150, waits up to 300 s
    svr.Post("/simulate", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type   = "simulate";
            cmd.param3 = j.value("steps", 100);
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Simulation queued"},
                      {"steps", cmd.param3}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /export ──────────────────────────────────────────────────────────
    // Expects: {"path": "...", "format": "glb"}
    svr.Post("/export", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type   = "export";
            cmd.param1 = j.at("path");
            cmd.param2 = j.value("format", "glb");
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Export queued"},
                      {"path", cmd.param1}, {"format", cmd.param2}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /save-project ────────────────────────────────────────────────────
    // Expects: {"path": "...", "thumbnail": true}
    svr.Post("/save-project", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type       = "save-project";
            cmd.param1     = j.at("path");
            cmd.boolParam1 = j.value("thumbnail", true);
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Save queued"},
                      {"path", cmd.param1}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── Bind and listen ───────────────────────────────────────────────────────
    // 127.0.0.1 only — no external network exposure.
    svr.listen("127.0.0.1", 50505);

    g_server = nullptr;
}

// ─── dylib destructor — called on unload (main thread on macOS) ───────────────
__attribute__((destructor))
static void PluginShutdown()
{
    g_serverRunning = false;

    if (g_server)
        g_server->stop();

    if (g_drainTimer) {
        g_drainTimer->stop();
        delete g_drainTimer;
        g_drainTimer = nullptr;
    }
}

// ─── CLO plugin entry points ──────────────────────────────────────────────────
#define CLO_EXPORT extern "C" __attribute__((visibility("default")))

CLO_EXPORT const char* GetActionName()
{
    return "REST Server";
}

CLO_EXPORT const char* GetObjectNameTreeToAddAction()
{
    return "";
}

CLO_EXPORT int GetPositionIndexToAddAction()
{
    return 0;
}

// DoFunction is called from the CLO main thread when the user clicks the menu item.
CLO_EXPORT void DoFunction()
{
    if (g_serverRunning.load()) {
        // Already running. If the queue has work and the timer somehow missed it,
        // drain manually so the user can use the menu as a fallback.
        bool hasWork = false;
        {
            std::lock_guard<std::mutex> lk(g_queueMutex);
            hasWork = !g_commandQueue.empty();
        }
        if (hasWork && !g_queueProcessing.load())
            ProcessCommandQueue();
        return;
    }

    // ── First invocation: start server + Qt drain timer ──────────────────────
    g_serverRunning = true;

    g_serverThread = std::thread(StartRESTServer);
    g_serverThread.detach();

    // QTimer must be created on the main thread so its events are processed by
    // CLO's Qt event loop. The lambda runs on the main thread on each tick.
    if (!g_drainTimer) {
        g_drainTimer = new QTimer(nullptr);
        g_drainTimer->setInterval(200);  // 200 ms — queue check interval
        QObject::connect(g_drainTimer, &QTimer::timeout, []() {
            if (!g_serverRunning.load() || g_queueProcessing.load()) return;
            bool hasWork = false;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                hasWork = !g_commandQueue.empty();
            }
            if (hasWork)
                ProcessCommandQueue();
        });
        g_drainTimer->start();
    }

    // Brief wait to allow the server thread to bind the port before returning.
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
}

CLO_EXPORT void DoFunctionAfterLoadingCLOFile(const char* /*fileExtension*/) {}

// DoFunctionContinuously is not called by CLO v2025; drain is handled by QTimer.
CLO_EXPORT void DoFunctionContinuously() {}
