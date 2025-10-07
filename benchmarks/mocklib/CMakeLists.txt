cmake_minimum_required(VERSION 3.10)
project(mocklib VERSION 1.0.0)

# Set C standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Add library
add_library(mocklib_static STATIC mocklib.c)
add_library(mocklib_shared SHARED mocklib.c)

# Set library properties
set_target_properties(mocklib_static PROPERTIES
    OUTPUT_NAME mocklib
    PUBLIC_HEADER mocklib.h
)

set_target_properties(mocklib_shared PROPERTIES
    OUTPUT_NAME mocklib
    PUBLIC_HEADER mocklib.h
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

# Include directories
target_include_directories(mocklib_static PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

target_include_directories(mocklib_shared PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

# Installation
install(TARGETS mocklib_static mocklib_shared
    EXPORT mocklibTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    PUBLIC_HEADER DESTINATION include
)