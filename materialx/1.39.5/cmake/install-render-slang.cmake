foreach(_required_var IN ITEMS MATERIALX_BUILD_DIR MATERIALX_SOURCE_DIR MATERIALX_INSTALL_PREFIX)
    if(NOT DEFINED ${_required_var})
        message(FATAL_ERROR "${_required_var} is required")
    endif()
endforeach()

file(MAKE_DIRECTORY "${MATERIALX_INSTALL_PREFIX}/include/MaterialXRenderSlang")
file(GLOB _materialx_render_slang_headers
     "${MATERIALX_SOURCE_DIR}/source/MaterialXRenderSlang/*.h")
file(COPY ${_materialx_render_slang_headers}
     DESTINATION "${MATERIALX_INSTALL_PREFIX}/include/MaterialXRenderSlang")

if(WIN32)
    file(MAKE_DIRECTORY "${MATERIALX_INSTALL_PREFIX}/bin")
    file(MAKE_DIRECTORY "${MATERIALX_INSTALL_PREFIX}/lib")
    file(GLOB_RECURSE _materialx_render_slang_runtime
         "${MATERIALX_BUILD_DIR}/MaterialXRenderSlang.dll")
    file(GLOB_RECURSE _materialx_render_slang_import
         "${MATERIALX_BUILD_DIR}/MaterialXRenderSlang.lib")
    file(COPY ${_materialx_render_slang_runtime}
         DESTINATION "${MATERIALX_INSTALL_PREFIX}/bin")
    file(COPY ${_materialx_render_slang_import}
         DESTINATION "${MATERIALX_INSTALL_PREFIX}/lib")
elseif(APPLE)
    file(MAKE_DIRECTORY "${MATERIALX_INSTALL_PREFIX}/lib")
    file(GLOB_RECURSE _materialx_render_slang_runtime
         "${MATERIALX_BUILD_DIR}/libMaterialXRenderSlang*.dylib")
    file(COPY ${_materialx_render_slang_runtime}
         DESTINATION "${MATERIALX_INSTALL_PREFIX}/lib")
else()
    file(MAKE_DIRECTORY "${MATERIALX_INSTALL_PREFIX}/lib")
    file(GLOB_RECURSE _materialx_render_slang_runtime
         "${MATERIALX_BUILD_DIR}/libMaterialXRenderSlang.so*")
    file(COPY ${_materialx_render_slang_runtime}
         DESTINATION "${MATERIALX_INSTALL_PREFIX}/lib")
endif()

if(NOT _materialx_render_slang_runtime)
    message(FATAL_ERROR "MaterialXRenderSlang runtime library was not found under ${MATERIALX_BUILD_DIR}")
endif()
