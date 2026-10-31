cmake_minimum_required(VERSION 3.20)
project(opensubdiv_consumer LANGUAGES CXX)

find_package(OpenSubdiv CONFIG REQUIRED)

set(OPENSUBDIV_CPU_TARGET "")
if(TARGET OpenSubdiv::osdCPU)
  set(OPENSUBDIV_CPU_TARGET OpenSubdiv::osdCPU)
elseif(TARGET OpenSubdiv::osdCPU_static)
  set(OPENSUBDIV_CPU_TARGET OpenSubdiv::osdCPU_static)
else()
  message(FATAL_ERROR "OpenSubdiv CPU target was not exported")
endif()

if(OPENSUBDIV_CONSUMER_EXPECT_CPU_ONLY)
  if(TARGET OpenSubdiv::osdGPU OR TARGET OpenSubdiv::osdGPU_static)
    message(FATAL_ERROR "CPU-only OpenSubdiv package unexpectedly exports a GPU target")
  endif()
endif()

set(OPENSUBDIV_GPU_TARGET "")
if(TARGET OpenSubdiv::osdGPU)
  set(OPENSUBDIV_GPU_TARGET OpenSubdiv::osdGPU)
elseif(TARGET OpenSubdiv::osdGPU_static)
  set(OPENSUBDIV_GPU_TARGET OpenSubdiv::osdGPU_static)
endif()

if(OPENSUBDIV_CONSUMER_REQUIRE_GPU AND NOT OPENSUBDIV_GPU_TARGET)
  message(FATAL_ERROR "GPU OpenSubdiv package did not export a GPU target")
endif()

set(OPENSUBDIV_LINK_TARGETS ${OPENSUBDIV_CPU_TARGET})
if(OPENSUBDIV_CONSUMER_REQUIRE_GPU)
  list(APPEND OPENSUBDIV_LINK_TARGETS ${OPENSUBDIV_GPU_TARGET})
endif()

if(OPENSUBDIV_GPU_TARGET)
  get_target_property(OPENSUBDIV_GPU_DEFINES ${OPENSUBDIV_GPU_TARGET} INTERFACE_COMPILE_DEFINITIONS)
  if(NOT OPENSUBDIV_GPU_DEFINES)
    set(OPENSUBDIV_GPU_DEFINES "")
  endif()

  if(OPENSUBDIV_CONSUMER_REQUIRE_CUDA AND NOT "OPENSUBDIV_HAS_CUDA" IN_LIST OPENSUBDIV_GPU_DEFINES)
    message(FATAL_ERROR "GPU OpenSubdiv target is missing OPENSUBDIV_HAS_CUDA")
  endif()

  if(OPENSUBDIV_CONSUMER_REQUIRE_METAL AND NOT "OPENSUBDIV_HAS_METAL" IN_LIST OPENSUBDIV_GPU_DEFINES)
    message(FATAL_ERROR "GPU OpenSubdiv target is missing OPENSUBDIV_HAS_METAL")
  endif()

  if(OPENSUBDIV_CONSUMER_REQUIRE_OPENGL AND NOT "OPENSUBDIV_HAS_OPENGL" IN_LIST OPENSUBDIV_GPU_DEFINES)
    message(FATAL_ERROR "GPU OpenSubdiv target is missing OPENSUBDIV_HAS_OPENGL")
  endif()

  if(OPENSUBDIV_CONSUMER_REQUIRE_TBB AND NOT "OPENSUBDIV_HAS_TBB" IN_LIST OPENSUBDIV_GPU_DEFINES)
    message(FATAL_ERROR "GPU OpenSubdiv target is missing OPENSUBDIV_HAS_TBB")
  endif()

  if(OPENSUBDIV_CONSUMER_FORBID_CUDA AND "OPENSUBDIV_HAS_CUDA" IN_LIST OPENSUBDIV_GPU_DEFINES)
    message(FATAL_ERROR "GPU OpenSubdiv target unexpectedly has OPENSUBDIV_HAS_CUDA")
  endif()

  if(OPENSUBDIV_CONSUMER_FORBID_METAL AND "OPENSUBDIV_HAS_METAL" IN_LIST OPENSUBDIV_GPU_DEFINES)
    message(FATAL_ERROR "GPU OpenSubdiv target unexpectedly has OPENSUBDIV_HAS_METAL")
  endif()
endif()

add_executable(opensubdiv_consumer opensubdiv_consumer.cpp)
target_compile_features(opensubdiv_consumer PRIVATE cxx_std_14)
target_link_libraries(opensubdiv_consumer PRIVATE ${OPENSUBDIV_LINK_TARGETS})

foreach(_opensubdiv_consumer_feature IN ITEMS GPU CUDA OPENGL METAL TBB)
  if(OPENSUBDIV_CONSUMER_REQUIRE_${_opensubdiv_consumer_feature})
    target_compile_definitions(opensubdiv_consumer PRIVATE OPENSUBDIV_CONSUMER_REQUIRE_${_opensubdiv_consumer_feature}=1)
  endif()
endforeach()

if(OPENSUBDIV_CONSUMER_REQUIRE_METAL)
  enable_language(OBJCXX)
  add_library(opensubdiv_metal_header_check OBJECT opensubdiv_metal_consumer.mm)
  set_target_properties(opensubdiv_metal_header_check PROPERTIES OBJCXX_STANDARD 14 OBJCXX_STANDARD_REQUIRED YES)
  target_link_libraries(opensubdiv_metal_header_check PRIVATE ${OPENSUBDIV_LINK_TARGETS})
endif()

enable_testing()
add_test(NAME opensubdiv_consumer COMMAND opensubdiv_consumer)
