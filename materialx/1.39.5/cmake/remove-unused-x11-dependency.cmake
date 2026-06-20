if(NOT DEFINED MATERIALX_CONFIG_FILE)
    message(FATAL_ERROR "MATERIALX_CONFIG_FILE is required")
endif()

if(NOT EXISTS "${MATERIALX_CONFIG_FILE}")
    message(FATAL_ERROR "MaterialX config file not found: ${MATERIALX_CONFIG_FILE}")
endif()

file(READ "${MATERIALX_CONFIG_FILE}" _materialx_config)
string(REPLACE "\r\n" "\n" _materialx_config "${_materialx_config}")

set(_unused_x11_dependency [=[
if(UNIX AND NOT APPLE)
    find_dependency(X11 REQUIRED COMPONENTS Xt)
    if("RenderGlsl" IN_LIST MaterialX_FIND_COMPONENTS)
        find_dependency(OpenGL REQUIRED)
        set(MaterialX_RenderGlsl_FOUND TRUE)
    endif()
endif()
]=])

string(REPLACE "${_unused_x11_dependency}" "" _materialx_config_patched "${_materialx_config}")
file(WRITE "${MATERIALX_CONFIG_FILE}" "${_materialx_config_patched}")

get_filename_component(_materialx_config_dir "${MATERIALX_CONFIG_FILE}" DIRECTORY)
file(GLOB _materialx_cmake_files "${_materialx_config_dir}/*.cmake")
foreach(_materialx_cmake_file IN LISTS _materialx_cmake_files)
    file(READ "${_materialx_cmake_file}" _materialx_cmake_content)
    string(TOLOWER "${_materialx_cmake_content}" _materialx_cmake_content_lower)
    if(_materialx_cmake_content_lower MATCHES "find_(dependency|package)[ \t\r\n]*\\([ \t\r\n]*x11")
        message(FATAL_ERROR "MaterialX CMake metadata still contains an unexpected X11 dependency: ${_materialx_cmake_file}")
    endif()
endforeach()
