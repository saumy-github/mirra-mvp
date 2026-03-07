cmake_minimum_required(VERSION 3.20)
project(RestPlugin LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Add paths for CLO SDK
set(CLO_SDK_ROOT "C:/setup/CLO_SDK_v2025.2.236_WIN/CLO_SDK_v2025.2.236_WIN")
set(CLO_API_INTERFACE_DIR "${CLO_SDK_ROOT}/CLOAPIInterface")

# Create shared library
add_library(RestPlugin SHARED
    RestPlugin.cpp
    dllmain.cpp
)

# Include directories
target_include_directories(RestPlugin PRIVATE
    ${CLO_API_INTERFACE_DIR}
    ${CLO_API_INTERFACE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}
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

# Post build message
add_custom_command(TARGET RestPlugin POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "========================================="
    COMMAND ${CMAKE_COMMAND} -E echo "Build complete!"
    COMMAND ${CMAKE_COMMAND} -E echo "========================================="
    COMMAND ${CMAKE_COMMAND} -E echo "DLL Location: ${CMAKE_BINARY_DIR}/Release/RestPlugin.dll"
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "To install:"
    COMMAND ${CMAKE_COMMAND} -E echo "1. Close CLO if running"
    COMMAND ${CMAKE_COMMAND} -E echo "2. Copy to: C:/Program Files/CLO Standalone OnlineAuth/plugins/"
    COMMAND ${CMAKE_COMMAND} -E echo "3. Restart CLO"
    COMMAND ${CMAKE_COMMAND} -E echo "========================================="
    COMMAND ${CMAKE_COMMAND} -E echo ""
)
