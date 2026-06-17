cmake_minimum_required(VERSION 3.20)

project(libuhdr_consumer LANGUAGES CXX)

set(_libuhdr_prefixes)
foreach(_env_var IN ITEMS CONDA_PREFIX PREFIX LIBRARY_PREFIX)
    if(DEFINED ENV{${_env_var}})
        list(APPEND _libuhdr_prefixes "$ENV{${_env_var}}")
    endif()
endforeach()
list(REMOVE_DUPLICATES _libuhdr_prefixes)
if(NOT _libuhdr_prefixes)
    message(FATAL_ERROR "Expected a pixi/conda prefix environment variable for libuhdr lookup")
endif()

find_path(LIBUHDR_INCLUDE_DIR
    NAMES ultrahdr_api.h
    HINTS ${_libuhdr_prefixes}
    PATH_SUFFIXES include Library/include
    NO_DEFAULT_PATH
    REQUIRED
)
find_library(LIBUHDR_LIBRARY
    NAMES uhdr libuhdr
    HINTS ${_libuhdr_prefixes}
    PATH_SUFFIXES lib Library/lib
    NO_DEFAULT_PATH
    REQUIRED
)

add_executable(libuhdr_consumer libuhdr_consumer.cpp)
target_compile_features(libuhdr_consumer PRIVATE cxx_std_17)
target_compile_definitions(libuhdr_consumer PRIVATE UHDR_USING_SHARED_LIBRARY)
target_include_directories(libuhdr_consumer PRIVATE "${LIBUHDR_INCLUDE_DIR}")
target_link_libraries(libuhdr_consumer PRIVATE "${LIBUHDR_LIBRARY}")
