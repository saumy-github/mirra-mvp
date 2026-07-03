#include "stdafx.h"
#include "CLOAPIInterface.h"
#include "CloNativePluginSupport.h"
#include "PluginBuildInfo.h"
#include "httplib.h"
#include <atomic>
#include <string>
#include <map>
#include <cstdio>    // sprintf_s — Phase 3 crash-dump filename formatting
#include <json.hpp>  // nlohmann json library
#include <dbghelp.h> // MiniDumpWriteDump — Phase 3 SEH crash dumps
#pragma comment(lib, "Dbghelp.lib")

using json = nlohmann::json;
using namespace httplib;

static const char* AvatarGenderLabel(int gender)
{
    switch (gender) {
    case 0: return "male";
    case 1: return "female";
    default: return "unknown";
    }
}

static std::string JsonPrimitiveToString(const json& value)
{
    if (value.is_string()) {
        return value.get<std::string>();
    }
    if (value.is_boolean() || value.is_number() || value.is_null()) {
        return value.dump();
    }
    throw std::runtime_error("Avatar property values must be JSON primitives");
}

static std::map<std::string, std::string> JsonObjectToStringMap(const json& objectValue)
{
    if (!objectValue.is_object()) {
        throw std::runtime_error("properties must be a JSON object");
    }

    std::map<std::string, std::string> result;
    for (auto it = objectValue.begin(); it != objectValue.end(); ++it) {
        result[it.key()] = JsonPrimitiveToString(it.value());
    }
    return result;
}

static std::vector<std::string> ComputeChangedPropertyKeys(
    const std::map<std::string, std::string>& before,
    const std::map<std::string, std::string>& after,
    const std::map<std::string, std::string>& requested
)
{
    std::vector<std::string> changed;
    for (const auto& [key, _] : requested) {
        auto beforeIt = before.find(key);
        auto afterIt = after.find(key);
        if (afterIt == after.end()) {
            continue;
        }
        if (beforeIt == before.end() || beforeIt->second != afterIt->second) {
            changed.push_back(key);
        }
    }
    return changed;
}

static std::vector<std::string> ComputeMissingAfterKeys(
    const std::map<std::string, std::string>& after,
    const std::map<std::string, std::string>& requested
)
{
    std::vector<std::string> missing;
    for (const auto& [key, _] : requested) {
        if (after.find(key) == after.end()) {
            missing.push_back(key);
        }
    }
    return missing;
}

// Command queue system for thread-safe API calls
#include <queue>
#include <mutex>
#include <future>
#include <condition_variable>
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
    std::map<std::string, std::string> stringMapParam1; // avatar properties

    // Sync-read support: if isSync==true the result is delivered via syncPromise
    // instead of appended to g_lastResults.
    bool                                   isSync      = false;
    std::shared_ptr<std::promise<json>>    syncPromise;
};

// ─── Result tracking ────────────────────────────────────────────────────────
struct CommandResult {
    std::string type;
    bool        success = false;
    std::string message;
};

static std::queue<APICommand>       g_commandQueue;
static std::mutex                   g_queueMutex;
static std::vector<CommandResult>   g_lastResults;
static std::mutex                   g_resultsMutex;
static std::atomic<bool>            g_queueProcessing{false};
static std::atomic<int>      g_patternsLoaded{0};
static Server*               g_server = nullptr;

struct ImportScaleEntry {
    std::string path;
    float scale = 1.0f;
    bool success = false;
};

static std::mutex g_importDebugMutex;
static float g_lastAvatarImportScale = 1.0f;
static std::string g_lastAvatarImportPath;
static bool g_lastAvatarImportSuccess = false;
static std::vector<ImportScaleEntry> g_lastPatternImports;
static std::mutex g_nativeAvatarDebugMutex;
static NativeAvatarDebugState g_nativeAvatarDebugState;

static std::mutex g_avatarPropertyDebugMutex;
static AvatarPropertyDebugState g_avatarPropertyDebugState;

// ─── Dynamic capability flags (Phase 3) ────────────────────────────────────
// Set once at startup by RunCapabilityProbesOnce() (called from DoFunction's
// first invocation) and refreshed after every real ExportAVT call. Replaces
// the previously hardcoded /capabilities values for these two fields.
static std::atomic<bool> g_capabilityAvatarAvtExport{false};
static std::atomic<bool> g_capabilityAvatarStateReadback{false};
static std::atomic<bool> g_capabilityProbesRun{false};

// Global flag to keep server running
static std::atomic<bool> g_serverRunning{false};
static std::thread g_serverThread;

// Forward declaration — defined later in this file.
void ProcessCommandQueue();

// Windows timer used to drain the command queue on CLO's main thread.
// SetTimer is called once from DoFunction(); the callback fires every 200ms
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

// ─── Arrangement debug helper ─────────────────────────────────────────────────
static json BuildArrangementDebugPayload()
{
    json slot_list = json::array();
    auto list = PATTERN_API->GetArrangementList();
    for (int i = 0; i < (int)list.size(); i++) {
        json entry = {{"index", i}};
        for (const auto& kv : list[i])
            entry[kv.first] = kv.second;
        slot_list.push_back(entry);
    }

    json patterns = json::array();
    int count = 0;
    try { count = PATTERN_API->GetPatternCount(); } catch (...) {}
    for (int i = 0; i < count; i++) {
        json entry = {{"pattern_index", i}};
        auto info = PATTERN_API->GetArrangementOfPattern(i);
        for (const auto& kv : info)
            entry[kv.first] = kv.second;
        patterns.push_back(entry);
    }

    return {
        {"success", true},
        {"slot_count", (int)slot_list.size()},
        {"slots", slot_list},
        {"pattern_arrangement_count", (int)patterns.size()},
        {"patterns", patterns}
    };
}

// ─── Sync-read helper ─────────────────────────────────────────────────────────
// Pushes a read command and blocks up to 3 s for the main thread result.
static json dispatchSyncRead(const std::string& type, int param3 = 0, int param4 = 0)
{
    auto promisePtr = std::make_shared<std::promise<json>>();
    auto future     = promisePtr->get_future();

    APICommand cmd;
    cmd.type        = type;
    cmd.param3      = param3;
    cmd.param4      = param4;
    cmd.isSync      = true;
    cmd.syncPromise = promisePtr;
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

// ─── SEH crash protection (Phase 3) ────────────────────────────────────────
// MSVC forbids mixing __try/__except with local C++ objects that require
// unwinding in the SAME function (compiler error C2712). Every function
// below that contains __try therefore has NO local objects with
// destructors — it only calls out to ordinary helper functions (which may
// freely use std::string etc.) to do the real work.

static std::string GetCrashDumpDirectory()
{
    char modulePath[MAX_PATH] = { 0 };
    HMODULE hModule = nullptr;
    GetModuleHandleExA(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCSTR>(&GetCrashDumpDirectory),
        &hModule
    );
    GetModuleFileNameA(hModule, modulePath, MAX_PATH);

    std::string dir = modulePath;
    size_t pos = dir.find_last_of("\\/");
    dir = (pos == std::string::npos) ? "." : dir.substr(0, pos);
    dir += "\\CrashDumps";
    CreateDirectoryA(dir.c_str(), nullptr);
    return dir;
}

// Ordinary function (no __try) — safe to use std::string/SYSTEMTIME/etc.
// Called synchronously from the __except filter expression below while the
// EXCEPTION_POINTERS* is still valid.
static void WriteMiniDumpToDisk(EXCEPTION_POINTERS* exceptionPointers, const char* label)
{
    SYSTEMTIME st;
    GetLocalTime(&st);
    char stamp[32];
    sprintf_s(stamp, sizeof(stamp), "%04d%02d%02d_%02d%02d%02d",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);

    std::string path = GetCrashDumpDirectory() + "\\" + label + "_" + stamp + ".dmp";

    HANDLE hFile = CreateFileA(path.c_str(), GENERIC_WRITE, 0, nullptr,
        CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (hFile == INVALID_HANDLE_VALUE) return;

    MINIDUMP_EXCEPTION_INFORMATION mdei;
    mdei.ThreadId          = GetCurrentThreadId();
    mdei.ExceptionPointers = exceptionPointers;
    mdei.ClientPointers    = FALSE;

    MiniDumpWriteDump(
        GetCurrentProcess(),
        GetCurrentProcessId(),
        hFile,
        MiniDumpWithFullMemory,
        exceptionPointers ? &mdei : nullptr,
        nullptr,
        nullptr
    );
    CloseHandle(hFile);
}

// Valid only as (or from) the direct operand of __except — must be evaluated
// while the EXCEPTION_POINTERS* from GetExceptionInformation() is still live.
static LONG SEHFilterWriteDump(EXCEPTION_POINTERS* ep, const char* label)
{
    WriteMiniDumpToDisk(ep, label);
    return EXCEPTION_EXECUTE_HANDLER;
}

typedef bool (*SEHProbeFn)(void* context);

// The only function in this file whose __try scope must stay free of any
// local C++ object with a destructor: fn is a function pointer, context is a
// raw void*, both PODs. All real work happens inside fn(), an ordinary
// function that is free to use std::string, exceptions, etc.
static bool RunSEHGuarded(SEHProbeFn fn, void* context, const char* label)
{
    __try
    {
        return fn(context);
    }
    __except (SEHFilterWriteDump(GetExceptionInformation(), label))
    {
        return false;
    }
}

// ── ExportAVT: known to raise SEH exceptions even on the main thread ───────
static bool CallExportAVTOnce(void* context)
{
    const std::string* pathIn = static_cast<const std::string*>(context);
    return !EXPORT_API->ExportAVT(*pathIn).empty();
}

static bool ExportAVT_SEHSafe(const std::string& path)
{
    return RunSEHGuarded(
        CallExportAVTOnce,
        const_cast<void*>(static_cast<const void*>(&path)),
        "ExportAVT"
    );
}

// ── Startup capability probes ───────────────────────────────────────────────
// Runs once per plugin session (guarded by g_capabilityProbesRun), from the
// first DoFunction() invocation — the earliest point in this SDK's plugin
// lifecycle where the CLO API pointers (IMPORT_API/EXPORT_API/etc.) are known
// to be initialized. There is no DLL-load-time hook in this SDK sample that
// is safe for this (DllMain runs under the loader lock, before CLO has wired
// up the API pointers), so "plugin load" is interpreted as "first click."
//
// IMPORTANT: neither probe actually runs automatically right now. A live
// test (2026-07-03) showed CLO closing immediately when the ExportAVT probe
// ran automatically at startup, with no .dmp written to CrashDumps —
// meaning the fault bypassed the __try/__except wrapper entirely (this can
// happen if the real crash is on another thread, a stack overflow, an
// internal abort()/assertion, or a vectored exception handler CLO itself
// registers ahead of our frame-based handler). Calling any previously-
// unexercised CLO API unconditionally on every plugin session start — before
// the server thread even exists — is worse than the capability flag being
// stale, since it blocks the whole pipeline.
//
// CallAvatarStateProbeOnce() has no known crash history the way ExportAVT
// does, but it is exercised here at the exact same early, untested point in
// the lifecycle (right after the message box, before the timer/server
// start), so it is left disabled too until there is a reason to believe it's
// safe there. has_avatar_state_readback is instead set to true from real
// usage inside the "read-avatar-state" branch of ProcessCommandQueue, which
// already existed before Phase 3 and has an established track record via
// dispatchSyncRead. has_avatar_avt_export is likewise only set from a real
// /export-avatar-avt request (see ProcessCommandQueue), via ExportAVT_SEHSafe.
static void RunCapabilityProbesOnce()
{
    if (g_capabilityProbesRun.exchange(true)) return;
    // Intentionally empty for now — see comment above.
}

// HTTP Server Implementation
void StartRESTServer()
{
    try {
        Server svr;
        g_server = &svr;

        // Health check endpoint
        svr.Get("/health", [](const Request&, Response& res) {
            json response = {
                {"status", "ok"},
                {"plugin", MIRRA_PLUGIN_NAME},
                {"version", MIRRA_PLUGIN_VERSION},
                {"api_version", MIRRA_PLUGIN_API_VERSION},
                {"release_date", MIRRA_PLUGIN_RELEASE_DATE},
                {"release_status", MIRRA_PLUGIN_RELEASE_STATUS},
                {"platform", MIRRA_PLUGIN_PLATFORM},
                {"platform_sync_state", MIRRA_PLUGIN_PLATFORM_SYNC_STATE},
                {"contract_name", MIRRA_PLUGIN_CONTRACT_NAME},
                {"contract_version", MIRRA_PLUGIN_CONTRACT_VERSION},
                {"plugin_built_at", MIRRA_PLUGIN_BUILD_TIME}
            };
            res.set_content(response.dump(), "application/json");
        });

        // Capability descriptor for orchestration layer.
        svr.Get("/capabilities", [](const Request&, Response& res) {
            json response = {
                {"success", true},
                {"plugin_version", MIRRA_PLUGIN_VERSION},
                {"api_version", MIRRA_PLUGIN_API_VERSION},
                {"release_status", MIRRA_PLUGIN_RELEASE_STATUS},
                {"platform", MIRRA_PLUGIN_PLATFORM},
                {"has_scene_geometry_probe", true},
                {"has_pattern_line_count", false},
                {"has_pattern_bbox", true},
                {"has_pattern_line_length_probe", true},
                {"has_pattern_input_info", true},
                {"has_arrangement_list", true},
                {"has_pattern_arrangements", true},
                {"has_avatar_debug", true},
                {"has_native_avatar_import", true},
                {"has_avatar_measurement_import", true},
                {"has_native_avatar_debug", true},
                {"has_avatar_property_set", true},
                {"has_avatar_property_debug", true},
                {"has_avatar_state_readback", g_capabilityAvatarStateReadback.load()},
                {"has_avatar_avt_export", g_capabilityAvatarAvtExport.load()},
                {"notes", "has_avatar_state_readback and has_avatar_avt_export are set from a startup SEH-guarded probe (Phase 3), not hardcoded. Line count may be absent in GetPatternInformation; use line-length probe endpoint"}
            };
            res.set_content(response.dump(), "application/json");
        });

        // Debug endpoint exposing actual import scales used in the last runs.
        svr.Get("/debug/import-scales", [](const Request&, Response& res) {
            json patternImports = json::array();
            float avatarScale = 1.0f;
            std::string avatarPath;
            bool avatarSuccess = false;

            {
                std::lock_guard<std::mutex> lock(g_importDebugMutex);
                avatarScale = g_lastAvatarImportScale;
                avatarPath = g_lastAvatarImportPath;
                avatarSuccess = g_lastAvatarImportSuccess;
                for (const auto& row : g_lastPatternImports) {
                    patternImports.push_back({
                        {"path", row.path},
                        {"scale", row.scale},
                        {"success", row.success}
                    });
                }
            }

            json response = {
                {"success", true},
                {"avatar_import", {
                    {"path", avatarPath},
                    {"scale", avatarScale},
                    {"success", avatarSuccess}
                }},
                {"pattern_imports", patternImports}
            };
            res.set_content(response.dump(), "application/json");
        });

        // Avatar + arrangement readiness debug endpoint.
        svr.Get("/avatar/debug", [](const Request&, Response& res) {
            json r = dispatchSyncRead("read-avatar-debug");
            res.set_content(r.dump(), "application/json");
        });

        // Native-avatar debug endpoint for the isolated CLO-native experiment.
        svr.Get("/avatar/native-debug", [](const Request&, Response& res) {
            json r = dispatchSyncRead("read-avatar-native-debug");
            res.set_content(r.dump(), "application/json");
        });

        // Experimental avatar-property debug endpoint for JSON/property mutation research.
        svr.Get("/avatar/property-debug", [](const Request&, Response& res) {
            try {
                AvatarPropertyDebugState snapshot;
                {
                    std::lock_guard<std::mutex> lock(g_avatarPropertyDebugMutex);
                    snapshot = g_avatarPropertyDebugState;
                }
                res.set_content(BuildAvatarPropertyDebugJson(snapshot).dump(), "application/json");
            }
            catch (const std::exception& e) {
                json response = {{"success", false}, {"error", e.what()}};
                res.set_content(response.dump(), "application/json");
            }
        });

        // Avatar state readback — routes to main thread via dispatchSyncRead.
        svr.Get("/avatars/state", [](const Request&, Response& res) {
            json r = dispatchSyncRead("read-avatar-state");
            res.set_content(r.dump(), "application/json");
        });

    // Import Avatar (OBJ file) - QUEUED
    svr.Post("/import-avatar", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string filePath = j["path"];
            float scale = j.value("scale", 1.0f);
            
            APICommand cmd;
            cmd.type = "import-avatar";
            cmd.param1 = filePath;
            cmd.floatParam1 = scale;
            
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }
            
            json response = {
                {"success", true},
                {"message", "Avatar import queued. Call /execute to process."},
                {"path", filePath},
                {"scale", scale},
                {"queue_size", g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Import native CLO avatar template (.avt) - QUEUED
    svr.Post("/import-avatar-avt", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string filePath = j["path"];

            APICommand cmd;
            cmd.type = "import-avatar-avt";
            cmd.param1 = filePath;

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success", true},
                {"message", "Native avatar import queued. Call /execute to process."},
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

    // Import native avatar measurement CSV - QUEUED
    svr.Post("/import-avatar-measurements", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string csvPath = j["csv_path"];
            std::string templatePath = j.value("template_path", "");

            APICommand cmd;
            cmd.type = "import-avatar-measurements";
            cmd.param1 = csvPath;
            cmd.param2 = templatePath;

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success", true},
                {"message", "Avatar measurement import queued. Call /execute to process."},
                {"csv_path", csvPath},
                {"template_path", templatePath},
                {"queue_size", g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Experimental JSON/property path for avatar mutation research.
    // This does not replace CSV import; it gives us a second route to test
    // whether CLO's avatar property setter can control body values directly.
    svr.Post("/avatar/set-properties", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            if (!j.contains("properties")) {
                throw std::runtime_error("Missing required field: properties");
            }

            APICommand cmd;
            cmd.type = "avatar-set-properties";
            cmd.param3 = j.value("avatar_index", 0);
            cmd.param2 = j.value("unit", std::string("raw"));
            cmd.stringMapParam1 = JsonObjectToStringMap(j["properties"]);

            json propertyKeys = json::array();
            for (const auto& [key, _] : cmd.stringMapParam1) {
                propertyKeys.push_back(key);
            }

            int queueSize = 0;
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
                queueSize = (int)g_commandQueue.size();
            }

            json response = {
                {"success", true},
                {"message", "Avatar property update queued"},
                {"avatar_index", cmd.param3},
                {"unit", cmd.param2},
                {"property_count", (int)cmd.stringMapParam1.size()},
                {"property_keys", propertyKeys},
                {"queue_size", queueSize}
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
            float scale = j.value("scale", 1.0f);
            
            APICommand cmd;
            cmd.type = "import-pattern";
            cmd.param1 = filePath;
            cmd.floatParam1 = scale;
            
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }
            
            json response = {
                {"success", true},
                {"message", "Pattern import queued. Call /execute to process."},
                {"path", filePath},
                {"scale", scale},
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
        json r = dispatchSyncRead("read-pattern-count");
        res.set_content(r.dump(), "application/json");
    });

    // Get Pattern Information
    svr.Get("/patterns/(\\d+)", [](const Request& req, Response& res) {
        int patternIndex = std::stoi(req.matches[1]);
        json r = dispatchSyncRead("read-pattern-info", patternIndex);
        res.set_content(r.dump(), "application/json");
    });

    // Get Pattern Bounding Box / area (SDK-backed geometry signal)
    svr.Get("/patterns/(\\d+)/bbox", [](const Request& req, Response& res) {
        int patternIndex = std::stoi(req.matches[1]);
        json r = dispatchSyncRead("read-pattern-bbox", patternIndex);
        res.set_content(r.dump(), "application/json");
    });

    // Get Pattern Input Information (raw + parsed when possible)
    svr.Get("/patterns/(\\d+)/input", [](const Request& req, Response& res) {
        int patternIndex = std::stoi(req.matches[1]);
        json r = dispatchSyncRead("read-pattern-input", patternIndex);
        res.set_content(r.dump(), "application/json");
    });

    // Probe line lengths by index when line_count is missing from metadata.
    svr.Get("/patterns/(\\d+)/line-lengths", [](const Request& req, Response& res) {
        int patternIndex = std::stoi(req.matches[1]);
        int maxLines = 256;
        if (req.has_param("max")) {
            try { maxLines = std::stoi(req.get_param_value("max")); } catch (...) {}
        }
        json r = dispatchSyncRead("read-pattern-line-lengths", patternIndex, maxLines);
        res.set_content(r.dump(), "application/json");
    });

    // Save Project as ZPRJ - QUEUED (main-thread safe)
    svr.Post("/save-project", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type = "save-project";
            cmd.param1 = j["path"];
            cmd.param3 = j.value("thumbnail", true) ? 1 : 0;

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success", true},
                {"message", "Project save queued"},
                {"path", cmd.param1},
                {"queue_size", (int)g_commandQueue.size()}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Export current avatar as AVT - QUEUED (main-thread safe)
    svr.Post("/export-avatar-avt", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type = "export-avatar-avt";
            cmd.param1 = j["path"];

            int queueSize = 0;
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
                queueSize = (int)g_commandQueue.size();
            }

            json response = {
                {"success", true},
                {"message", "Avatar AVT export queued"},
                {"path", cmd.param1},
                {"queue_size", queueSize}
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
        json r = dispatchSyncRead("read-arrangement-list");
        res.set_content(r.dump(), "application/json");
    });

    // ── Arrangement of loaded patterns — read current arrangement per pattern ──
    svr.Get("/pattern-arrangements", [](const Request&, Response& res) {
        json r = dispatchSyncRead("read-pattern-arrangements");
        res.set_content(r.dump(), "application/json");
    });

    // ── Arrangement debug payload: raw slots + per-pattern arrangement in one call.
    svr.Get("/arrangement/debug", [](const Request&, Response& res) {
        json r = dispatchSyncRead("read-arrangement-debug");
        res.set_content(r.dump(), "application/json");
    });

    // ── Status — queue state + last batch results (read-only, no queue) ──────
    svr.Get("/status", [](const Request&, Response& res) {
        try {
            int  queueSize  = 0;
            bool processing = g_queueProcessing;

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                queueSize = (int)g_commandQueue.size();
            }

            int patternsLoaded = g_patternsLoaded.load();

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
        bool success = svr.listen("127.0.0.1", 50505);
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
    }
    catch (...) {
        g_serverRunning = false;
    }
    g_server = nullptr;
}

void PluginShutdown()
{
    g_serverRunning = false;
    if (g_timerId != 0) { KillTimer(NULL, g_timerId); g_timerId = 0; }
    if (g_server != nullptr) { g_server->stop(); }
}

// ─────────────────────────────────────────────────────────────────────────────
// ProcessCommandQueue — MUST be called from CLO's main thread.
// ─────────────────────────────────────────────────────────────────────────────
void ProcessCommandQueue()
{
    // Atomic re-entrancy guard: exchange returns the previous value.
    // If already true, another drain is in progress — bail immediately.
    if (g_queueProcessing.exchange(true)) return;

    std::vector<APICommand> batch;
    {
        std::lock_guard<std::mutex> lock(g_queueMutex);
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
    // Pure sync-read batches (e.g. /avatars/state) must not wipe the last results.
    bool hasAsync = false;
    for (const auto& c : batch) if (!c.isSync) { hasAsync = true; break; }
    if (hasAsync) {
        std::lock_guard<std::mutex> rlock(g_resultsMutex);
        g_lastResults.clear();
    }

    for (auto& cmd : batch) {
        json syncResult;
        CommandResult asyncResult;
        asyncResult.type    = cmd.type;
        asyncResult.success = false;

        try {
            // ── Avatar import ─────────────────────────────────────────────
            if (cmd.type == "import-avatar") {
                Marvelous::ImportExportOption options;
                options.scale           = (cmd.floatParam1 > 0.0f ? cmd.floatParam1 : 1.0f);
                options.ImportObjectType = 0;
                options.bAutoTranslate  = true;
                asyncResult.success  = IMPORT_API->ImportOBJ(cmd.param1, options);
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastAvatarImportScale   = options.scale;
                    g_lastAvatarImportPath    = cmd.param1;
                    g_lastAvatarImportSuccess = asyncResult.success;
                }
                asyncResult.message = asyncResult.success
                    ? "Imported avatar: " + cmd.param1 + " (scale=" + std::to_string(options.scale) + ")"
                    : "Failed to import avatar: " + cmd.param1;
            }
            // ── Native avatar import (.avt) ───────────────────────────────
            else if (cmd.type == "import-avatar-avt") {
                Marvelous::ImportExportOption options;
                options.scale = 1.0f;
                asyncResult.success = IMPORT_API->ImportAvatar(cmd.param1, options);
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState.last_native_avatar_path    = cmd.param1;
                    g_nativeAvatarDebugState.last_native_avatar_success = asyncResult.success;
                    g_nativeAvatarDebugState.last_message = asyncResult.success
                        ? "Imported native avatar template"
                        : "Failed to import native avatar template";
                }
                asyncResult.message = asyncResult.success
                    ? "Imported native avatar template: " + cmd.param1
                    : "Failed to import native avatar template: " + cmd.param1;
            }
            else if (cmd.type == "import-avatar-measurements") {
                bool measurementOk = false;
                if (!cmd.param2.empty()) {
                    Marvelous::ImportExportOption options;
                    options.scale = 1.0f;
                    measurementOk = IMPORT_API->ImportAvatarMeasurement(cmd.param1, cmd.param2, options);
                }
                else {
                    measurementOk = IMPORT_API->ImportMeasurement(cmd.param1);
                }
                asyncResult.success = measurementOk;
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState.last_measurement_csv_path      = cmd.param1;
                    g_nativeAvatarDebugState.last_measurement_template_path = cmd.param2;
                    g_nativeAvatarDebugState.last_measurement_csv_success   = asyncResult.success;
                    g_nativeAvatarDebugState.last_message = asyncResult.success
                        ? "Imported native avatar measurement CSV"
                        : "Failed to import native avatar measurement CSV";
                }
                asyncResult.message = asyncResult.success
                    ? "Imported native avatar measurements: " + cmd.param1
                    : "Failed to import native avatar measurements: " + cmd.param1;
            }
            else if (cmd.type == "avatar-set-properties") {
                AvatarPropertyDebugState debugState;
                debugState.avatar_index          = (cmd.param3 >= 0 ? static_cast<unsigned int>(cmd.param3) : 0);
                debugState.unit                  = (cmd.param2.empty() ? "raw" : cmd.param2);
                debugState.requested_properties  = cmd.stringMapParam1;

                try {
                    try {
                        debugState.properties_before = UTILITY_API->GetAvatarProperties(debugState.avatar_index);
                    }
                    catch (...) {}

                    UTILITY_API->SetAvatarProperties(debugState.avatar_index, cmd.stringMapParam1);

                    try {
                        debugState.properties_after = UTILITY_API->GetAvatarProperties(debugState.avatar_index);
                    }
                    catch (...) {}

                    debugState.changed_keys = ComputeChangedPropertyKeys(
                        debugState.properties_before,
                        debugState.properties_after,
                        debugState.requested_properties
                    );
                    debugState.missing_after_keys = ComputeMissingAfterKeys(
                        debugState.properties_after,
                        debugState.requested_properties
                    );
                    asyncResult.success = true;
                    asyncResult.message =
                        "Avatar properties applied to avatar " + std::to_string(debugState.avatar_index) +
                        " (requested=" + std::to_string(debugState.requested_properties.size()) +
                        ", changed=" + std::to_string(debugState.changed_keys.size()) +
                        ", missing_after=" + std::to_string(debugState.missing_after_keys.size()) + ")";
                    debugState.success      = true;
                    debugState.last_message = asyncResult.message;
                }
                catch (const std::exception& e) {
                    asyncResult.success     = false;
                    asyncResult.message     = "Failed to set avatar properties: " + std::string(e.what());
                    debugState.success      = false;
                    debugState.last_message = asyncResult.message;
                }
                catch (...) {
                    asyncResult.success     = false;
                    asyncResult.message     = "Failed to set avatar properties: unknown exception";
                    debugState.success      = false;
                    debugState.last_message = asyncResult.message;
                }

                {
                    std::lock_guard<std::mutex> lock(g_avatarPropertyDebugMutex);
                    g_avatarPropertyDebugState = debugState;
                }
            }
            else if (cmd.type == "import-pattern") {
                Marvelous::ImportDxfOption options;
                options.m_Scale   = (cmd.floatParam1 > 0.0f ? cmd.floatParam1 : 1.0f);
                options.m_bAppend = true;
                asyncResult.success = IMPORT_API->ImportDXF(cmd.param1, options);
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastPatternImports.push_back({cmd.param1, options.m_Scale, asyncResult.success});
                    if (g_lastPatternImports.size() > 64)
                        g_lastPatternImports.erase(g_lastPatternImports.begin(), g_lastPatternImports.begin() + 32);
                }
                asyncResult.message = asyncResult.success
                    ? "Imported pattern: " + cmd.param1 + " (scale=" + std::to_string(options.m_Scale) + ")"
                    : "Failed to import pattern: " + cmd.param1;
                if (asyncResult.success)
                    g_patternsLoaded++;
            }
            // ── Create seam ───────────────────────────────────────────────
            else if (cmd.type == "create-seam") {
                asyncResult.success = PATTERN_API->AddSeamlinePairGroup(
                    cmd.param3, cmd.param4,
                    cmd.param5, cmd.param6,
                    cmd.boolParam1, cmd.boolParam2
                );
                asyncResult.message = asyncResult.success
                    ? "Seam: pattern " + std::to_string(cmd.param3) +
                      " edge " + std::to_string(cmd.param4) +
                      " <-> pattern " + std::to_string(cmd.param5) +
                      " edge " + std::to_string(cmd.param6)
                    : "Failed to create seam";
            }
            // ── Simulation ────────────────────────────────────────────────
            else if (cmd.type == "simulate") {
                asyncResult.success = UTILITY_API->Simulate((unsigned int)cmd.param3);
                asyncResult.message = asyncResult.success
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
                asyncResult.success = !out.empty();
                asyncResult.message = asyncResult.success
                    ? "Exported to: " + cmd.param1
                    : "Export failed";
            }
            // ── New project ───────────────────────────────────────────────
            else if (cmd.type == "new-project") {
                UTILITY_API->NewProject();
                g_patternsLoaded = 0;
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastPatternImports.clear();
                    g_lastAvatarImportPath.clear();
                    g_lastAvatarImportScale   = 1.0f;
                    g_lastAvatarImportSuccess = false;
                }
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState = NativeAvatarDebugState{};
                }
                {
                    std::lock_guard<std::mutex> lock(g_avatarPropertyDebugMutex);
                    g_avatarPropertyDebugState = AvatarPropertyDebugState{};
                }
                asyncResult.success = true;
                asyncResult.message = "New project created";
            }
            // ── Arrange pattern in 3D space ───────────────────────────────
            // param3 = patternIndex, param4 = arrangementIndex (-1 = skip SetArrangement)
            // floatParam1/2/3 = X/Y/Z offset in mm, param5 = orientation enum
            else if (cmd.type == "arrange-pattern") {
                if (cmd.param4 >= 0)
                    PATTERN_API->SetArrangement(cmd.param3, cmd.param4);
                PATTERN_API->SetArrangementPosition(
                    cmd.param3,
                    (int)cmd.floatParam1,
                    (int)cmd.floatParam2,
                    (int)cmd.floatParam3
                );
                if (cmd.param5 != 0)
                    PATTERN_API->SetArrangementOrientation(cmd.param3, cmd.param5);
                asyncResult.success = true;
                asyncResult.message = "Pattern " + std::to_string(cmd.param3) +
                    (cmd.param4 >= 0 ? " -> arrangement slot " + std::to_string(cmd.param4) : " position set") +
                    " pos=(" + std::to_string((int)cmd.floatParam1) +
                    "," + std::to_string((int)cmd.floatParam2) +
                    "," + std::to_string((int)cmd.floatParam3) + ")mm";
            }
            // ── Set fabric ────────────────────────────────────────────────
            else if (cmd.type == "set-fabric") {
                PATTERN_API->SetPatternPieceFabricIndex(cmd.param3, cmd.param4);
                asyncResult.success = true;
                asyncResult.message = "Fabric index " + std::to_string(cmd.param4) +
                    " applied to pattern " + std::to_string(cmd.param3);
            }
            // ── Save project ──────────────────────────────────────────────
            else if (cmd.type == "save-project") {
                bool thumb  = (cmd.param3 != 0);
                std::string out = EXPORT_API->ExportZPrj(cmd.param1, thumb);
                asyncResult.success = !out.empty();
                asyncResult.message = asyncResult.success
                    ? "Project saved: " + out
                    : "Save failed";
            }
            else if (cmd.type == "export-avatar-avt") {
                // Phase 3: routed through the SEH-safe wrapper so a hardware
                // exception from ExportAVT is contained (minidump written,
                // false returned) instead of crashing CLO's main thread.
                bool exportOk = ExportAVT_SEHSafe(cmd.param1);
                g_capabilityAvatarAvtExport = exportOk;
                asyncResult.success = exportOk;
                asyncResult.message = exportOk
                    ? "Avatar exported via ExportAVT: " + cmd.param1
                    : "ExportAVT failed or raised a hardware exception (SEH) — check the CrashDumps folder next to the plugin DLL for a .dmp if one was written";
            }
            // ── Sync reads (all called via dispatchSyncRead) ──────────────
            else if (cmd.type == "read-pattern-count") {
                int cnt = 0;
                bool ok = false;
                try { cnt = PATTERN_API->GetPatternCount(); ok = true; } catch (...) {}
                if (ok) g_patternsLoaded = cnt;
                syncResult = {{"success", ok}, {"count", cnt}};
            }
            else if (cmd.type == "read-pattern-info") {
                int total = 0;
                try { total = PATTERN_API->GetPatternCount(); } catch (...) {}
                int idx = cmd.param3;
                if (idx < 0 || idx >= total) {
                    syncResult = {
                        {"success", false},
                        {"error",   "invalid index"},
                        {"message", "Pattern index " + std::to_string(idx) +
                                    " out of range (count=" + std::to_string(total) + ")"}
                    };
                } else {
                    std::string raw;
                    bool cloOk = false;
                    try { raw = PATTERN_API->GetPatternInformation(idx); cloOk = true; } catch (...) {}
                    json parsed;
                    try { parsed = json::parse(raw); }
                    catch (...) { parsed = raw; }
                    syncResult = {
                        {"success",       cloOk},
                        {"pattern_index", idx},
                        {"info",          parsed}
                    };
                }
            }
            else if (cmd.type == "read-pattern-bbox") {
                int patternIndex = cmd.param3;
                json bbox = json::object();
                float area = 0.0f;
                bool bboxOk = false;
                try {
                    auto raw = PATTERN_API->GetBoundingBoxOfPattern(patternIndex);
                    for (const auto& kv : raw)
                        bbox[kv.first] = kv.second;
                    bboxOk = true;
                } catch (...) {}
                try { area = PATTERN_API->GetPatternPieceArea(patternIndex); } catch (...) {}
                syncResult = {
                    {"success",       bboxOk},
                    {"pattern_index", patternIndex},
                    {"bbox",          bbox},
                    {"area",          area}
                };
            }
            else if (cmd.type == "read-pattern-input") {
                int patternIndex = cmd.param3;
                std::string inputInfo;
                bool cloOk = false;
                try { inputInfo = PATTERN_API->GetPatternInputInformation(patternIndex); cloOk = true; } catch (...) {}
                json parsed;
                bool parsedOk = false;
                try {
                    parsed   = json::parse(inputInfo);
                    parsedOk = true;
                }
                catch (...) {
                    parsed = json::object();
                }
                syncResult = {
                    {"success",       cloOk},
                    {"pattern_index", patternIndex},
                    {"parsed",        parsedOk},
                    {"input",         parsedOk ? parsed : json(inputInfo)}
                };
            }
            else if (cmd.type == "read-pattern-line-lengths") {
                int patternIndex = cmd.param3;
                int maxLines     = (cmd.param4 > 0 ? cmd.param4 : 256);
                int stopAfterConsecutiveZero = 12;
                json lines = json::array();
                int zeroStreak = 0;
                for (int i = 0; i < maxLines; i++) {
                    float len = 0.0f;
                    try { len = PATTERN_API->GetLineLength(patternIndex, i); }
                    catch (...) { len = 0.0f; }
                    if (len > 0.0001f) {
                        lines.push_back({{"line_index", i}, {"length", len}});
                        zeroStreak = 0;
                    } else {
                        zeroStreak++;
                        if (!lines.empty() && zeroStreak >= stopAfterConsecutiveZero)
                            break;
                    }
                }
                syncResult = {
                    {"success",       true},
                    {"pattern_index", patternIndex},
                    {"line_count",    (int)lines.size()},
                    {"lines",         lines}
                };
            }
            else if (cmd.type == "read-arrangement-list") {
                json slotList = json::array();
                bool ok = false;
                try {
                    auto list = PATTERN_API->GetArrangementList();
                    ok = true;
                    for (int i = 0; i < (int)list.size(); i++) {
                        json entry = {{"index", i}};
                        for (const auto& kv : list[i])
                            entry[kv.first] = kv.second;
                        slotList.push_back(entry);
                    }
                } catch (...) {}
                syncResult = {
                    {"success", ok},
                    {"count",   (int)slotList.size()},
                    {"slots",   slotList}
                };
            }
            else if (cmd.type == "read-pattern-arrangements") {
                json patterns = json::array();
                int count = 0;
                try { count = PATTERN_API->GetPatternCount(); } catch (...) {}
                for (int i = 0; i < count; i++) {
                    json entry = {{"pattern_index", i}};
                    try {
                        auto info = PATTERN_API->GetArrangementOfPattern(i);
                        for (const auto& kv : info)
                            entry[kv.first] = kv.second;
                    } catch (...) {}
                    patterns.push_back(entry);
                }
                syncResult = {{"success", true}, {"patterns", patterns}};
            }
            else if (cmd.type == "read-arrangement-debug") {
                try { syncResult = BuildArrangementDebugPayload(); }
                catch (...) { syncResult = {{"success", false}, {"error", "exception in BuildArrangementDebugPayload"}}; }
            }
            else if (cmd.type == "read-avatar-debug") {
                float avatarScale = 1.0f;
                std::string avatarPath;
                bool avatarSuccess = false;
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    avatarScale   = g_lastAvatarImportScale;
                    avatarPath    = g_lastAvatarImportPath;
                    avatarSuccess = g_lastAvatarImportSuccess;
                }
                int patternCount = 0;
                try { patternCount = PATTERN_API->GetPatternCount(); } catch (...) {}
                int slotCount = 0;
                try {
                    auto slotList = PATTERN_API->GetArrangementList();
                    slotCount = (int)slotList.size();
                } catch (...) {}
                int patternArrangementCount = 0;
                for (int i = 0; i < patternCount; i++) {
                    try {
                        auto rec = PATTERN_API->GetArrangementOfPattern(i);
                        if (!rec.empty()) patternArrangementCount++;
                    }
                    catch (...) {}
                }
                std::string anchorMode = "none";
                std::string semanticsQuality = "none";
                if (avatarSuccess && slotCount > 0) {
                    anchorMode        = "semantic_slots";
                    semanticsQuality  = (slotCount >= 4 ? "high" : "medium");
                } else if (avatarSuccess && slotCount == 0 && patternArrangementCount > 0) {
                    anchorMode        = "generic_arrangement_point";
                    semanticsQuality  = "low";
                } else if (avatarSuccess) {
                    anchorMode        = "imported_mesh_avatar";
                    semanticsQuality  = "none";
                }
                syncResult = {
                    {"success", true},
                    {"avatar_import", {
                        {"path",    avatarPath},
                        {"scale",   avatarScale},
                        {"success", avatarSuccess}
                    }},
                    {"pattern_count",               patternCount},
                    {"arrangement_list_populated",  slotCount > 0},
                    {"arrangement_slot_count",      slotCount},
                    {"pattern_arrangement_count",   patternArrangementCount},
                    {"avatar_anchor_mode",          anchorMode},
                    {"arrangement_semantics_quality", semanticsQuality}
                };
            }
            else if (cmd.type == "read-avatar-native-debug") {
                NativeAvatarDebugState snapshot;
                int patternCount = 0;
                int patternArrangementCount = 0;
                int arrangementSlotCount = 0;
                std::vector<std::string> slotNames;
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    snapshot = g_nativeAvatarDebugState;
                }
                try { patternCount = PATTERN_API->GetPatternCount(); } catch (...) {}
                try {
                    auto list = PATTERN_API->GetArrangementList();
                    arrangementSlotCount = (int)list.size();
                    for (const auto& row : list) {
                        auto it = row.find("name");
                        if (it != row.end()) { slotNames.push_back(it->second); continue; }
                        auto an = row.find("ArrangementName");
                        if (an != row.end()) { slotNames.push_back(an->second); continue; }
                        auto desc = row.find("description");
                        if (desc != row.end()) slotNames.push_back(desc->second);
                    }
                } catch (...) {}
                for (int i = 0; i < patternCount; i++) {
                    try {
                        auto rec = PATTERN_API->GetArrangementOfPattern(i);
                        if (!rec.empty()) patternArrangementCount++;
                    } catch (...) {}
                }
                syncResult = BuildNativeAvatarDebugJson(
                    snapshot,
                    arrangementSlotCount,
                    patternArrangementCount,
                    patternCount,
                    slotNames
                );
            }
            else if (cmd.type == "read-avatar-state") {
                unsigned int avatarCount = 0;
                std::vector<std::string> avatarNames;
                std::vector<int> avatarGenders;
                json avatars = json::array();

                try { avatarCount   = EXPORT_API->GetAvatarCount();    } catch (...) {}
                try { avatarNames   = EXPORT_API->GetAvatarNameList();  } catch (...) {}
                try { avatarGenders = EXPORT_API->GetAvatarGenderList(); } catch (...) {}

                for (unsigned int i = 0; i < avatarCount; ++i) {
                    std::map<std::string, std::string> properties;
                    try { properties = UTILITY_API->GetAvatarProperties(i); } catch (...) {}

                    json propertyJson = json::object();
                    for (const auto& kv : properties)
                        propertyJson[kv.first] = kv.second;

                    std::string avatarName =
                        (i < avatarNames.size() ? avatarNames[i] : ("avatar_" + std::to_string(i)));
                    int avatarGender =
                        (i < avatarGenders.size() ? avatarGenders[i] : -1);

                    avatars.push_back({
                        {"index",       i},
                        {"name",        avatarName},
                        {"gender_code", avatarGender},
                        {"gender",      AvatarGenderLabel(avatarGender)},
                        {"properties",  propertyJson}
                    });
                }

                // Reached without a hard crash — this handler has run
                // successfully (real GetAvatarCount/NameList/GenderList
                // calls, individually try/catch-guarded above since Phase 1).
                g_capabilityAvatarStateReadback = true;

                syncResult = {
                    {"success",      true},
                    {"avatar_count", avatarCount},
                    {"avatars",      avatars}
                };
            }
            else {
                asyncResult.message = "Unknown command type: " + cmd.type;
                syncResult = {{"success", false}, {"error", "unknown command: " + cmd.type}};
            }
        }
        catch (const std::exception& e) {
            asyncResult.success = false;
            asyncResult.message = "Exception in '" + cmd.type + "': " + std::string(e.what());
            syncResult = {{"success", false}, {"error", e.what()}};
        }
        catch (...) {
            asyncResult.success = false;
            asyncResult.message = "Unknown exception in '" + cmd.type + "'";
            syncResult = {{"success", false}, {"error", "unknown exception — CLO threw a non-std type"}};
        }

        if (cmd.isSync && cmd.syncPromise) {
            cmd.syncPromise->set_value(syncResult);
        } else {
            std::lock_guard<std::mutex> rlock(g_resultsMutex);
            g_lastResults.push_back(asyncResult);
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
            UTILITY_API->DisplayMessageBox("Starting REST server on http://localhost:50505\n\nQueue drains automatically every 200 ms — no further menu clicks needed.");

            // Phase 3: probe SEH-crash-prone CLO APIs once, on the main
            // thread, before the server starts taking requests, so
            // /capabilities reflects what actually works this session.
            RunCapabilityProbesOnce();

            g_serverRunning = true;
            g_serverThread = std::thread(StartRESTServer);
            g_serverThread.detach();

            // Register a 200ms Windows timer so the queue is drained on the
            // main thread automatically (CLO v2025 has no DoFunctionContinuously).
            if (g_timerId == 0) {
                g_timerId = SetTimer(NULL, 0, 200, QueueDrainTimer);
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
// Queue draining is handled by QueueDrainTimer (SetTimer, 200ms).
CLO_PLUGIN_SPECIFIER void DoFunctionContinuously() { }
