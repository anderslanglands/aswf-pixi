cmake_minimum_required(VERSION 3.20)
project(shader_slang_consumer LANGUAGES CXX)

find_package(slang CONFIG REQUIRED)

if(NOT TARGET slang::slangc)
    message(FATAL_ERROR "The slang::slangc imported executable target was not exported")
endif()
if(NOT SLANG_EXECUTABLE)
    message(FATAL_ERROR "SLANG_EXECUTABLE was not set by the Slang CMake package")
endif()

add_executable(shader_slang_consumer shader_slang_consumer.cpp)
target_compile_features(shader_slang_consumer PRIVATE cxx_std_17)
target_link_libraries(shader_slang_consumer PRIVATE slang::slang)
