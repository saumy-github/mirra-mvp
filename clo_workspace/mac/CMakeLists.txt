cmake_minimum_required(VERSION 3.20)
project(RestPlugin LANGUAGES CXX)

# ─── C++ standard ─────────────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ─── macOS target ─────────────────────────────────────────────────────────────
set(CMAKE_OSX_ARCHITECTURES "arm64" CACHE STRING "Build for Apple Silicon")
set(CMAKE_MACOSX_RPATH ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ─── CLO SDK path ─────────────────────────────────────────────────────────────
# Priority: -DCLO_SDK_PATH=... on command line > CLO_SDK_PATH env var
if(DEFINED CLO_SDK_PATH)
    set(CLO_SDK_ROOT "${CLO_SDK_PATH}")
elseif(DEFINED ENV{CLO_SDK_PATH})
    file(TO_CMAKE_PATH "$ENV{CLO_SDK_PATH}" CLO_SDK_ROOT)
else()
    message(FATAL_ERROR
        "CLO SDK path not set.\n"
        "Pass -DCLO_SDK_PATH=/path/to/CLO_SDK or set the CLO_SDK_PATH environment variable.")
endif()

set(CLO_API_DIR "${CLO_SDK_ROOT}/CLOAPIInterface")

message(STATUS "CLO SDK root : ${CLO_SDK_ROOT}")
message(STATUS "CLO API dir  : ${CLO_API_DIR}")

# ─── Qt 6 ─────────────────────────────────────────────────────────────────────
# We need Qt headers for QTimer/QObject, but we do NOT link against Qt::Core.
# CLO already has Qt loaded in its process; -undefined dynamic_lookup lets
# Qt symbols resolve from CLO's own Qt at runtime (no duplicate Qt instance).
#
# Qt6, not Qt5: CLO 2026 (verified on 2026.0.374) ships Qt 6.10.3 and no Qt5
# at all. A Qt5-header build links fine but dlopen fails at load time —
# QArrayData::shared_null, QArrayData::deallocate(QArrayData*,ulong,ulong) and
# QString::fromUtf8_helper(const char*,int) were all removed or resigned in
# Qt6, so CLO cannot satisfy them. Keep this on Qt6 unless CLO reverts.
find_package(Qt6 COMPONENTS Core REQUIRED)
message(STATUS "Qt6Core      : ${Qt6Core_DIR}")

# ─── Shared headers from clo_workspace/shared/ ──────────────────────────────────
set(SHARED_HEADERS "${CMAKE_CURRENT_SOURCE_DIR}/../shared")

# ─── Plugin target ────────────────────────────────────────────────────────────
add_library(RestPlugin SHARED RestPlugin_macOS.cpp)

target_include_directories(RestPlugin PRIVATE
    "${CLO_API_DIR}"
    "${CLO_API_DIR}/include"
    "${SHARED_HEADERS}"
    "${CMAKE_CURRENT_SOURCE_DIR}"
    # Qt6 headers only — not linked, symbols resolved from CLO's Qt6 at runtime
    "$<TARGET_PROPERTY:Qt6::Core,INTERFACE_INCLUDE_DIRECTORIES>"
)

# Find CLOAPIInterface static/dynamic library
find_library(CLO_API_LIB
    NAMES CLOAPIInterface
    HINTS "${CLO_API_DIR}/Lib"
          "${CLO_API_DIR}/lib"
    REQUIRED
)
message(STATUS "CLOAPIInterface: ${CLO_API_LIB}")

target_link_libraries(RestPlugin PRIVATE
    "${CLO_API_LIB}"
    # Qt6::Core intentionally omitted — CLO provides Qt6 at runtime.
    # -undefined dynamic_lookup allows Qt symbols to be unresolved at link time.
)

# Allow unresolved Qt symbols — they resolve from CLO's loaded Qt6 at runtime.
target_link_options(RestPlugin PRIVATE -undefined dynamic_lookup)

# ─── Compiler flags ───────────────────────────────────────────────────────────
# Hide all symbols by default; only CLO_EXPORT-marked symbols are visible.
target_compile_options(RestPlugin PRIVATE -fvisibility=hidden)

target_compile_definitions(RestPlugin PRIVATE
    CPPHTTPLIB_THREAD_POOL_COUNT=4
    # Qt headers emit a reference to qt_version_tag_<major>_<minor> matching the
    # headers you compiled against. CLO ships Qt 6.10.3 while Homebrew's qt is
    # 6.11.x, so that symbol does not exist in the host and dlopen fails with
    # "symbol not found in flat namespace '_qt_version_tag_6_11'" — CLO then
    # reports "The plug-in has a problem." Qt provides this macro to suppress
    # the tag; the plugin only uses long-stable QtCore API, so exact-minor
    # matching buys nothing. Remove only if you build against CLO's exact Qt.
    QT_NO_VERSION_TAGGING
)

# ─── Output name and directory ────────────────────────────────────────────────
set_target_properties(RestPlugin PROPERTIES
    OUTPUT_NAME  "RestPlugin"
    PREFIX       "lib"
    SUFFIX       ".dylib"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/Release"
)

# ─── RPATH ────────────────────────────────────────────────────────────────────
# Embed @rpath so the dylib finds Qt and CLO libs at runtime without manual
# install_name_tool surgery.
set_target_properties(RestPlugin PROPERTIES
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "@loader_path;@loader_path/../Frameworks"
)
