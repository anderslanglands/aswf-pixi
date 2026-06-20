if(NOT DEFINED OSL_PARTIO_PREFIX OR OSL_PARTIO_PREFIX STREQUAL "")
  message(FATAL_ERROR "OSL_PARTIO_PREFIX is required")
endif()

set(_partio_config "${OSL_PARTIO_PREFIX}/lib/cmake/Partio/PartioConfig.cmake")
if(NOT EXISTS "${_partio_config}")
  message(FATAL_ERROR "PartioConfig.cmake not found at ${_partio_config}")
endif()

file(READ "${_partio_config}" _partio_config_contents)
if(_partio_config_contents MATCHES "partio::partio")
  return()
endif()

file(APPEND "${_partio_config}" [=[

if(TARGET Partio::partio AND NOT TARGET partio::partio)
  add_library(partio::partio INTERFACE IMPORTED)
  set_target_properties(partio::partio PROPERTIES
    INTERFACE_LINK_LIBRARIES Partio::partio
  )
endif()
]=])
