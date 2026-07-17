#include "stdafx.h"
#include "CLOAPIInterface.h"
#include "CloNativePluginSupport.h"
#include "PluginBuildInfo.h"
#include "httplib.h"
#include <atomic>
#include <string>
#include <map>
#include <json.hpp>  // nlohmann json library
#include <fstream>
#include <chrono>
#include <ctime>
#include <mutex>
#include <thread>
#include <filesystem>

using json = nlohmann::json;
using namespace httplib;

// ── Crash-forensic trace log ────────────────────────────────────────────────
// Investigating: CLO crashes hard (process dies) during/after seam creation,
// with no exception surfacing through catch(const std::exception&) or even
// catch(...) — consistent with a genuine SEH/access-violation-class crash
// inside the CLO SDK (same class of bug already documented for ExportAVT in
// this file). A hard crash means g_lastResults (in-memory) and the HTTP
// response are both lost — Python never learns which command was in flight.
//
// This log brackets every CAPI call that has ever been implicated (avatar
// import, pattern import, seam creation) with a BEGIN line written and
// flushed to disk *before* the call, and an END line *after* it returns.
// Opened + flushed + closed on every single call (not held open) specifically
// so a hard crash between BEGIN and END still leaves BEGIN on disk with no
// matching END — that unmatched BEGIN is the crash site. Postmortem: grep the
// file for the last BEGIN with no following END.
static std::mutex g_traceLogMutex;

static std::string TraceLogPath()
{
    // Repo-relative logs dir, matching build_plugin.py's own LOGS_DIR convention.
    return "C:/Users/Anant/mirra-mvp/clo_workspace/logs/plugin_crash_trace.log";
}

static void TraceLog(const std::string& message)
{
    std::lock_guard<std::mutex> lock(g_traceLogMutex);
    try {
        std::filesystem::path p(TraceLogPath());
        std::filesystem::create_directories(p.parent_path());
        std::ofstream f(p, std::ios::app);
        if (!f.is_open()) return;
        auto now = std::chrono::system_clock::now();
        std::time_t t = std::chrono::system_clock::to_time_t(now);
        std::tm tm_buf{};
        localtime_s(&tm_buf, &t);
        char buf[16];
        std::strftime(buf, sizeof(buf), "%H:%M:%S", &tm_buf);
        f << "[" << buf << "] [tid=" << std::this_thread::get_id() << "] " << message << "\n";
        f.flush();
    } catch (...) {
        // Never let logging itself be a new crash source.
    }
}

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

static json StringMapToJson(const std::map<std::string, std::string>& values)
{
    json out = json::object();
    for (const auto& [key, value] : values) {
        out[key] = value;
    }
    return out;
}

static json StringVectorToJson(const std::vector<std::string>& values)
{
    json out = json::array();
    for (const auto& value : values) {
        out.push_back(value);
    }
    return out;
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
std::atomic<bool>            g_queueProcessing{false};
static std::atomic<int>      g_patternsLoaded{0};
static Server*               g_server = nullptr;

// ── Fabric dispatch globals ───────────────────────────────────────────────────
// SetFabricPBRMaterialBaseColor and SetBaseTextureMapImageGivenFilePath cannot
// be called from inside QueueDrainTimer (a Win32 TIMERPROC). They internally
// post Qt/Win32 events that cannot be pumped while the message loop is already
// inside the callback frame — causing a deadlock/hang.
//
// Fix: use PostMessage with custom WM_APP messages so the CAPI calls execute
// at the top of the next Win32 message loop iteration with a clean call stack.

#define WM_MIRRA_SET_COLOR    (WM_APP + 101)
#define WM_MIRRA_SET_TEXTURE  (WM_APP + 102)
#define WM_MIRRA_DRAIN_QUEUE  (WM_APP + 103)

struct FabricColorParams  { int fabric_idx; float r, g, b; };
struct FabricTextureParams { int fabric_idx; std::string path; };

// Atomic counters so /fabric-status can report completion without holding a lock.
struct FabricStatus {
    std::atomic<int>  pending{0};      // incremented before PostMessage
    std::atomic<int>  completed{0};    // incremented after CAPI call returns
    std::atomic<int>  failed{0};       // incremented if CAPI throws
    std::atomic<bool> lastSuccess{true};
    std::mutex        msgMutex;
    std::string       lastMessage;
};
static FabricStatus g_fabricStatus;

static HWND    g_cloMainWnd  = nullptr;  // CLO top-level HWND (discovered once at startup)
static WNDPROC g_origWndProc = nullptr;  // CLO's original WndProc (restored on shutdown)

struct ImportScaleEntry {
    std::string path;
    float scale = 1.0f;
    bool success = false;
};

std::mutex g_importDebugMutex;
float g_lastAvatarImportScale = 1.0f;
std::string g_lastAvatarImportPath;
bool g_lastAvatarImportSuccess = false;
std::vector<ImportScaleEntry> g_lastPatternImports;
std::mutex g_nativeAvatarDebugMutex;
NativeAvatarDebugState g_nativeAvatarDebugState;

struct AvatarPropertyDebugState {
    unsigned int avatar_index = 0;
    bool success = false;
    std::string unit = "raw";
    std::string last_message;
    std::map<std::string, std::string> requested_properties;
    std::map<std::string, std::string> properties_before;
    std::map<std::string, std::string> properties_after;
    std::vector<std::string> changed_keys;
    std::vector<std::string> missing_after_keys;
};

std::mutex g_avatarPropertyDebugMutex;
AvatarPropertyDebugState g_avatarPropertyDebugState;

static json BuildAvatarPropertyDebugJson(const AvatarPropertyDebugState& state)
{
    return {
        {"success", true},
        {"avatar_index", state.avatar_index},
        {"apply_success", state.success},
        {"unit", state.unit},
        {"requested_properties", StringMapToJson(state.requested_properties)},
        {"properties_before", StringMapToJson(state.properties_before)},
        {"properties_after", StringMapToJson(state.properties_after)},
        {"changed_keys", StringVectorToJson(state.changed_keys)},
        {"missing_after_keys", StringVectorToJson(state.missing_after_keys)},
        {"last_message", state.last_message}
    };
}

// Global flag to keep server running
std::atomic<bool> g_serverRunning{false};
std::thread g_serverThread;

// Forward declaration — defined later in this file.
void ProcessCommandQueue();

// ── CLO SDK Guard ─────────────────────────────────────────────────────────────
// Every CAPI call must pass these checks. CLO's SDK pointers can be null during
// scene transitions or on certain CLO versions. Failing loudly here prevents
// silent hangs and makes diagnostics clear in /fabric-status.
namespace CLOGuard {

inline bool fabricReady(std::string& outError) {
    if (!FABRIC_API) { outError = "FABRIC_API is null (CLO SDK not ready)"; return false; }
    return true;
}

inline bool patternIndexValid(int idx, std::string& outError) {
    if (!PATTERN_API) { outError = "PATTERN_API is null"; return false; }
    int count = 0;
    try { count = PATTERN_API->GetPatternCount(); }
    catch (...) { outError = "GetPatternCount threw — CLO may be in scene transition"; return false; }
    if (idx < 0 || idx >= count) {
        outError = "pattern_index " + std::to_string(idx) +
                   " out of range (count=" + std::to_string(count) + ")";
        return false;
    }
    return true;
}

inline bool fileExists(const std::string& path, std::string& outError) {
    DWORD attr = GetFileAttributesA(path.c_str());
    if (attr == INVALID_FILE_ATTRIBUTES) {
        outError = "File not found: " + path; return false;
    }
    return true;
}

} // namespace CLOGuard

// ── MirraWndProc — receives WM_MIRRA_* messages on CLO's main thread ─────────
// Executes the deferred CAPI calls with a clean call stack (outside the timer
// callback frame). Updates g_fabricStatus counters so /fabric-status reflects
// real completion, not just queue drain.
static LRESULT CALLBACK MirraWndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    if (msg == WM_MIRRA_SET_COLOR) {
        auto* p = reinterpret_cast<FabricColorParams*>(lp);
        try {
            FABRIC_API->SetFabricPBRMaterialBaseColor(
                static_cast<unsigned int>(p->fabric_idx), 0u, p->r, p->g, p->b, 1.0f);
            g_fabricStatus.lastSuccess = true;
            { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
              g_fabricStatus.lastMessage = "Color applied to fabric " + std::to_string(p->fabric_idx); }
            g_fabricStatus.completed++;
        } catch (const std::exception& e) {
            g_fabricStatus.failed++;
            g_fabricStatus.lastSuccess = false;
            { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
              g_fabricStatus.lastMessage = std::string("SetFabricPBRMaterialBaseColor threw: ") + e.what(); }
        } catch (...) {
            g_fabricStatus.failed++;
            g_fabricStatus.lastSuccess = false;
        }
        delete p;
        return 0;
    }
    if (msg == WM_MIRRA_SET_TEXTURE) {
        auto* p = reinterpret_cast<FabricTextureParams*>(lp);
        try {
            FABRIC_API->SetBaseTextureMapImageGivenFilePath(p->path, p->fabric_idx);
            g_fabricStatus.lastSuccess = true;
            { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
              g_fabricStatus.lastMessage = "Texture applied to fabric " + std::to_string(p->fabric_idx) + ": " + p->path; }
            g_fabricStatus.completed++;
        } catch (const std::exception& e) {
            g_fabricStatus.failed++;
            g_fabricStatus.lastSuccess = false;
            { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
              g_fabricStatus.lastMessage = std::string("SetBaseTextureMapImageGivenFilePath threw: ") + e.what(); }
        } catch (...) {
            g_fabricStatus.failed++;
            g_fabricStatus.lastSuccess = false;
        }
        delete p;
        return 0;
    }
    if (msg == WM_MIRRA_DRAIN_QUEUE) {
        // Posted by POST /execute so a client can force an immediate drain
        // instead of waiting on QueueDrainTimer. Runs here — on CLO's main
        // thread, clean call stack — for the same reason fabric calls do.
        // ProcessCommandQueue() already no-ops on an empty queue and is
        // guarded by g_queueMutex, so redundant posts are harmless.
        ProcessCommandQueue();
        return 0;
    }
    return CallWindowProc(g_origWndProc, hwnd, msg, wp, lp);
}

// ── WndProc health-check ──────────────────────────────────────────────────────
// CLO may reinstall its own WndProc on scene reload or project open. This check
// runs every 500 ms inside QueueDrainTimer to re-chain from the new proc so our
// WM_MIRRA_* messages are never silently dropped.
static void EnsureWndProcSubclass()
{
    if (!g_cloMainWnd || !g_origWndProc) return;

    // g_cloMainWnd can go stale (CLO destroys/recreates its main window on
    // scene reload). GetWindowLongPtr on a dead handle returns 0, which used
    // to be indistinguishable from "CLO installed a new WndProc" below — that
    // false read overwrote g_origWndProc with nullptr, and every future
    // message on the (still MirraWndProc-subclassed, now-dangling) handle
    // fell through to `CallWindowProc(nullptr, ...)`: an access violation with
    // no catchable C++ exception. Bail out and let startup HWND discovery
    // rediscover the real window instead of corrupting the chain on a guess.
    if (!IsWindow(g_cloMainWnd)) {
        TraceLog("EnsureWndProcSubclass: g_cloMainWnd is no longer a valid window — clearing for rediscovery");
        g_cloMainWnd = nullptr;
        g_origWndProc = nullptr;
        return;
    }

    auto current = reinterpret_cast<WNDPROC>(
        GetWindowLongPtr(g_cloMainWnd, GWLP_WNDPROC));

    // A null read from a *valid* window handle means GetWindowLongPtr failed
    // (see GetLastError) rather than "no WndProc" — never treat that as "CLO
    // replaced the proc," since chaining through a null WNDPROC crashes on
    // the next message. Only re-chain when we got a real, different pointer.
    if (current != nullptr && current != MirraWndProc) {
        // CLO replaced the WndProc — chain from it and re-install ours.
        g_origWndProc = current;
        SetWindowLongPtr(g_cloMainWnd, GWLP_WNDPROC,
                         reinterpret_cast<LONG_PTR>(MirraWndProc));
    }
}

// ── FabricDispatcher ──────────────────────────────────────────────────────────
// Unified interface for ProcessCommandQueue. Increments pending before posting
// so /fabric-status can track in-flight vs. completed calls.
namespace FabricDispatcher {

inline bool available() { return g_cloMainWnd != nullptr; }

inline void dispatchColor(int fabric_idx, float r, float g, float b)
{
    g_fabricStatus.pending++;
    if (!available()) {
        // HWND not found — direct call fallback (may hang if called during timer).
        // This path is only reached if CLO HWND discovery failed at startup.
        try {
            FABRIC_API->SetFabricPBRMaterialBaseColor(
                static_cast<unsigned int>(fabric_idx), 0u, r, g, b, 1.0f);
            g_fabricStatus.completed++;
            g_fabricStatus.lastSuccess = true;
        } catch (...) { g_fabricStatus.failed++; g_fabricStatus.lastSuccess = false; }
        return;
    }
    auto* p = new FabricColorParams{fabric_idx, r, g, b};
    PostMessage(g_cloMainWnd, WM_MIRRA_SET_COLOR, 0, reinterpret_cast<LPARAM>(p));
}

inline void dispatchTexture(int fabric_idx, const std::string& path)
{
    g_fabricStatus.pending++;
    if (!available()) {
        try {
            FABRIC_API->SetBaseTextureMapImageGivenFilePath(path, fabric_idx);
            g_fabricStatus.completed++;
            g_fabricStatus.lastSuccess = true;
        } catch (...) { g_fabricStatus.failed++; g_fabricStatus.lastSuccess = false; }
        return;
    }
    auto* p = new FabricTextureParams{fabric_idx, path};
    PostMessage(g_cloMainWnd, WM_MIRRA_SET_TEXTURE, 0, reinterpret_cast<LPARAM>(p));
}

} // namespace FabricDispatcher

// Windows timer used to drain the command queue on CLO's main thread.
// SetTimer is called once from DoFunction(); the callback fires every 500ms
// via CLO's Win32 message pump — no menu click needed after the first one.
UINT_PTR g_timerId = 0;

VOID CALLBACK QueueDrainTimer(HWND, UINT, UINT_PTR, DWORD)
{
    // Re-check WndProc subclass every tick — handles CLO scene reloads.
    EnsureWndProcSubclass();

    // Heartbeat: proves whether this timer is actually firing at all in a
    // given CLO session (its reliability has been in question — the whole
    // reason /execute needed a real dispatch path instead of just polling
    // status). Throttled to every ~100th tick (~50s at 500ms) so the log
    // stays readable; every tick that finds real work logs unconditionally.
    static std::atomic<long> s_tickCount{0};
    long tick = ++s_tickCount;
    if (tick % 100 == 1) {
        TraceLog("QueueDrainTimer heartbeat tick=" + std::to_string(tick)
            + " serverRunning=" + std::string(g_serverRunning ? "true" : "false")
            + " queueProcessing=" + std::string(g_queueProcessing ? "true" : "false"));
    }

    if (!g_serverRunning) return;
    if (g_queueProcessing) {
        TraceLog("QueueDrainTimer tick=" + std::to_string(tick) + " SKIPPED — g_queueProcessing already true (stuck flag or genuinely mid-batch)");
        return;
    }
    bool hasCommands;
    {
        std::lock_guard<std::mutex> lock(g_queueMutex);
        hasCommands = !g_commandQueue.empty();
    }
    if (hasCommands) {
        TraceLog("QueueDrainTimer tick=" + std::to_string(tick) + " draining queue");
        ProcessCommandQueue();
        TraceLog("QueueDrainTimer tick=" + std::to_string(tick) + " drain call returned");
    }
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
                {"has_avatar_state_readback", false},
                {"has_avatar_avt_export", false},
                {"has_set_fabric_color", true},
                {"has_set_fabric_texture", true},
                {"has_set_fabric_graphic", true},
                {"notes", "Line count may be absent in GetPatternInformation; use line-length probe endpoint"}
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
            try {
                float avatarScale = 1.0f;
                std::string avatarPath;
                bool avatarSuccess = false;

                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    avatarScale = g_lastAvatarImportScale;
                    avatarPath = g_lastAvatarImportPath;
                    avatarSuccess = g_lastAvatarImportSuccess;
                }

                int patternCount = 0;
                try { patternCount = PATTERN_API->GetPatternCount(); } catch (...) {}

                auto slotList = PATTERN_API->GetArrangementList();
                int slotCount = (int)slotList.size();

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
                    anchorMode = "semantic_slots";
                    semanticsQuality = (slotCount >= 4 ? "high" : "medium");
                }
                else if (avatarSuccess && slotCount == 0 && patternArrangementCount > 0) {
                    anchorMode = "generic_arrangement_point";
                    semanticsQuality = "low";
                }
                else if (avatarSuccess) {
                    anchorMode = "imported_mesh_avatar";
                    semanticsQuality = "none";
                }

                json response = {
                    {"success", true},
                    {"avatar_import", {
                        {"path", avatarPath},
                        {"scale", avatarScale},
                        {"success", avatarSuccess}
                    }},
                    {"pattern_count", patternCount},
                    {"arrangement_list_populated", slotCount > 0},
                    {"arrangement_slot_count", slotCount},
                    {"pattern_arrangement_count", patternArrangementCount},
                    {"avatar_anchor_mode", anchorMode},
                    {"arrangement_semantics_quality", semanticsQuality}
                };
                res.set_content(response.dump(), "application/json");
            }
            catch (const std::exception& e) {
                json response = {{"success", false}, {"error", e.what()}};
                res.set_content(response.dump(), "application/json");
            }
        });

        // Native-avatar debug endpoint for the isolated CLO-native experiment.
        svr.Get("/avatar/native-debug", [](const Request&, Response& res) {
            try {
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
                        if (it != row.end()) {
                            slotNames.push_back(it->second);
                            continue;
                        }
                        auto arrangementName = row.find("ArrangementName");
                        if (arrangementName != row.end()) {
                            slotNames.push_back(arrangementName->second);
                            continue;
                        }
                        auto desc = row.find("description");
                        if (desc != row.end()) {
                            slotNames.push_back(desc->second);
                        }
                    }
                } catch (...) {}
                for (int i = 0; i < patternCount; i++) {
                    try {
                        auto rec = PATTERN_API->GetArrangementOfPattern(i);
                        if (!rec.empty()) patternArrangementCount++;
                    } catch (...) {}
                }
                res.set_content(
                    BuildNativeAvatarDebugJson(
                        snapshot,
                        arrangementSlotCount,
                        patternArrangementCount,
                        patternCount,
                        slotNames
                    ).dump(),
                    "application/json"
                );
            }
            catch (const std::exception& e) {
                json response = {{"success", false}, {"error", e.what()}};
                res.set_content(response.dump(), "application/json");
            }
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

        // Avatar state readback endpoint.
        // CLO API calls (GetAvatarCount, GetAvatarNameList, GetAvatarProperties) cannot be
        // made safely from the HTTP thread on Windows — they raise SEH exceptions that
        // catch(...) does not intercept under /EHs, crashing the server thread.
        // This endpoint returns an error until avatar state is cached on the main thread.
        svr.Get("/avatars/state", [](const Request&, Response& res) {
            json response = {
                {"success", false},
                {"error", "avatars/state: CLO API calls not safe from HTTP thread on Windows; pending main-thread caching"}
            };
            res.set_content(response.dump(), "application/json");
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

    // Execute queued commands.
    // NOTE (history): this used to be a no-op — its old comment claimed
    // "DoFunctionContinuously drains the queue automatically on the main
    // thread every frame" and this endpoint "just returns the current queue
    // status without touching the queue itself". That assumption is false
    // for CLO v2025 (DoFunctionContinuously is never called — see its
    // definition below) and QueueDrainTimer (SetTimer-based) does not fire
    // reliably in every session, which silently stalled the whole pipeline
    // until someone clicked the plugin's Plugins-menu entry by hand.
    //
    // Fix: actively request a drain via the same PostMessage/main-thread
    // pattern used for fabric calls, instead of just polling status.
    svr.Post("/execute", [](const Request& req, Response& res) {
        try {
            int qsize;
            bool processing;
            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                qsize = (int)g_commandQueue.size();
                processing = g_queueProcessing;
            }

            std::string dispatchNote = "queue empty";
            if (qsize > 0 && !processing) {
                if (g_cloMainWnd) {
                    PostMessage(g_cloMainWnd, WM_MIRRA_DRAIN_QUEUE, 0, 0);
                    dispatchNote = "drain posted to main thread";
                } else {
                    // g_cloMainWnd was never discovered (should not happen once
                    // DoFunction() has run once) — same last-resort fallback
                    // FabricDispatcher uses; carries the same risk of calling
                    // CAPI off the main thread, but beats never draining at all.
                    TraceLog("/execute: g_cloMainWnd NOT SET — calling ProcessCommandQueue() "
                        "directly on the HTTP server thread (cross-thread CAPI risk)");
                    ProcessCommandQueue();
                    dispatchNote = "drain called directly [no HWND — fallback]";
                }
            } else if (processing) {
                dispatchNote = "drain already in progress";
            }
            TraceLog("/execute called: qsize=" + std::to_string(qsize)
                + " processing=" + std::string(processing ? "true" : "false")
                + " hwndKnown=" + std::string(g_cloMainWnd ? "true" : "false")
                + " -> " + dispatchNote);

            json response = {
                {"success",          true},
                {"queue_size",       qsize},
                {"queue_processing", processing},
                {"message",          dispatchNote}
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

    // Get Pattern Bounding Box / area (SDK-backed geometry signal)
    svr.Get("/patterns/(\\d+)/bbox", [](const Request& req, Response& res) {
        try {
            int patternIndex = std::stoi(req.matches[1]);
            auto raw = PATTERN_API->GetBoundingBoxOfPattern(patternIndex);
            json bbox = json::object();
            for (auto& kv : raw)
                bbox[kv.first] = kv.second;

            json response = {
                {"success", true},
                {"pattern_index", patternIndex},
                {"bbox", bbox},
                {"area", PATTERN_API->GetPatternPieceArea(patternIndex)}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Get Pattern Input Information (raw + parsed when possible)
    svr.Get("/patterns/(\\d+)/input", [](const Request& req, Response& res) {
        try {
            int patternIndex = std::stoi(req.matches[1]);
            std::string inputInfo = PATTERN_API->GetPatternInputInformation(patternIndex);
            json parsed;
            bool parsedOk = false;
            try {
                parsed = json::parse(inputInfo);
                parsedOk = true;
            }
            catch (...) {
                parsed = json::object();
            }

            json response = {
                {"success", true},
                {"pattern_index", patternIndex},
                {"parsed", parsedOk},
                {"input", parsedOk ? parsed : json(inputInfo)}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
    });

    // Probe line lengths by index when line_count is missing from metadata.
    svr.Get("/patterns/(\\d+)/line-lengths", [](const Request& req, Response& res) {
        try {
            int patternIndex = std::stoi(req.matches[1]);
            int maxLines = 256;
            int stopAfterConsecutiveZero = 12;
            if (req.has_param("max")) {
                try { maxLines = std::stoi(req.get_param_value("max")); } catch (...) {}
            }

            json lines = json::array();
            int zeroStreak = 0;
            for (int i = 0; i < maxLines; i++) {
                float len = 0.0f;
                try {
                    len = PATTERN_API->GetLineLength(patternIndex, i);
                }
                catch (...) {
                    len = 0.0f;
                }

                if (len > 0.0001f) {
                    lines.push_back({{"line_index", i}, {"length", len}});
                    zeroStreak = 0;
                }
                else {
                    zeroStreak++;
                    if (!lines.empty() && zeroStreak >= stopAfterConsecutiveZero)
                        break;
                }
            }

            json response = {
                {"success", true},
                {"pattern_index", patternIndex},
                {"line_count", (int)lines.size()},
                {"lines", lines}
            };
            res.set_content(response.dump(), "application/json");
        }
        catch (const std::exception& e) {
            json response = {{"success", false}, {"error", e.what()}};
            res.set_content(response.dump(), "application/json");
        }
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

    // ── Set fabric diffuse color ─────────────────────────────────────────────
    // Expects: {pattern_index, r, g, b}  (r/g/b in 0–255)
    svr.Post("/set-fabric-color", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type        = "set-fabric-color";
            cmd.param3      = j["pattern_index"].get<int>();
            cmd.floatParam1 = (float)j["r"].get<int>();
            cmd.floatParam2 = (float)j["g"].get<int>();
            cmd.floatParam3 = (float)j["b"].get<int>();

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",       true},
                {"message",       "Fabric color queued"},
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

    // ── Set fabric diffuse texture ───────────────────────────────────────────
    // Expects: {pattern_index, texture_path}
    svr.Post("/set-fabric-texture", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type   = "set-fabric-texture";
            cmd.param3 = j["pattern_index"].get<int>();
            cmd.param1 = j["texture_path"].get<std::string>();

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",       true},
                {"message",       "Fabric texture queued"},
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

    // ── Set fabric graphic overlay ───────────────────────────────────────────
    // Expects: {pattern_index, graphic_path, u?, v?, scale?}
    svr.Post("/set-fabric-graphic", [](const Request& req, Response& res) {
        try {
            auto j = json::parse(req.body);

            APICommand cmd;
            cmd.type        = "set-fabric-graphic";
            cmd.param3      = j["pattern_index"].get<int>();
            cmd.param1      = j["graphic_path"].get<std::string>();
            cmd.floatParam4 = (float)j.value("u",     0.5);
            cmd.floatParam5 = (float)j.value("v",     0.3);
            cmd.floatParam6 = (float)j.value("scale", 1.0);

            {
                std::lock_guard<std::mutex> lock(g_queueMutex);
                g_commandQueue.push(cmd);
            }

            json response = {
                {"success",       true},
                {"message",       "Fabric graphic queued"},
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

    // ── Fabric dispatch status endpoints ────────────────────────────────────────
    // GET /fabric-status — returns pending/completed/failed counters so
    // Python can poll for async fabric call completion after PostMessage.
    svr.Get("/fabric-status", [](const Request&, Response& res) {
        std::string lastMsg;
        { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
          lastMsg = g_fabricStatus.lastMessage; }
        bool allDone = (g_fabricStatus.completed.load() + g_fabricStatus.failed.load())
                       >= g_fabricStatus.pending.load();
        json response = {
            {"success",      true},
            {"pending",      g_fabricStatus.pending.load()},
            {"completed",    g_fabricStatus.completed.load()},
            {"failed",       g_fabricStatus.failed.load()},
            {"all_done",     allDone},
            {"last_success", g_fabricStatus.lastSuccess.load()},
            {"last_message", lastMsg},
            {"dispatcher",   FabricDispatcher::available() ? "PostMessage" : "direct"}
        };
        res.set_content(response.dump(), "application/json");
    });

    // POST /fabric-status/reset — clears counters before a new fabric batch.
    // Call this from Python before issuing a set of color/texture commands.
    svr.Post("/fabric-status/reset", [](const Request&, Response& res) {
        g_fabricStatus.pending   = 0;
        g_fabricStatus.completed = 0;
        g_fabricStatus.failed    = 0;
        g_fabricStatus.lastSuccess = true;
        { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
          g_fabricStatus.lastMessage.clear(); }
        res.set_content(
            json{{"success", true}, {"message", "fabric status reset"}}.dump(),
            "application/json"
        );
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

    // ── Arrangement debug payload: raw slots + per-pattern arrangement in one call.
    svr.Get("/arrangement/debug", [](const Request&, Response& res) {
        try {
            json slots = json::array();
            auto list = PATTERN_API->GetArrangementList();
            for (int i = 0; i < (int)list.size(); i++) {
                json entry = {{"index", i}};
                for (auto& kv : list[i])
                    entry[kv.first] = kv.second;
                slots.push_back(entry);
            }

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

            json response = {
                {"success", true},
                {"slot_count", (int)slots.size()},
                {"slots", slots},
                {"pattern_arrangement_count", (int)patterns.size()},
                {"patterns", patterns}
            };
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
        bool success = svr.listen("127.0.0.1", 50600);
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
    // Restore original WndProc before shutting down so CLO's own message
    // handling is fully intact after the plugin is unloaded.
    if (g_origWndProc && g_cloMainWnd) {
        SetWindowLongPtr(g_cloMainWnd, GWLP_WNDPROC,
                         reinterpret_cast<LONG_PTR>(g_origWndProc));
        g_origWndProc = nullptr;
    }
    g_serverRunning = false;
    if (g_timerId != 0) { KillTimer(NULL, g_timerId); g_timerId = 0; }
    if (g_server != nullptr) { g_server->stop(); }
}

// ─────────────────────────────────────────────────────────────────────────────
// ProcessCommandQueue — MUST be called from CLO's main thread.
// Called automatically every frame by DoFunctionContinuously().
// Also called manually when the user clicks Plugins → REST Server & Execute.
// ─────────────────────────────────────────────────────────────────────────────
// The reentrancy guard below (ReentrancyResetGuard) is RAII so g_queueProcessing
// always resets to false when ProcessCommandQueue returns — including via an
// exception that escapes the per-command try/catch below (e.g. a non-std::exception
// type thrown by a CLO SDK call). Before this was RAII, a single bad command could
// permanently stick the flag at true, silently disabling QueueDrainTimer AND the
// /execute-triggered drain for the rest of the CLO session; a manual menu click
// still worked as a last resort because DoFunction() called ProcessCommandQueue()
// unconditionally, ignoring the flag. That bypass is no longer required for
// recovery now that the flag always resets — see the reentrancy-guard comment
// inside the function for why DoFunction's call site still goes through it.
void ProcessCommandQueue()
{
    // Reentrancy guard (parity with macOS, which already has this via
    // g_queueProcessing.exchange(true)). Windows previously had none here —
    // only QueueDrainTimer checked the flag before *calling* this function;
    // ProcessCommandQueue() itself would run again if re-entered from another
    // call site while already mid-batch. That's reachable now that
    // WM_MIRRA_DRAIN_QUEUE (posted from POST /execute) calls this directly:
    // if a CLO SDK call inside the batch below pumps the Win32 message loop
    // internally (the same reentrancy class that forced fabric calls off the
    // timer callback onto PostMessage in the first place), a pending
    // WM_MIRRA_DRAIN_QUEUE could dispatch and re-enter this function on the
    // same thread mid-batch. Without this guard, the inner call's RAII reset
    // would flip g_queueProcessing back to false while the outer call is
    // still executing — letting the timer schedule a second overlapping
    // drain that interleaves with in-flight CLO SDK state. A plausible
    // contributor to both the seam-creation crash and corrupted seam
    // ordering ("avatar distortion"). The DoFunction() manual-menu-click path
    // used to bypass g_queueProcessing entirely as a way to unstick a
    // permanently-true flag from a pre-RAII bug; that recovery is no longer
    // needed now that this guard always resets the flag on exit (see
    // ReentrancyResetGuard below), so honoring the guard here does not
    // reintroduce the stuck-flag problem.
    if (g_queueProcessing.exchange(true)) return;
    struct ReentrancyResetGuard {
        ~ReentrancyResetGuard() { g_queueProcessing = false; }
    } reentrancyGuard;

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
                // Avatar scale is provided by pipeline based on export metadata units.
                options.scale           = (cmd.floatParam1 > 0.0f ? cmd.floatParam1 : 1.0f);
                options.ImportObjectType = 0;   // Avatar
                options.bAutoTranslate  = true; // moves feet to Y=0 (ground)
                result.success  = IMPORT_API->ImportOBJ(cmd.param1, options);
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastAvatarImportScale = options.scale;
                    g_lastAvatarImportPath = cmd.param1;
                    g_lastAvatarImportSuccess = result.success;
                }
                result.message  = result.success
                    ? "Imported avatar: " + cmd.param1 + " (scale=" + std::to_string(options.scale) + ")"
                    : "Failed to import avatar: " + cmd.param1;
            }
            // ── Pattern import ────────────────────────────────────────────
            else if (cmd.type == "import-avatar-avt") {
                Marvelous::ImportExportOption options;
                options.scale = 1.0f;
                TraceLog("BEGIN import-avatar-avt path=" + cmd.param1 + " scale=" + std::to_string(options.scale));
                result.success = IMPORT_API->ImportAvatar(cmd.param1, options);
                TraceLog("END   import-avatar-avt success=" + std::string(result.success ? "true" : "false"));
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState.last_native_avatar_path = cmd.param1;
                    g_nativeAvatarDebugState.last_native_avatar_success = result.success;
                    g_nativeAvatarDebugState.last_message = result.success
                        ? "Imported native avatar template"
                        : "Failed to import native avatar template";
                }
                result.message = result.success
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
                result.success = measurementOk;
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState.last_measurement_csv_path = cmd.param1;
                    g_nativeAvatarDebugState.last_measurement_template_path = cmd.param2;
                    g_nativeAvatarDebugState.last_measurement_csv_success = result.success;
                    g_nativeAvatarDebugState.last_message = result.success
                        ? "Imported native avatar measurement CSV"
                        : "Failed to import native avatar measurement CSV";
                }
                result.message = result.success
                    ? "Imported native avatar measurements: " + cmd.param1
                    : "Failed to import native avatar measurements: " + cmd.param1;
            }
            else if (cmd.type == "avatar-set-properties") {
                AvatarPropertyDebugState debugState;
                debugState.avatar_index = (cmd.param3 >= 0 ? static_cast<unsigned int>(cmd.param3) : 0);
                debugState.unit = (cmd.param2.empty() ? "raw" : cmd.param2);
                debugState.requested_properties = cmd.stringMapParam1;

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
                    result.success = true;
                    result.message =
                        "Avatar properties applied to avatar " + std::to_string(debugState.avatar_index) +
                        " (requested=" + std::to_string(debugState.requested_properties.size()) +
                        ", changed=" + std::to_string(debugState.changed_keys.size()) +
                        ", missing_after=" + std::to_string(debugState.missing_after_keys.size()) + ")";
                    debugState.success = true;
                    debugState.last_message = result.message;
                }
                catch (const std::exception& e) {
                    result.success = false;
                    result.message = "Failed to set avatar properties: " + std::string(e.what());
                    debugState.success = false;
                    debugState.last_message = result.message;
                }
                catch (...) {
                    result.success = false;
                    result.message = "Failed to set avatar properties: unknown exception";
                    debugState.success = false;
                    debugState.last_message = result.message;
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
                TraceLog("BEGIN import-pattern path=" + cmd.param1 + " scale=" + std::to_string(options.m_Scale));
                result.success = IMPORT_API->ImportDXF(cmd.param1, options);
                TraceLog("END   import-pattern success=" + std::string(result.success ? "true" : "false")
                    + " patternsLoaded=" + std::to_string(g_patternsLoaded.load()));
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastPatternImports.push_back({cmd.param1, options.m_Scale, result.success});
                    if (g_lastPatternImports.size() > 64)
                        g_lastPatternImports.erase(g_lastPatternImports.begin(), g_lastPatternImports.begin() + 32);
                }
                result.message = result.success
                    ? "Imported pattern: " + cmd.param1 + " (scale=" + std::to_string(options.m_Scale) + ")"
                    : "Failed to import pattern: " + cmd.param1;
                if (result.success)
                    g_patternsLoaded++;
            }
            // ── Create seam ───────────────────────────────────────────────
            else if (cmd.type == "create-seam") {
                // Investigating a hard CLO crash that happens during/after the
                // 10-seam batch this pipeline sends. Two of those ten are
                // self-seams (pattern_a == pattern_b, e.g. sleeve-L-tube joins
                // edge 1 to edge 4 of the SAME sleeve piece to roll it into a
                // tube) — architecturally different from the other eight,
                // which join two distinct pieces. Flagging that explicitly
                // here since it's the leading hypothesis for what
                // AddSeamlinePairGroup might not handle safely.
                bool isSelfSeam = (cmd.param3 == cmd.param5);
                int patternCountNow = -1;
                try { patternCountNow = PATTERN_API->GetPatternCount(); } catch (...) {}
                TraceLog(
                    "BEGIN create-seam pattern_a=" + std::to_string(cmd.param3) +
                    " edge_a=" + std::to_string(cmd.param4) +
                    " pattern_b=" + std::to_string(cmd.param5) +
                    " edge_b=" + std::to_string(cmd.param6) +
                    " dirA=" + std::to_string(cmd.boolParam1) +
                    " dirB=" + std::to_string(cmd.boolParam2) +
                    " selfSeam=" + std::string(isSelfSeam ? "true" : "false") +
                    " livePatternCount=" + std::to_string(patternCountNow)
                );
                result.success = PATTERN_API->AddSeamlinePairGroup(
                    cmd.param3, cmd.param4,
                    cmd.param5, cmd.param6,
                    cmd.boolParam1, cmd.boolParam2
                );
                TraceLog("END   create-seam success=" + std::string(result.success ? "true" : "false"));
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
                g_patternsLoaded = 0;
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastPatternImports.clear();
                    g_lastAvatarImportPath.clear();
                    g_lastAvatarImportScale = 1.0f;
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
                result.success = true;
                result.message = "New project created";
            }
            // ── Arrange pattern in 3D space ───────────────────────────────
            // SetArrangement assigns the pattern to a named avatar slot (front/back/sleeve).
            // SetArrangementPosition then fine-tunes with mm offsets from that slot centre.
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
                result.success = true;
                result.message = "Pattern " + std::to_string(cmd.param3) +
                    (cmd.param4 >= 0 ? " -> arrangement slot " + std::to_string(cmd.param4) : " position set") +
                    " pos=(" + std::to_string((int)cmd.floatParam1) +
                    "," + std::to_string((int)cmd.floatParam2) +
                    "," + std::to_string((int)cmd.floatParam3) + ")mm";
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
            // ── Set fabric diffuse color ──────────────────────────────────────
            // floatParam1/2/3 = R/G/B (0–255); param3 = pattern_index
            // Uses CLOGuard to validate SDK state + pattern index before
            // dispatching via FabricDispatcher (PostMessage, non-blocking).
            else if (cmd.type == "set-fabric-color") {
                std::string guardErr;
                if (!CLOGuard::fabricReady(guardErr) ||
                    !CLOGuard::patternIndexValid(cmd.param3, guardErr)) {
                    result.success = false;
                    result.message = "[Guard] " + guardErr;
                } else {
                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
                    if (fabric_idx < 0) fabric_idx = 0;
                    float r = std::clamp(cmd.floatParam1, 0.0f, 255.0f) / 255.0f;
                    float g = std::clamp(cmd.floatParam2, 0.0f, 255.0f) / 255.0f;
                    float b = std::clamp(cmd.floatParam3, 0.0f, 255.0f) / 255.0f;
                    FabricDispatcher::dispatchColor(fabric_idx, r, g, b);
                    result.success = true;
                    result.message = "Color RGB(" +
                        std::to_string((int)cmd.floatParam1) + "," +
                        std::to_string((int)cmd.floatParam2) + "," +
                        std::to_string((int)cmd.floatParam3) +
                        ") dispatched to fabric " + std::to_string(fabric_idx) +
                        (FabricDispatcher::available() ? " [PostMessage]" : " [direct]");
                }
            }
            // ── Set fabric base texture ───────────────────────────────────────
            // param1 = texture file path (PNG/JPEG); param3 = pattern_index
            else if (cmd.type == "set-fabric-texture") {
                std::string guardErr;
                if (!CLOGuard::fabricReady(guardErr)       ||
                    !CLOGuard::patternIndexValid(cmd.param3, guardErr) ||
                    !CLOGuard::fileExists(cmd.param1, guardErr)) {
                    result.success = false;
                    result.message = "[Guard] " + guardErr;
                } else {
                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
                    if (fabric_idx < 0) fabric_idx = 0;
                    FabricDispatcher::dispatchTexture(fabric_idx, cmd.param1);
                    result.success = true;
                    result.message = "Texture dispatched to fabric " +
                        std::to_string(fabric_idx) + ": " + cmd.param1 +
                        (FabricDispatcher::available() ? " [PostMessage]" : " [direct]");
                }
            }
            // ── Set fabric graphic overlay ────────────────────────────────────
            // param1 = graphic file path; param3 = pattern_index.
            // Dispatched identically to set-fabric-texture (base texture replacement).
            else if (cmd.type == "set-fabric-graphic") {
                std::string guardErr;
                if (!CLOGuard::fabricReady(guardErr)       ||
                    !CLOGuard::patternIndexValid(cmd.param3, guardErr) ||
                    !CLOGuard::fileExists(cmd.param1, guardErr)) {
                    result.success = false;
                    result.message = "[Guard] " + guardErr;
                } else {
                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
                    if (fabric_idx < 0) fabric_idx = 0;
                    FabricDispatcher::dispatchTexture(fabric_idx, cmd.param1);
                    result.success = true;
                    result.message = "Graphic dispatched to fabric " +
                        std::to_string(fabric_idx) + ": " + cmd.param1 +
                        (FabricDispatcher::available() ? " [PostMessage]" : " [direct]");
                }
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
            else if (cmd.type == "export-avatar-avt") {
                // ExportAVT raises SEH exceptions that are not caught by catch(std::exception&)
                // under /EHs, crashing CLO's main thread. Disabled until SEH handling is added.
                result.success = false;
                result.message = "export-avatar-avt: ExportAVT crashes CLO main thread via SEH; use zprj extraction instead";
            }
            else {
                result.message = "Unknown command type: " + cmd.type;
            }
        }
        catch (const std::exception& e) {
            result.success = false;
            result.message = "Exception in '" + cmd.type + "': " + std::string(e.what());
        }
        catch (...) {
            // Non-std::exception throw (e.g. a CLO SDK internal type). Record it
            // and keep draining the rest of the batch instead of letting it
            // escape the loop — ReentrancyResetGuard would still reset the flag
            // either way, but catching here keeps subsequent queued commands
            // from being silently dropped along with the crashing one.
            result.success = false;
            result.message = "Exception in '" + cmd.type + "': non-standard exception (unknown type)";
        }

        {
            std::lock_guard<std::mutex> rlock(g_resultsMutex);
            g_lastResults.push_back(result);
        }
    }

    // processingGuard's destructor resets g_queueProcessing = false here,
    // whether we reach this point normally or via an exception unwinding
    // out of the loop above.
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
            UTILITY_API->DisplayMessageBox("Starting REST server on http://localhost:50600\n\nQueue drains automatically every 500 ms — no further menu clicks needed.");

            g_serverRunning = true;
            g_serverThread = std::thread(StartRESTServer);
            g_serverThread.detach();

            // Register a 500ms Windows timer so the queue is drained on the
            // main thread automatically (CLO v2025 has no DoFunctionContinuously).
            if (g_timerId == 0) {
                g_timerId = SetTimer(NULL, 0, 500, QueueDrainTimer);
            }

            // Discover CLO's top-level HWND and subclass it so WM_MIRRA_* messages
            // are delivered safely outside the timer callback frame.
            // Done once at startup; EnsureWndProcSubclass() re-installs on scene reload.
            if (g_cloMainWnd == nullptr) {
                EnumWindows([](HWND hwnd, LPARAM) -> BOOL {
                    DWORD pid = 0;
                    GetWindowThreadProcessId(hwnd, &pid);
                    if (pid == GetCurrentProcessId() && IsWindowVisible(hwnd)) {
                        g_cloMainWnd = hwnd;
                        return FALSE;
                    }
                    return TRUE;
                }, 0);
                if (g_cloMainWnd) {
                    // Sanity-log which window we actually picked — EnumWindows
                    // takes the FIRST visible top-level window of this process,
                    // which is not guaranteed to be CLO's real main frame (could
                    // be a splash/tool window depending on startup timing). If
                    // WM_MIRRA_* messages ever silently vanish, check this line
                    // first — subclassing the wrong HWND would explain it.
                    char title[256] = {0};
                    char cls[256] = {0};
                    GetWindowTextA(g_cloMainWnd, title, sizeof(title));
                    GetClassNameA(g_cloMainWnd, cls, sizeof(cls));
                    TraceLog(std::string("DoFunction: g_cloMainWnd discovered hwnd=")
                        + std::to_string(reinterpret_cast<uintptr_t>(g_cloMainWnd))
                        + " title='" + title + "' class='" + cls + "'");
                }
                if (g_cloMainWnd && g_origWndProc == nullptr) {
                    g_origWndProc = reinterpret_cast<WNDPROC>(
                        SetWindowLongPtr(g_cloMainWnd, GWLP_WNDPROC,
                                         reinterpret_cast<LONG_PTR>(MirraWndProc)));
                }
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
            TraceLog("DoFunction: manual menu click, queue_size=" + std::to_string(queue_size) + " — calling ProcessCommandQueue() directly (now honors the reentrancy guard; no-ops if a batch is already in flight)");
            ProcessCommandQueue();
            TraceLog("DoFunction: ProcessCommandQueue() returned normally (no crash)");
        }
        else {
            UTILITY_API->DisplayMessageBox("REST server is running on http://localhost:50600\n\nNo commands in queue.\n\nQueue commands via REST API, then click this menu item again to execute them.");
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
// Queue draining is handled by QueueDrainTimer (SetTimer, 500ms).
CLO_PLUGIN_SPECIFIER void DoFunctionContinuously() { }
