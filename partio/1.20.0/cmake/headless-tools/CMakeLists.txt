cmake_minimum_required(VERSION 3.15)
project(partio_headless_tools LANGUAGES CXX)

include(GNUInstallDirs)

if(NOT DEFINED PARTIO_SOURCE_DIR)
  message(FATAL_ERROR "PARTIO_SOURCE_DIR is required")
endif()

find_package(ZLIB REQUIRED)

find_library(PARTIO_LIBRARY
  NAMES partio
  REQUIRED
)

foreach(tool IN ITEMS partattr partconvert partinfo)
  add_executable(${tool} "${PARTIO_SOURCE_DIR}/src/tools/${tool}.cpp")
  target_compile_features(${tool} PRIVATE cxx_std_17)
  target_include_directories(${tool} PRIVATE "${PARTIO_SOURCE_DIR}/src/lib")
  target_link_libraries(${tool} PRIVATE "${PARTIO_LIBRARY}" ZLIB::ZLIB)
  install(TARGETS ${tool} RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
endforeach()
