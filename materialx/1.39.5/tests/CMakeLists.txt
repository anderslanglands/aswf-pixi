cmake_minimum_required(VERSION 3.20)

project(materialx_consumer LANGUAGES CXX)

find_package(MaterialX CONFIG REQUIRED)

add_executable(materialx_consumer materialx_consumer.cpp)
target_compile_features(materialx_consumer PRIVATE cxx_std_17)
target_link_libraries(materialx_consumer
    PRIVATE
        MaterialXCore
        MaterialXFormat
        MaterialXGenShader
        MaterialXGenGlsl
        MaterialXGenMsl
        MaterialXGenOsl
        MaterialXGenMdl
        MaterialXGenSlang
)

if(TARGET MaterialXRender AND TARGET MaterialXRenderGlsl)
    add_executable(materialx_render_consumer materialx_render_consumer.cpp)
    target_compile_features(materialx_render_consumer PRIVATE cxx_std_17)
    target_link_libraries(materialx_render_consumer
        PRIVATE
            MaterialXRender
            MaterialXRenderGlsl
    )
endif()

if(TARGET MaterialXRenderOsl)
    if(NOT TARGET MaterialXGenOsl_LibsToOso)
        message(FATAL_ERROR "MaterialXGenOsl_LibsToOso target is required with MaterialXRenderOsl")
    endif()
    add_executable(materialx_render_osl_consumer materialx_render_osl_consumer.cpp)
    target_compile_features(materialx_render_osl_consumer PRIVATE cxx_std_17)
    target_link_libraries(materialx_render_osl_consumer
        PRIVATE
            MaterialXRenderOsl
    )
endif()

if(TARGET MaterialXRenderSlang)
    add_executable(materialx_render_slang_consumer materialx_render_slang_consumer.cpp)
    target_compile_features(materialx_render_slang_consumer PRIVATE cxx_std_17)
    target_link_libraries(materialx_render_slang_consumer
        PRIVATE
            MaterialXRenderSlang
    )
endif()

if(APPLE AND TARGET MaterialXRenderMsl)
    enable_language(OBJCXX)
    add_executable(materialx_render_msl_consumer materialx_render_msl_consumer.mm)
    target_compile_features(materialx_render_msl_consumer PRIVATE cxx_std_17)
    target_link_libraries(materialx_render_msl_consumer
        PRIVATE
            MaterialXRenderMsl
    )
endif()
