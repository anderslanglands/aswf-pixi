cmake_minimum_required(VERSION 3.20)

project(opencolorio_consumer LANGUAGES CXX)

find_package(OpenColorIO CONFIG REQUIRED)

add_executable(opencolorio_consumer opencolorio_consumer.cpp)
target_link_libraries(opencolorio_consumer PRIVATE OpenColorIO::OpenColorIO)
target_compile_features(opencolorio_consumer PRIVATE cxx_std_11)
