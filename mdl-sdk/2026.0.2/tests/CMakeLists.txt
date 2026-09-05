cmake_minimum_required(VERSION 3.20)

project(mdl_sdk_consumer LANGUAGES CXX)

find_package(mdl CONFIG REQUIRED)

foreach(_target mdl::mdl_sdk mdl::mdl_core)
    if(NOT TARGET "${_target}")
        message(FATAL_ERROR "Expected MDL SDK target ${_target} to be exported.")
    endif()
endforeach()

add_executable(mdl_sdk_consumer mdl_sdk_consumer.cpp)
target_compile_features(mdl_sdk_consumer PRIVATE cxx_std_17)
foreach(_target mdl::mdl_sdk mdl::mdl_core)
    get_target_property(_include_dirs "${_target}" INTERFACE_INCLUDE_DIRECTORIES)
    if(_include_dirs)
        target_include_directories(mdl_sdk_consumer PRIVATE ${_include_dirs})
    endif()
endforeach()
target_link_libraries(mdl_sdk_consumer PRIVATE ${CMAKE_DL_LIBS})
target_compile_definitions(mdl_sdk_consumer PRIVATE
    MDL_SDK_LIBRARY_PATH="$<TARGET_FILE:mdl::mdl_sdk>"
    MDL_CORE_LIBRARY_PATH="$<TARGET_FILE:mdl::mdl_core>"
)

enable_testing()
add_test(NAME mdl_sdk_consumer COMMAND mdl_sdk_consumer)
