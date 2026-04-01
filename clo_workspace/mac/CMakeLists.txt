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

# ─── Qt 5.15 ──────────────────────────────────────────────────────────────────
# We need Qt5 headers for QTimer/QObject, but we do NOT link against Qt5::Core.
# CLO already has Qt5 loaded in its process; -undefined dynamic_lookup lets
# Qt symbols resolve from CLO's own Qt5 at runtime (no duplicate Qt5 instance).
find_package(Qt5 COMPONENTS Core REQUIRED)
message(STATUS "Qt5Core      : ${Qt5Core_DIR}")

# ─── Shared headers from clo_workspace/shared/ ──────────────────────────────────
set(SHARED_HEADERS "${CMAKE_CURRENT_SOURCE_DIR}/../shared")

# ─── Plugin target ────────────────────────────────────────────────────────────
add_library(RestPlugin SHARED RestPlugin_macOS.cpp)

target_include_directories(RestPlugin PRIVATE
    "${CLO_API_DIR}"
    "${CLO_API_DIR}/include"
    "${SHARED_HEADERS}"
    "${CMAKE_CURRENT_SOURCE_DIR}"
    # Qt5 headers only — not linked, symbols resolved from CLO's Qt5 at runtime
    "$<TARGET_PROPERTY:Qt5::Core,INTERFACE_INCLUDE_DIRECTORIES>"
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
    # Qt5::Core intentionally omitted — CLO provides Qt5 at runtime.
    # -undefined dynamic_lookup allows Qt symbols to be unresolved at link time.
)

# Allow unresolved Qt symbols — they resolve from CLO's loaded Qt5 at runtime.
target_link_options(RestPlugin PRIVATE -undefined dynamic_lookup)

# ─── Compiler flags ───────────────────────────────────────────────────────────
# Hide all symbols by default; only CLO_EXPORT-marked symbols are visible.
target_compile_options(RestPlugin PRIVATE -fvisibility=hidden)

target_compile_definitions(RestPlugin PRIVATE
    CPPHTTPLIB_THREAD_POOL_COUNT=4
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

# ─── Install target ───────────────────────────────────────────────────────────
# Copies the dylib to the default CLO plugin search directory.
if(DEFINED ENV{CLO_PLUGINS_DIR} AND NOT "$ENV{CLO_PLUGINS_DIR}" STREQUAL "")
    file(TO_CMAKE_PATH "$ENV{CLO_PLUGINS_DIR}" CLO_PLUGIN_INSTALL_DIR)
else()
    set(CLO_PLUGIN_INSTALL_DIR "$ENV{HOME}/Documents/CLO/Plugins")
endif()

install(TARGETS RestPlugin
    LIBRARY DESTINATION "${CLO_PLUGIN_INSTALL_DIR}"
)

# ─── Post-build verification hints ────────────────────────────────────────────
add_custom_command(TARGET RestPlugin POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "========================================================="
    COMMAND ${CMAKE_COMMAND} -E echo "Build complete: $<TARGET_FILE:RestPlugin>"
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "Verify the dylib:"
    COMMAND ${CMAKE_COMMAND} -E echo "  file $<TARGET_FILE:RestPlugin>"
    COMMAND ${CMAKE_COMMAND} -E echo "  otool -L $<TARGET_FILE:RestPlugin>"
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "Install to CLO plugin folder:"
    COMMAND ${CMAKE_COMMAND} -E echo "  cmake --install ."
    COMMAND ${CMAKE_COMMAND} -E echo "  Target: ${CLO_PLUGIN_INSTALL_DIR}/"
    COMMAND ${CMAKE_COMMAND} -E echo "========================================================="
)
