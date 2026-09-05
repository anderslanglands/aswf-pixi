cmake_minimum_required(VERSION 3.15)

project(ptex_consumer LANGUAGES CXX)

find_package(Ptex 2.5 CONFIG REQUIRED)

if(NOT TARGET Ptex::Ptex_dynamic)
    message(FATAL_ERROR "Expected shared Ptex CMake target Ptex::Ptex_dynamic")
endif()

add_executable(ptex_consumer ptex_consumer.cpp)
target_compile_features(ptex_consumer PRIVATE cxx_std_17)
target_link_libraries(ptex_consumer PRIVATE Ptex::Ptex_dynamic)
