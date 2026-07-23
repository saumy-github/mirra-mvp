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
    bool ImportAvatar(const std::string&, const Marvelous::ImportExportOption&) { return false; }
    bool ImportAvatarMeasurement(const std::string&, const std::string&, const Marvelous::ImportExportOption&) { return false; }
    bool ImportMeasurement(const std::string&) { return false; }
};
extern ImportAPI* IMPORT_API;

struct ExportAPI {
    std::string ExportGLTF(const std::string&, const Marvelous::ImportExportOption&, bool) { return std::string(); }
    std::string ExportZPrj(const std::string&, bool) { return std::string(); }
    std::string ExportAVT(const std::string&) { return std::string(); }
    unsigned int GetAvatarCount() { return 0; }
    std::vector<std::string> GetAvatarNameList() { return {}; }
    std::vector<int> GetAvatarGenderList() { return {}; }
};
extern ExportAPI* EXPORT_API;

struct UtilityAPI {
    void NewProject() {}
    bool Simulate(unsigned int) { return false; }
    std::map<std::string, std::string> GetAvatarProperties(unsigned int) { return {}; }
    void SetAvatarProperties(unsigned int, const std::map<std::string, std::string>&) {}
};
extern UtilityAPI* UTILITY_API;

struct FabricAPI {
    int  GetFabricIndexForPattern(int) { return 0; }
    bool SetFabricPBRMaterialBaseColor(unsigned int, unsigned int, float, float, float, float) { return false; }
    void SetBaseTextureMapImageGivenFilePath(const std::string&, int) {}
};
extern FabricAPI* FABRIC_API;

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
    std::map<std::string, float> GetBoundingBoxOfPattern(int) { return {}; }
    float GetPatternPieceArea(int) { return 0.0f; }
    std::string GetPatternInputInformation(int) { return std::string("{}"); }
    float GetLineLength(int, int) { return 0.0f; }
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
#include "CloNativePluginSupport.h"
#include "PluginBuildInfo.h"

// Standard library
#include <algorithm>
#include <atomic>
#include <chrono>
#include <future>
#include <map>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

// Phase 3 crash protection: POSIX signal handling for SIGSEGV/SIGBUS/SIGILL.
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <unistd.h>

using json = nlohmann::json;
using namespace httplib;

#if defined(__GNUC__) || defined(__clang__)
#  define CLO_EXPORT      extern "C" __attribute__((visibility("default")))
#  define DYLIB_DESTRUCTOR __attribute__((destructor))
#else
// Windows IntelliSense / MSVC: strip Clang/GCC-only attributes so the editor
// can parse this file without false-positive errors. The actual build always
// uses Clang on macOS where both attributes are supported.
#  define CLO_EXPORT      extern "C"
#  define DYLIB_DESTRUCTOR
#endif

static const char* AvatarGenderLabel(int gender)
{
    switch (gender) {
    case 0: return "male";
    case 1: return "female";
    default: return "unknown";
    }
}

// ─── Crash protection (Phase 3) ────────────────────────────────────────────
// macOS has no equivalent to Windows SEH (__try/__except) that lets a caught
// hardware fault resume execution safely — after SIGSEGV/SIGBUS/SIGILL, the
// heap/global state may already be corrupted, so "catch and continue" via
// sigsetjmp/siglongjmp is not attempted here (this is not just a scoping
// choice: it is widely considered unsafe in production, which is part of why
// browsers isolate crash-prone work in separate sandboxed processes instead
// of recovering in-process). This handler only writes a small diagnostic
// breadcrumb next to macOS's own automatic crash report, then restores the
// default handler and re-raises so the OS's normal crash path (.ips report +
// process termination) still happens exactly as it would without this file.
//
// The handler body only calls write()/open()/close()/snprintf() into a stack
// buffer — no malloc, no std::string, no iostream — to stay as close to
// async-signal-safe as practical C++ allows.
static void MirraCrashSignalHandler(int signalNumber)
{
    const char* label = "UNKNOWN";
    if (signalNumber == SIGSEGV) label = "SIGSEGV";
    else if (signalNumber == SIGBUS) label = "SIGBUS";
    else if (signalNumber == SIGILL) label = "SIGILL";

    char path[512];
    const char* home = getenv("HOME");
    if (home) {
        snprintf(path, sizeof(path), "%s/Library/Logs/DiagnosticReports/MirraRestPlugin_crash.log", home);
    } else {
        snprintf(path, sizeof(path), "/tmp/MirraRestPlugin_crash.log");
    }

    int fd = open(path, O_CREAT | O_WRONLY | O_APPEND, 0644);
    if (fd >= 0) {
        char line[256];
        int len = snprintf(line, sizeof(line),
            "[MirraRestPlugin] signal=%s (%d) pid=%d — see the accompanying macOS crash report in this directory\n",
            label, signalNumber, (int)getpid());
        if (len > 0) write(fd, line, (size_t)len);
        close(fd);
    }

    signal(signalNumber, SIG_DFL);
    raise(signalNumber);
}

static void InstallCrashSignalHandlers()
{
    signal(SIGSEGV, MirraCrashSignalHandler);
    signal(SIGBUS,  MirraCrashSignalHandler);
    signal(SIGILL,  MirraCrashSignalHandler);
}

// ─── Dynamic capability flags (Phase 3) ────────────────────────────────────
// Mirrors the Windows probe pattern: exercise each historically crash-prone
// CLO API once at startup and set the corresponding capability flag from the
// real result instead of a hardcoded value. Unlike Windows there is no
// per-call recovery wrapper around these calls (see above) — a genuine
// SIGSEGV/SIGBUS/SIGILL during the probe is still fatal to the CLO process,
// just now with a breadcrumb logged first.
static std::atomic<bool> g_capabilityAvatarAvtExport{false};
static std::atomic<bool> g_capabilityAvatarStateReadback{false};
static std::atomic<bool> g_capabilityProbesRun{false};

static void RunCapabilityProbesOnce()
{
    if (g_capabilityProbesRun.exchange(true)) return;

    try {
        g_capabilityAvatarAvtExport =
            !EXPORT_API->ExportAVT("/tmp/mirra_rest_plugin_probe_export.avt").empty();
    } catch (...) {
        g_capabilityAvatarAvtExport = false;
    }

    try {
        (void)EXPORT_API->GetAvatarCount();
        (void)EXPORT_API->GetAvatarNameList();
        (void)EXPORT_API->GetAvatarGenderList();
        g_capabilityAvatarStateReadback = true;
    } catch (...) {
        g_capabilityAvatarStateReadback = false;
    }
}

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
    float floatParam1 = 0.f;   // position.x | scale
    float floatParam2 = 0.f;   // position.y
    float floatParam3 = 0.f;   // position.offset  (sent by client as "offset", not "z")
    float floatParam4 = 0.f;
    float floatParam5 = 0.f;
    float floatParam6 = 0.f;
    std::map<std::string, std::string> stringMapParam1; // avatar properties

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

struct ImportScaleEntry {
    std::string path;
    float scale = 1.0f;
    bool success = false;
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

static std::mutex g_importDebugMutex;
static float g_lastAvatarImportScale = 1.0f;
static std::string g_lastAvatarImportPath;
static bool g_lastAvatarImportSuccess = false;
static std::vector<ImportScaleEntry> g_lastPatternImports;
static std::mutex g_nativeAvatarDebugMutex;
static NativeAvatarDebugState g_nativeAvatarDebugState;

// Raw pointer to Qt timer – created and owned on the main thread.
// Stopped and deleted in the dylib destructor (also main thread on macOS).
static QTimer* g_drainTimer = nullptr;

// Raw pointer to the httplib server so the destructor can call stop().
static Server* g_server = nullptr;

// ── Fabric dispatch globals ───────────────────────────────────────────────────
// SetFabricPBRMaterialBaseColor and SetBaseTextureMapImageGivenFilePath cannot
// be called directly from inside a Qt timer slot. They internally post Qt events
// that cannot be delivered while the event loop is executing the slot — deadlock.
//
// Fix: QMetaObject::invokeMethod with Qt::QueuedConnection posts the call to the
// Qt event queue. It executes at the top of the next event loop iteration, after
// the current timer slot has returned and the call stack is clean.
struct FabricStatus {
    std::atomic<int>  pending{0};
    std::atomic<int>  completed{0};
    std::atomic<int>  failed{0};
    std::atomic<bool> lastSuccess{true};
    std::mutex        msgMutex;
    std::string       lastMessage;
};
static FabricStatus g_fabricStatus;


// ─── Avatar property helpers (pure C++, no platform dependency) ──────────────

static std::string JsonPrimitiveToString(const json& value)
{
    if (value.is_string()) return value.get<std::string>();
    if (value.is_boolean() || value.is_number() || value.is_null()) return value.dump();
    throw std::runtime_error("Avatar property values must be JSON primitives");
}

static std::map<std::string, std::string> JsonObjectToStringMap(const json& obj)
{
    if (!obj.is_object()) throw std::runtime_error("properties must be a JSON object");
    std::map<std::string, std::string> result;
    for (auto it = obj.begin(); it != obj.end(); ++it)
        result[it.key()] = JsonPrimitiveToString(it.value());
    return result;
}

static std::vector<std::string> ComputeChangedPropertyKeys(
    const std::map<std::string, std::string>& before,
    const std::map<std::string, std::string>& after,
    const std::map<std::string, std::string>& requested)
{
    std::vector<std::string> changed;
    for (const auto& [key, _] : requested) {
        auto beforeIt = before.find(key);
        auto afterIt  = after.find(key);
        if (afterIt == after.end()) continue;
        if (beforeIt == before.end() || beforeIt->second != afterIt->second)
            changed.push_back(key);
    }
    return changed;
}

static std::vector<std::string> ComputeMissingAfterKeys(
    const std::map<std::string, std::string>& after,
    const std::map<std::string, std::string>& requested)
{
    std::vector<std::string> missing;
    for (const auto& [key, _] : requested)
        if (after.find(key) == after.end()) missing.push_back(key);
    return missing;
}

// ─── Avatar property debug state ─────────────────────────────────────────────
// AvatarPropertyDebugState and BuildAvatarPropertyDebugJson now live in
// CloNativePluginSupport.h, shared with the Windows plugin.

static std::mutex g_avatarPropertyDebugMutex;
static AvatarPropertyDebugState g_avatarPropertyDebugState;

// ─── Forward declaration ──────────────────────────────────────────────────────
static void ProcessCommandQueue();

// ── CLO SDK Guard ─────────────────────────────────────────────────────────────
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
#if __has_include(<unistd.h>)
    if (::access(path.c_str(), F_OK) != 0) {
        outError = "File not found: " + path; return false;
    }
#else
    FILE* f = ::fopen(path.c_str(), "rb");
    if (!f) { outError = "File not found: " + path; return false; }
    ::fclose(f);
#endif
    return true;
}

} // namespace CLOGuard

// ── FabricDispatcher (macOS) ────────────────────────────────────────────────────
// Uses QMetaObject::invokeMethod(Qt::QueuedConnection) to run the CAPI call at
// the top of the next Qt event loop iteration — outside the timer slot frame.
// Lambdas capture by value; no heap allocation needed (Qt ref-counts internally).
namespace FabricDispatcher {

inline void dispatchColor(int fabric_idx, float r, float g, float b)
{
    g_fabricStatus.pending++;
    QMetaObject::invokeMethod(
        QCoreApplication::instance(),
        [fabric_idx, r, g, b]() {
            try {
                FABRIC_API->SetFabricPBRMaterialBaseColor(
                    static_cast<unsigned int>(fabric_idx), 0u, r, g, b, 1.0f);
                g_fabricStatus.lastSuccess = true;
                { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
                  g_fabricStatus.lastMessage = "Color applied to fabric " + std::to_string(fabric_idx); }
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
        },
        Qt::QueuedConnection
    );
}

inline void dispatchTexture(int fabric_idx, const std::string& path)
{
    g_fabricStatus.pending++;
    QString qpath = QString::fromStdString(path);
    QMetaObject::invokeMethod(
        QCoreApplication::instance(),
        [fabric_idx, qpath]() {
            try {
                FABRIC_API->SetBaseTextureMapImageGivenFilePath(
                    qpath.toStdString(), fabric_idx);
                g_fabricStatus.lastSuccess = true;
                { std::lock_guard<std::mutex> lk(g_fabricStatus.msgMutex);
                  g_fabricStatus.lastMessage = "Texture applied to fabric " + std::to_string(fabric_idx); }
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
        },
        Qt::QueuedConnection
    );
}

} // namespace FabricDispatcher


static json BuildArrangementDebugPayload()
{
    json slot_list = json::array();
    auto list = PATTERN_API->GetArrangementList();
    for (int i = 0; i < static_cast<int>(list.size()); i++) {
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
        {"slot_count", static_cast<int>(slot_list.size())},
        {"slots", slot_list},
        {"pattern_arrangement_count", static_cast<int>(patterns.size())},
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

    // RAII reset: guarantees g_queueProcessing goes back to false on every exit
    // path below (early return, normal completion, or an exception unwinding
    // out of the per-command loop) — including a non-std::exception type that
    // the per-command catch doesn't cover. Without this, one bad command could
    // permanently strand the flag at true, silently disabling all future
    // automatic drains for the rest of the CLO session.
    struct ProcessingResetGuard { ~ProcessingResetGuard() { g_queueProcessing = false; } } resetGuard;

    // Drain the queue under the mutex; release before calling any CLO API.
    std::vector<APICommand> batch;
    {
        std::lock_guard<std::mutex> lk(g_queueMutex);
        if (g_commandQueue.empty()) {
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
                opts.scale            = (cmd.floatParam1 > 0.0f ? cmd.floatParam1 : 1.0f);
                opts.ImportObjectType = 0;
                opts.bAutoTranslate   = true;
                asyncResult.success = IMPORT_API->ImportOBJ(cmd.param1, opts);
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastAvatarImportScale = opts.scale;
                    g_lastAvatarImportPath = cmd.param1;
                    g_lastAvatarImportSuccess = asyncResult.success;
                }
                asyncResult.message = asyncResult.success
                    ? "Imported avatar: " + cmd.param1 + " (scale=" + std::to_string(opts.scale) + ")"
                    : "Failed to import avatar: " + cmd.param1;
            }
            else if (cmd.type == "import-avatar-avt") {
                Marvelous::ImportExportOption opts;
                opts.scale = 1.0f;
                asyncResult.success = IMPORT_API->ImportAvatar(cmd.param1, opts);
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState.last_native_avatar_path = cmd.param1;
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
                    Marvelous::ImportExportOption opts;
                    opts.scale = 1.0f;
                    measurementOk = IMPORT_API->ImportAvatarMeasurement(cmd.param1, cmd.param2, opts);
                }
                else {
                    measurementOk = IMPORT_API->ImportMeasurement(cmd.param1);
                }
                asyncResult.success = measurementOk;
                {
                    std::lock_guard<std::mutex> lock(g_nativeAvatarDebugMutex);
                    g_nativeAvatarDebugState.last_measurement_csv_path = cmd.param1;
                    g_nativeAvatarDebugState.last_measurement_template_path = cmd.param2;
                    g_nativeAvatarDebugState.last_measurement_csv_success = asyncResult.success;
                    g_nativeAvatarDebugState.last_message = asyncResult.success
                        ? "Imported native avatar measurement CSV"
                        : "Failed to import native avatar measurement CSV";
                }
                asyncResult.message = asyncResult.success
                    ? "Imported native avatar measurements: " + cmd.param1
                    : "Failed to import native avatar measurements: " + cmd.param1;
            }
            // ── Pattern import (DXF) ──────────────────────────────────────────
            else if (cmd.type == "import-pattern") {
                Marvelous::ImportDxfOption opts;
                opts.m_Scale   = (cmd.floatParam1 > 0.0f ? cmd.floatParam1 : 1.0f);
                opts.m_bAppend = true;          // append — preserve import order
                asyncResult.success = IMPORT_API->ImportDXF(cmd.param1, opts);
                {
                    std::lock_guard<std::mutex> lock(g_importDebugMutex);
                    g_lastPatternImports.push_back({cmd.param1, opts.m_Scale, asyncResult.success});
                    if (g_lastPatternImports.size() > 64)
                        g_lastPatternImports.erase(g_lastPatternImports.begin(), g_lastPatternImports.begin() + 32);
                }
                asyncResult.message = asyncResult.success
                    ? "Imported pattern: " + cmd.param1 + " (scale=" + std::to_string(opts.m_Scale) + ")"
                    : "Failed to import pattern: " + cmd.param1;
                if (asyncResult.success)
                    g_patternsLoaded++;
            }
            // ── New project ───────────────────────────────────────────────────
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
            // ── Set fabric diffuse color ─────────────────────────────────────────────────
            // floatParam1/2/3 = R/G/B (0–255); param3 = pattern_index
            // Uses CLOGuard + FabricDispatcher (Qt::QueuedConnection, non-blocking).
            else if (cmd.type == "set-fabric-color") {
                std::string guardErr;
                if (!CLOGuard::fabricReady(guardErr) ||
                    !CLOGuard::patternIndexValid(cmd.param3, guardErr)) {
                    asyncResult.success = false;
                    asyncResult.message = "[Guard] " + guardErr;
                } else {
                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
                    if (fabric_idx < 0) fabric_idx = 0;
                    float r = std::clamp(cmd.floatParam1, 0.0f, 255.0f) / 255.0f;
                    float g = std::clamp(cmd.floatParam2, 0.0f, 255.0f) / 255.0f;
                    float b = std::clamp(cmd.floatParam3, 0.0f, 255.0f) / 255.0f;
                    FabricDispatcher::dispatchColor(fabric_idx, r, g, b);
                    asyncResult.success = true;
                    asyncResult.message = "Color RGB(" +
                        std::to_string((int)cmd.floatParam1) + "," +
                        std::to_string((int)cmd.floatParam2) + "," +
                        std::to_string((int)cmd.floatParam3) +
                        ") dispatched to fabric " + std::to_string(fabric_idx) +
                        " [QueuedConnection]";
                }
            }
            // ── Set fabric base texture ───────────────────────────────────────
            // param1 = texture file path (PNG/JPEG); param3 = pattern_index
            else if (cmd.type == "set-fabric-texture") {
                std::string guardErr;
                if (!CLOGuard::fabricReady(guardErr)       ||
                    !CLOGuard::patternIndexValid(cmd.param3, guardErr) ||
                    !CLOGuard::fileExists(cmd.param1, guardErr)) {
                    asyncResult.success = false;
                    asyncResult.message = "[Guard] " + guardErr;
                } else {
                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
                    if (fabric_idx < 0) fabric_idx = 0;
                    FabricDispatcher::dispatchTexture(fabric_idx, cmd.param1);
                    asyncResult.success = true;
                    asyncResult.message = "Texture dispatched to fabric " +
                        std::to_string(fabric_idx) + ": " + cmd.param1 +
                        " [QueuedConnection]";
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
                    asyncResult.success = false;
                    asyncResult.message = "[Guard] " + guardErr;
                } else {
                    int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3);
                    if (fabric_idx < 0) fabric_idx = 0;
                    FabricDispatcher::dispatchTexture(fabric_idx, cmd.param1);
                    asyncResult.success = true;
                    asyncResult.message = "Graphic dispatched to fabric " +
                        std::to_string(fabric_idx) + ": " + cmd.param1 +
                        " [QueuedConnection]";
                }
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
            // ── Export avatar as AVT ──────────────────────────────────────────
            else if (cmd.type == "export-avatar-avt") {
                auto out = EXPORT_API->ExportAVT(cmd.param1);
                asyncResult.success = !out.empty();
                asyncResult.message = asyncResult.success
                    ? "Avatar AVT exported: " + out
                    : "Avatar AVT export failed";
            }
            // ── Avatar property mutation ──────────────────────────────────────
            else if (cmd.type == "avatar-set-properties") {
                AvatarPropertyDebugState debugState;
                debugState.avatar_index = (cmd.param3 >= 0 ? static_cast<unsigned int>(cmd.param3) : 0);
                debugState.unit = (cmd.param2.empty() ? "raw" : cmd.param2);
                debugState.requested_properties = cmd.stringMapParam1;
                try {
                    try { debugState.properties_before = UTILITY_API->GetAvatarProperties(debugState.avatar_index); } catch (...) {}
                    UTILITY_API->SetAvatarProperties(debugState.avatar_index, cmd.stringMapParam1);
                    try { debugState.properties_after = UTILITY_API->GetAvatarProperties(debugState.avatar_index); } catch (...) {}
                    debugState.changed_keys = ComputeChangedPropertyKeys(
                        debugState.properties_before, debugState.properties_after, debugState.requested_properties);
                    debugState.missing_after_keys = ComputeMissingAfterKeys(
                        debugState.properties_after, debugState.requested_properties);
                    asyncResult.success = true;
                    asyncResult.message =
                        "Avatar properties applied to avatar " + std::to_string(debugState.avatar_index) +
                        " (requested=" + std::to_string(debugState.requested_properties.size()) +
                        ", changed=" + std::to_string(debugState.changed_keys.size()) +
                        ", missing_after=" + std::to_string(debugState.missing_after_keys.size()) + ")";
                    debugState.success = true;
                    debugState.last_message = asyncResult.message;
                } catch (const std::exception& e) {
                    asyncResult.success = false;
                    asyncResult.message = "Failed to set avatar properties: " + std::string(e.what());
                    debugState.success = false;
                    debugState.last_message = asyncResult.message;
                }
                {
                    std::lock_guard<std::mutex> lock(g_avatarPropertyDebugMutex);
                    g_avatarPropertyDebugState = debugState;
                }
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
            else if (cmd.type == "read-pattern-bbox") {
                int patternIndex = cmd.param3;
                auto raw = PATTERN_API->GetBoundingBoxOfPattern(patternIndex);
                json bbox = json::object();
                for (const auto& kv : raw)
                    bbox[kv.first] = kv.second;
                syncResult = {
                    {"success", true},
                    {"pattern_index", patternIndex},
                    {"bbox", bbox},
                    {"area", PATTERN_API->GetPatternPieceArea(patternIndex)}
                };
            }
            else if (cmd.type == "read-pattern-input") {
                int patternIndex = cmd.param3;
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
                syncResult = {
                    {"success", true},
                    {"pattern_index", patternIndex},
                    {"parsed", parsedOk},
                    {"input", parsedOk ? parsed : json(inputInfo)}
                };
            }
            else if (cmd.type == "read-pattern-line-lengths") {
                int patternIndex = cmd.param3;
                int maxLines = (cmd.param4 > 0 ? cmd.param4 : 256);
                int stopAfterConsecutiveZero = 12;
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
                syncResult = {
                    {"success", true},
                    {"pattern_index", patternIndex},
                    {"line_count", static_cast<int>(lines.size())},
                    {"lines", lines}
                };
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
            else if (cmd.type == "read-arrangement-debug") {
                syncResult = BuildArrangementDebugPayload();
            }
            else if (cmd.type == "read-avatar-debug") {
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
                int slotCount = static_cast<int>(slotList.size());

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

                syncResult = {
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
                    arrangementSlotCount = static_cast<int>(list.size());
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
                        if (desc != row.end())
                            slotNames.push_back(desc->second);
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
            else if (cmd.type == "read-avatar-property-debug") {
                AvatarPropertyDebugState snapshot;
                {
                    std::lock_guard<std::mutex> lock(g_avatarPropertyDebugMutex);
                    snapshot = g_avatarPropertyDebugState;
                }
                syncResult = BuildAvatarPropertyDebugJson(snapshot);
            }
            else if (cmd.type == "read-avatar-state") {
                unsigned int avatarCount = 0;
                std::vector<std::string> avatarNames;
                std::vector<int> avatarGenders;
                json avatars = json::array();

                try { avatarCount = EXPORT_API->GetAvatarCount(); } catch (...) {}
                try { avatarNames = EXPORT_API->GetAvatarNameList(); } catch (...) {}
                try { avatarGenders = EXPORT_API->GetAvatarGenderList(); } catch (...) {}

                for (unsigned int i = 0; i < avatarCount; ++i) {
                    std::map<std::string, std::string> properties;
                    try {
                        properties = UTILITY_API->GetAvatarProperties(i);
                    }
                    catch (...) {}

                    json propertyJson = json::object();
                    for (const auto& kv : properties)
                        propertyJson[kv.first] = kv.second;

                    std::string avatarName =
                        (i < avatarNames.size() ? avatarNames[i] : ("avatar_" + std::to_string(i)));
                    int avatarGender =
                        (i < avatarGenders.size() ? avatarGenders[i] : -1);

                    avatars.push_back({
                        {"index", i},
                        {"name", avatarName},
                        {"gender_code", avatarGender},
                        {"gender", AvatarGenderLabel(avatarGender)},
                        {"properties", propertyJson}
                    });
                }

                syncResult = {
                    {"success", true},
                    {"avatar_count", avatarCount},
                    {"avatars", avatars}
                };
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
        catch (...) {
            // Non-std::exception throw. Record it and keep draining the rest
            // of the batch instead of letting it escape the loop.
            asyncResult.success = false;
            asyncResult.message = "Exception in '" + cmd.type + "': non-standard exception (unknown type)";
            syncResult = {{"success", false}, {"error", "non-standard exception (unknown type)"}};
        }

        if (cmd.isSync && cmd.syncPromise) {
            cmd.syncPromise->set_value(syncResult);
        } else {
            std::lock_guard<std::mutex> rl(g_resultsMutex);
            g_lastResults.push_back(asyncResult);
        }
    }

    // resetGuard's destructor resets g_queueProcessing = false here.
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
    svr.Get("/health", [](const Request&, Response& res) {
        json r = {
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
        res.set_content(r.dump(), "application/json");
    });

    // ── Fabric dispatch status endpoints ──────────────────────────────────────
    // GET /fabric-status: pending/completed/failed counters for async fabric calls.
    // POST /fabric-status/reset: clears counters before a new batch.
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
            {"dispatcher",   "QueuedConnection"}
        };
        res.set_content(response.dump(), "application/json");
    });

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

    svr.Get("/capabilities", [](const Request&, Response& res) {
        json r = {
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
            {"has_set_fabric_color", true},
            {"has_set_fabric_texture", true},
            {"has_set_fabric_graphic", true},
            {"notes", "has_avatar_state_readback and has_avatar_avt_export are set from a startup probe (Phase 3), not hardcoded. Line count may be absent in GetPatternInformation; use line-length probe endpoint"}
        };
        res.set_content(r.dump(), "application/json");
    });

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

        json r = {
            {"success", true},
            {"avatar_import", {
                {"path", avatarPath},
                {"scale", avatarScale},
                {"success", avatarSuccess}
            }},
            {"pattern_imports", patternImports}
        };
        res.set_content(r.dump(), "application/json");
    });

    svr.Get("/avatar/debug", [](const Request&, Response& res) {
        json r = dispatchSyncRead("read-avatar-debug");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    svr.Get("/avatar/native-debug", [](const Request&, Response& res) {
        json r = dispatchSyncRead("read-avatar-native-debug");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    svr.Get("/avatars/state", [](const Request&, Response& res) {
        json r = dispatchSyncRead("read-avatar-state");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

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
            {"last_results",     lastResults}
        };
        res.set_content(r.dump(), "application/json");
    });

    // ── POST /execute ────────────────────────────────────────────────────────
    // NOTE (history): this used to be a pure "compatibility nudge" that only
    // reported queue state, on the assumption the QTimer drains automatically.
    // That assumption doesn't always hold — the timer can silently stop firing
    // for a session, stalling the whole pipeline until someone clicks the
    // plugin's menu item by hand. wait_for_queue() in client.py already calls
    // this endpoint every few seconds while polling, so make it actually
    // request a drain via the same Qt::QueuedConnection pattern FabricDispatcher
    // uses, instead of just reporting status.
    svr.Post("/execute", [](const httplib::Request&, httplib::Response& res) {
        int  qsize      = 0;
        bool processing = false;
        {
            std::lock_guard<std::mutex> lk(g_queueMutex);
            qsize = static_cast<int>(g_commandQueue.size());
        }
        processing = g_queueProcessing.load();

        std::string dispatchNote = "queue empty";
        if (qsize > 0 && !processing) {
            // ProcessCommandQueue() guards its own re-entrancy via
            // g_queueProcessing.exchange(true), so redundant posts are safe.
            QMetaObject::invokeMethod(
                QCoreApplication::instance(),
                []() { ProcessCommandQueue(); },
                Qt::QueuedConnection
            );
            dispatchNote = "drain posted to main thread";
        } else if (processing) {
            dispatchNote = "drain already in progress";
        }

        json r = {
            {"success",          true},
            {"queue_size",       qsize},
            {"queue_processing", processing},
            {"message",          dispatchNote}
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

    svr.Get(R"(/patterns/(\d+)/bbox)", [](const httplib::Request& req, httplib::Response& res) {
        int idx = std::stoi(req.matches[1]);
        json r = dispatchSyncRead("read-pattern-bbox", idx);
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    svr.Get(R"(/patterns/(\d+)/input)", [](const httplib::Request& req, httplib::Response& res) {
        int idx = std::stoi(req.matches[1]);
        json r = dispatchSyncRead("read-pattern-input", idx);
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
    });

    svr.Get(R"(/patterns/(\d+)/line-lengths)", [](const httplib::Request& req, httplib::Response& res) {
        int idx = std::stoi(req.matches[1]);
        int maxLines = 256;
        if (req.has_param("max")) {
            try { maxLines = std::stoi(req.get_param_value("max")); } catch (...) {}
        }
        json r = dispatchSyncRead("read-pattern-line-lengths", idx, maxLines);
        res.status = r.value("success", false) ? 200 : 503;
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

    svr.Get("/arrangement/debug", [](const httplib::Request&, httplib::Response& res) {
        json r = dispatchSyncRead("read-arrangement-debug");
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
            float scale = j.value("scale", 1.0f);
            APICommand cmd;
            cmd.type   = "import-avatar";
            cmd.param1 = path;
            cmd.floatParam1 = scale;
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Avatar import queued"},
                      {"path", path}, {"scale", scale}, {"queue_size", qsize}};
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
    svr.Post("/import-avatar-avt", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string path = j.at("path");
            APICommand cmd;
            cmd.type   = "import-avatar-avt";
            cmd.param1 = path;
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Native avatar import queued. Call /execute to process."},
                      {"path", path}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    svr.Post("/import-avatar-measurements", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string csvPath = j.at("csv_path");
            std::string templatePath = j.value("template_path", "");
            APICommand cmd;
            cmd.type   = "import-avatar-measurements";
            cmd.param1 = csvPath;
            cmd.param2 = templatePath;
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Avatar measurement import queued. Call /execute to process."},
                      {"csv_path", csvPath}, {"template_path", templatePath}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    svr.Post("/import-pattern", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            std::string path = j.at("path");
            float scale = j.value("scale", 1.0f);
            APICommand cmd;
            cmd.type   = "import-pattern";
            cmd.param1 = path;
            cmd.floatParam1 = scale;
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Pattern import queued"},
                      {"path", path}, {"scale", scale}, {"queue_size", qsize}};
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

    // ── POST /set-fabric-color ────────────────────────────────────────────────
    // Expects: {pattern_index, r, g, b}  (r/g/b in 0–255)
    svr.Post("/set-fabric-color", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type        = "set-fabric-color";
            cmd.param3      = j.at("pattern_index").get<int>();
            cmd.floatParam1 = (float)j.at("r").get<int>();
            cmd.floatParam2 = (float)j.at("g").get<int>();
            cmd.floatParam3 = (float)j.at("b").get<int>();
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Fabric color queued"},
                      {"pattern_index", cmd.param3}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /set-fabric-texture ──────────────────────────────────────────────
    // Expects: {pattern_index, texture_path}
    svr.Post("/set-fabric-texture", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type   = "set-fabric-texture";
            cmd.param3 = j.at("pattern_index").get<int>();
            cmd.param1 = j.at("texture_path").get<std::string>();
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Fabric texture queued"},
                      {"pattern_index", cmd.param3}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /set-fabric-graphic ──────────────────────────────────────────────
    // Expects: {pattern_index, graphic_path, u?, v?, scale?}
    svr.Post("/set-fabric-graphic", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type        = "set-fabric-graphic";
            cmd.param3      = j.at("pattern_index").get<int>();
            cmd.param1      = j.at("graphic_path").get<std::string>();
            cmd.floatParam4 = (float)j.value("u",     0.5);
            cmd.floatParam5 = (float)j.value("v",     0.3);
            cmd.floatParam6 = (float)j.value("scale", 1.0);
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Fabric graphic queued"},
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

    // ── POST /export-avatar-avt ───────────────────────────────────────────────
    svr.Post("/export-avatar-avt", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            APICommand cmd;
            cmd.type   = "export-avatar-avt";
            cmd.param1 = j.at("path");
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {{"success", true}, {"message", "Avatar AVT export queued"},
                      {"path", cmd.param1}, {"queue_size", qsize}};
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── POST /avatar/set-properties ───────────────────────────────────────────
    svr.Post("/avatar/set-properties", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            if (!j.contains("properties"))
                throw std::runtime_error("Missing required field: properties");
            APICommand cmd;
            cmd.type   = "avatar-set-properties";
            cmd.param3 = j.value("avatar_index", 0);
            cmd.param2 = j.value("unit", std::string("raw"));
            cmd.stringMapParam1 = JsonObjectToStringMap(j["properties"]);
            json propertyKeys = json::array();
            for (const auto& [key, _] : cmd.stringMapParam1)
                propertyKeys.push_back(key);
            int qsize = 0;
            {
                std::lock_guard<std::mutex> lk(g_queueMutex);
                g_commandQueue.push(cmd);
                qsize = static_cast<int>(g_commandQueue.size());
            }
            json r = {
                {"success", true},
                {"message", "Avatar property update queued"},
                {"avatar_index", cmd.param3},
                {"unit", cmd.param2},
                {"property_count", static_cast<int>(cmd.stringMapParam1.size())},
                {"property_keys", propertyKeys},
                {"queue_size", qsize}
            };
            res.set_content(r.dump(), "application/json");
        } catch (const std::exception& e) {
            json r = {{"success", false}, {"error", e.what()}};
            res.status = 400;
            res.set_content(r.dump(), "application/json");
        }
    });

    // ── GET /avatar/property-debug ────────────────────────────────────────────
    svr.Get("/avatar/property-debug", [](const httplib::Request&, httplib::Response& res) {
        json r = dispatchSyncRead("read-avatar-property-debug");
        res.status = r.value("success", false) ? 200 : 503;
        res.set_content(r.dump(), "application/json");
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
DYLIB_DESTRUCTOR
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

CLO_EXPORT const char* GetActionName()
{
    return "REST Server & Execute";
}

CLO_EXPORT const char* GetObjectNameTreeToAddAction()
{
    return "Plugins";
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
    // Phase 3: install crash-log signal handlers and probe SEH-crash-prone
    // (on Windows) CLO APIs once, before the server starts taking requests,
    // so /capabilities reflects what actually works this session.
    InstallCrashSignalHandlers();
    RunCapabilityProbesOnce();

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
