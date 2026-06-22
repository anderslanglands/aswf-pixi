if(NOT DEFINED MATERIALX_CONFIG_DIR)
    message(FATAL_ERROR "MATERIALX_CONFIG_DIR is required")
endif()

if(NOT DEFINED MATERIALX_OPTIONAL_TARGET_SET)
    message(FATAL_ERROR "MATERIALX_OPTIONAL_TARGET_SET is required")
endif()

file(MAKE_DIRECTORY "${MATERIALX_CONFIG_DIR}")

set(_materialx_optional_common [=[
include(CMakeFindDependencyMacro)

get_filename_component(_materialx_optional_import_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

function(_materialx_optional_library_location _out_var _library_name)
    if(WIN32)
        set(_location "${_materialx_optional_import_prefix}/bin/${_library_name}.dll")
    elseif(APPLE)
        set(_location "${_materialx_optional_import_prefix}/lib/lib${_library_name}.dylib")
    else()
        set(_location "${_materialx_optional_import_prefix}/lib/lib${_library_name}.so")
    endif()
    set(${_out_var} "${_location}" PARENT_SCOPE)
endfunction()

function(_materialx_add_optional_library _target_name _library_name)
    if(TARGET ${_target_name})
        return()
    endif()

    _materialx_optional_library_location(_materialx_optional_location "${_library_name}")
    if(NOT EXISTS "${_materialx_optional_location}")
        return()
    endif()

    add_library(${_target_name} SHARED IMPORTED)
    set_target_properties(${_target_name} PROPERTIES
        IMPORTED_LOCATION "${_materialx_optional_location}"
        INTERFACE_INCLUDE_DIRECTORIES "${_materialx_optional_import_prefix}/include")

    if(WIN32)
        set_target_properties(${_target_name} PROPERTIES
            IMPORTED_IMPLIB "${_materialx_optional_import_prefix}/lib/${_library_name}.lib")
    endif()
endfunction()
]=])

if(MATERIALX_OPTIONAL_TARGET_SET STREQUAL "render")
    set(_materialx_optional_contents "${_materialx_optional_common}")
    string(APPEND _materialx_optional_contents [=[

if(UNIX AND NOT APPLE)
    find_dependency(X11 REQUIRED COMPONENTS Xt)
    find_dependency(OpenGL REQUIRED)
elseif(APPLE)
    find_dependency(OpenGL REQUIRED)
endif()

_materialx_add_optional_library(MaterialXRender MaterialXRender)
if(TARGET MaterialXRender)
    set_target_properties(MaterialXRender PROPERTIES
        INTERFACE_LINK_LIBRARIES "MaterialXGenShader;MaterialXGenHw")
endif()

_materialx_add_optional_library(MaterialXRenderHw MaterialXRenderHw)
if(TARGET MaterialXRenderHw)
    if(APPLE)
        set(_materialx_render_hw_deps "MaterialXRender;-framework Foundation;-framework Metal;-framework Cocoa")
    elseif(UNIX)
        set(_materialx_render_hw_deps "MaterialXRender;X11::X11;X11::Xt")
    else()
        set(_materialx_render_hw_deps "MaterialXRender")
    endif()
    set_target_properties(MaterialXRenderHw PROPERTIES
        INTERFACE_LINK_LIBRARIES "${_materialx_render_hw_deps}")
endif()

_materialx_add_optional_library(MaterialXRenderGlsl MaterialXRenderGlsl)
if(TARGET MaterialXRenderGlsl)
    if(WIN32)
        set(_materialx_render_glsl_deps "MaterialXRenderHw;MaterialXGenGlsl;Opengl32")
    elseif(APPLE)
        set(_materialx_render_glsl_deps "MaterialXRenderHw;MaterialXGenGlsl;-framework OpenGL;-framework Foundation;-framework Cocoa;-framework Metal")
    else()
        set(_materialx_render_glsl_deps "MaterialXRenderHw;MaterialXGenGlsl;OpenGL::GL;X11::X11;X11::Xt")
    endif()
    set_target_properties(MaterialXRenderGlsl PROPERTIES
        INTERFACE_LINK_LIBRARIES "${_materialx_render_glsl_deps}")
endif()

_materialx_add_optional_library(MaterialXRenderMsl MaterialXRenderMsl)
if(TARGET MaterialXRenderMsl)
    if(APPLE)
        set(_materialx_render_msl_deps "MaterialXRenderHw;MaterialXGenMsl;-framework Cocoa;-framework OpenGL;-framework Foundation;-framework Metal;-framework MetalPerformanceShaders")
    elseif(UNIX)
        set(_materialx_render_msl_deps "MaterialXRenderHw;MaterialXGenMsl;OpenGL::GL;X11::X11;X11::Xt")
    else()
        set(_materialx_render_msl_deps "MaterialXRenderHw;MaterialXGenMsl;Opengl32")
    endif()
    set_target_properties(MaterialXRenderMsl PROPERTIES
        INTERFACE_LINK_LIBRARIES "${_materialx_render_msl_deps}")
endif()

unset(_materialx_render_glsl_deps)
unset(_materialx_render_hw_deps)
unset(_materialx_render_msl_deps)
]=])
    set(_materialx_optional_filename "MaterialXRenderOptionalTargets.cmake")
elseif(MATERIALX_OPTIONAL_TARGET_SET STREQUAL "render-osl")
    set(_materialx_optional_contents "${_materialx_optional_common}")
    string(APPEND _materialx_optional_contents [=[

_materialx_add_optional_library(MaterialXRenderOsl MaterialXRenderOsl)
if(TARGET MaterialXRenderOsl)
    set_target_properties(MaterialXRenderOsl PROPERTIES
        INTERFACE_LINK_LIBRARIES "MaterialXRender")
endif()

if(NOT TARGET MaterialXGenOsl_LibsToOso)
    if(WIN32)
        set(_materialx_libstooso_location "${_materialx_optional_import_prefix}/bin/MaterialXGenOsl_LibsToOso.exe")
    else()
        set(_materialx_libstooso_location "${_materialx_optional_import_prefix}/bin/MaterialXGenOsl_LibsToOso")
    endif()
    if(EXISTS "${_materialx_libstooso_location}")
        add_executable(MaterialXGenOsl_LibsToOso IMPORTED)
        set_target_properties(MaterialXGenOsl_LibsToOso PROPERTIES
            IMPORTED_LOCATION "${_materialx_libstooso_location}")
    endif()
endif()

unset(_materialx_libstooso_location)
]=])
    set(_materialx_optional_filename "MaterialXRenderOslOptionalTargets.cmake")
elseif(MATERIALX_OPTIONAL_TARGET_SET STREQUAL "render-slang")
    set(_materialx_optional_contents "${_materialx_optional_common}")
    string(APPEND _materialx_optional_contents [=[

find_dependency(slang CONFIG REQUIRED)

_materialx_add_optional_library(MaterialXRenderSlang MaterialXRenderSlang)
if(TARGET MaterialXRenderSlang)
    set_target_properties(MaterialXRenderSlang PROPERTIES
        INTERFACE_LINK_LIBRARIES "MaterialXRenderHw;MaterialXGenSlang;slang::slang")
endif()
]=])
    set(_materialx_optional_filename "MaterialXRenderSlangOptionalTargets.cmake")
else()
    message(FATAL_ERROR "Unknown MATERIALX_OPTIONAL_TARGET_SET: ${MATERIALX_OPTIONAL_TARGET_SET}")
endif()

file(WRITE "${MATERIALX_CONFIG_DIR}/${_materialx_optional_filename}" "${_materialx_optional_contents}")
