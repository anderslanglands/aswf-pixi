if(NOT DEFINED PARTIO_CONFIG_PREFIX)
  message(FATAL_ERROR "PARTIO_CONFIG_PREFIX is required")
endif()

set(_partio_config "${PARTIO_CONFIG_PREFIX}/lib/cmake/Partio/PartioConfig.cmake")
if(NOT EXISTS "${_partio_config}")
  return()
endif()

file(READ "${_partio_config}" _partio_config_contents)
string(FIND "${_partio_config_contents}" "partio::partio" _partio_alias_pos)
if(_partio_alias_pos EQUAL -1)
  file(APPEND "${_partio_config}" [=[

if(TARGET Partio::partio AND NOT TARGET partio::partio)
  add_library(partio::partio INTERFACE IMPORTED)
  target_link_libraries(partio::partio INTERFACE Partio::partio)
endif()

set(partio_FOUND TRUE)
]=])
endif()
