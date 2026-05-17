cmake_minimum_required(VERSION 3.20)
project(RestPlugin LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Add paths for CLO SDK
if(DEFINED ENV{CLO_SDK_PATH} AND NOT "$ENV{CLO_SDK_PATH}" STREQUAL "")
    file(TO_CMAKE_PATH "$ENV{CLO_SDK_PATH}" CLO_SDK_ROOT)
else()
    message(FATAL_ERROR "CLO_SDK_PATH must be set before configuring RestPlugin.")
endif()
set(CLO_API_INTERFACE_DIR "${CLO_SDK_ROOT}/CLOAPIInterface")

# Create shared library
add_library(RestPlugin SHARED
    RestPlugin_windows.cpp
    dllmain.cpp
)

# Include directories
target_include_directories(RestPlugin PRIVATE
    ${CLO_API_INTERFACE_DIR}
    ${CLO_API_INTERFACE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../shared
)

# Find and link CLOAPIInterface library
find_library(CLO_API_INTERFACE NAMES CLOAPIInterface HINTS ${CLO_API_INTERFACE_DIR}/Lib REQUIRED)
find_file(CLO_API_INTERFACE_DLL NAMES CLOAPIInterface.dll HINTS ${CLO_API_INTERFACE_DIR}/Lib REQUIRED)

# Windows specific settings
if(MSVC)
    # Runtime library
    set_target_properties(RestPlugin PROPERTIES
        MSVC_RUNTIME_LIBRARY "MultiThreadedDLL"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/Release"
        LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/Release"
    )
    
    # Preprocessor definitions
    target_compile_definitions(RestPlugin PRIVATE
        UNICODE
        _UNICODE
        _WINDOWS
        _USRDLL
        BOMAPIDLL_EXPORTS
    )
    
    # Link against CLOAPIInterface
    target_link_libraries(RestPlugin PRIVATE
        ${CLO_API_INTERFACE}
    )
endif()
