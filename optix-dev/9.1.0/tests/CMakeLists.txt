cmake_minimum_required(VERSION 3.23)
project(optix_consumer LANGUAGES CXX)

find_package(OptiX 9.1 CONFIG REQUIRED)

add_executable(optix_consumer optix_consumer.cpp)
target_link_libraries(optix_consumer PRIVATE OptiX::OptiX)
target_compile_features(optix_consumer PRIVATE cxx_std_17)
