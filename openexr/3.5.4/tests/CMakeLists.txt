cmake_minimum_required(VERSION 3.20)

project(openexr_consumer LANGUAGES C CXX)

option(OPENEXR_CONSUMER_EXPECT_FULL "Require the full OpenEXR C++ package" OFF)
find_package(OpenEXRCore CONFIG REQUIRED)

add_executable(openexr_core_consumer openexr_core_consumer.c)
target_link_libraries(openexr_core_consumer PRIVATE OpenEXRCore::OpenEXRCore)
add_custom_target(run_openexr_core_consumer ALL
  COMMAND openexr_core_consumer
  DEPENDS openexr_core_consumer
)

find_package(OpenEXR CONFIG QUIET)

if(TARGET OpenEXR::OpenEXR)
  add_executable(openexr_cpp_consumer openexr_cpp_consumer.cpp)
  target_link_libraries(openexr_cpp_consumer PRIVATE OpenEXR::OpenEXR)
  add_custom_target(run_openexr_cpp_consumer ALL
    COMMAND openexr_cpp_consumer
    DEPENDS openexr_cpp_consumer
  )
elseif(OPENEXR_CONSUMER_EXPECT_FULL)
  message(FATAL_ERROR "Expected full OpenEXR C++ package metadata, but OpenEXR::OpenEXR was not found")
endif()
