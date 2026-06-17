cmake_minimum_required(VERSION 3.20)

project(materialx_consumer LANGUAGES CXX)

find_package(MaterialX CONFIG REQUIRED)

add_executable(materialx_consumer materialx_consumer.cpp)
target_link_libraries(materialx_consumer
    PRIVATE
        MaterialXCore
        MaterialXFormat
        MaterialXGenShader
        MaterialXGenGlsl
        MaterialXGenMsl
)
