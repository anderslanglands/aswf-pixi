if(NOT DEFINED OPENSD_CONFIG)
  message(FATAL_ERROR "OPENSD_CONFIG is required")
endif()

if(NOT EXISTS "${OPENSD_CONFIG}")
  message(FATAL_ERROR "OpenSubdiv config does not exist: ${OPENSD_CONFIG}")
endif()

file(READ "${OPENSD_CONFIG}" _opensubdiv_config_contents)
set(_opensubdiv_targets [[include("${CMAKE_CURRENT_LIST_DIR}/OpenSubdivTargets.cmake")]])

set(_opensubdiv_injected "include(CMakeFindDependencyMacro)\n")
foreach(_opensubdiv_dep IN LISTS OPENSD_FIND_DEPENDENCIES)
  string(APPEND _opensubdiv_injected "find_dependency(${_opensubdiv_dep})\n")
endforeach()
if(OPENSD_FIND_CUDART)
  # CUDA-enabled consumers need the runtime headers/library, not nvcc. The
  # conda cudart development package has no toolkit version.json, so CMake's
  # FindCUDAToolkit cannot discover it without installing the CUDA compiler.
  string(APPEND _opensubdiv_injected [=[
if(NOT TARGET CUDA::cudart)
  get_filename_component(_opensubdiv_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
  find_library(_opensubdiv_cudart NAMES cudart
    PATHS "${_opensubdiv_prefix}/lib" "${_opensubdiv_prefix}/targets/x86_64-linux/lib"
    NO_DEFAULT_PATH REQUIRED)
  find_path(_opensubdiv_cuda_include cuda_runtime.h
    PATHS "${_opensubdiv_prefix}/include" "${_opensubdiv_prefix}/include/targets/x64"
          "${_opensubdiv_prefix}/targets/x86_64-linux/include"
    NO_DEFAULT_PATH REQUIRED)
  set(_opensubdiv_cuda_includes "${_opensubdiv_cuda_include}")
  foreach(_opensubdiv_cuda_suffix IN ITEMS include include/targets/x64 include/targets/x64/cccl
                                         targets/x86_64-linux/include targets/x86_64-linux/include/cccl)
    if(IS_DIRECTORY "${_opensubdiv_prefix}/${_opensubdiv_cuda_suffix}")
      list(APPEND _opensubdiv_cuda_includes "${_opensubdiv_prefix}/${_opensubdiv_cuda_suffix}")
    endif()
  endforeach()
  list(REMOVE_DUPLICATES _opensubdiv_cuda_includes)
  add_library(CUDA::cudart UNKNOWN IMPORTED)
  set_target_properties(CUDA::cudart PROPERTIES
    IMPORTED_LOCATION "${_opensubdiv_cudart}"
    INTERFACE_INCLUDE_DIRECTORIES "${_opensubdiv_cuda_includes}")
endif()
]=])
endif()
string(APPEND _opensubdiv_injected "${_opensubdiv_targets}\n")

if(DEFINED OPENSD_TARGET_DEFINITIONS AND NOT OPENSD_TARGET_DEFINITIONS STREQUAL "")
  string(APPEND _opensubdiv_injected "foreach(_opensubdiv_gpu_target IN ITEMS OpenSubdiv::osdGPU OpenSubdiv::osdGPU_static)\n")
  string(APPEND _opensubdiv_injected "  if(TARGET \${_opensubdiv_gpu_target})\n")
  string(APPEND _opensubdiv_injected "    target_compile_definitions(\${_opensubdiv_gpu_target} INTERFACE ${OPENSD_TARGET_DEFINITIONS})\n")
  string(APPEND _opensubdiv_injected "  endif()\n")
  string(APPEND _opensubdiv_injected "endforeach()\n")
endif()

string(REPLACE "${_opensubdiv_targets}" "${_opensubdiv_injected}" _opensubdiv_patched_contents "${_opensubdiv_config_contents}")
if(_opensubdiv_patched_contents STREQUAL _opensubdiv_config_contents)
  message(FATAL_ERROR "Failed to patch OpenSubdiv target include in ${OPENSD_CONFIG}")
endif()
file(WRITE "${OPENSD_CONFIG}" "${_opensubdiv_patched_contents}")
