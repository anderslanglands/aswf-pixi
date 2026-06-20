cmake_minimum_required(VERSION 3.20)

project(openexr_consumer LANGUAGES C CXX)

option(OPENEXR_CONSUMER_EXPECT_FULL "Require the full OpenEXR C++ package" OFF)
set(OPENEXR_CONSUMER_EXPECT_VERSION "" CACHE STRING "Expected OpenEXR runtime version")

if(NOT OPENEXR_CONSUMER_EXPECT_VERSION MATCHES "^([0-9]+)[.]([0-9]+)[.]([0-9]+)$")
  message(FATAL_ERROR "OPENEXR_CONSUMER_EXPECT_VERSION must be set to MAJOR.MINOR.PATCH")
endif()

set(_openexr_expected_major "${CMAKE_MATCH_1}")
set(_openexr_expected_minor "${CMAKE_MATCH_2}")
set(_openexr_expected_patch "${CMAKE_MATCH_3}")

find_package(OpenEXRCore ${OPENEXR_CONSUMER_EXPECT_VERSION} CONFIG REQUIRED)

add_executable(openexr_core_consumer openexr_core_consumer.c)
target_compile_definitions(openexr_core_consumer PRIVATE
  OPENEXR_CONSUMER_EXPECT_MAJOR=${_openexr_expected_major}
  OPENEXR_CONSUMER_EXPECT_MINOR=${_openexr_expected_minor}
  OPENEXR_CONSUMER_EXPECT_PATCH=${_openexr_expected_patch}
)
target_link_libraries(openexr_core_consumer PRIVATE OpenEXRCore::OpenEXRCore)
add_custom_target(run_openexr_core_consumer ALL
  COMMAND openexr_core_consumer
  DEPENDS openexr_core_consumer
)

find_package(OpenEXR ${OPENEXR_CONSUMER_EXPECT_VERSION} CONFIG QUIET)

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
