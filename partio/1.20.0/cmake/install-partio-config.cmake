if(NOT DEFINED PARTIO_CONFIG_PREFIX)
  message(FATAL_ERROR "PARTIO_CONFIG_PREFIX is required")
endif()

if(NOT DEFINED PARTIO_CONFIG_VERSION)
  message(FATAL_ERROR "PARTIO_CONFIG_VERSION is required")
endif()

set(_config_dir "${PARTIO_CONFIG_PREFIX}/lib/cmake/Partio")
set(_lower_config_dir "${PARTIO_CONFIG_PREFIX}/lib/cmake/partio")
file(MAKE_DIRECTORY "${_config_dir}" "${_lower_config_dir}")

file(WRITE "${_config_dir}/PartioConfig.cmake" [=[
include(CMakeFindDependencyMacro)

find_dependency(ZLIB)

get_filename_component(_PARTIO_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

if(NOT TARGET Partio::partio)
  add_library(Partio::partio SHARED IMPORTED)
  set_target_properties(Partio::partio PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_PARTIO_PREFIX}/include"
    INTERFACE_LINK_LIBRARIES "ZLIB::ZLIB"
  )

  if(WIN32)
    set_target_properties(Partio::partio PROPERTIES
      IMPORTED_IMPLIB "${_PARTIO_PREFIX}/lib/partio.lib"
      IMPORTED_LOCATION "${_PARTIO_PREFIX}/bin/partio.dll"
    )
  elseif(APPLE)
    set_target_properties(Partio::partio PROPERTIES
      IMPORTED_LOCATION "${_PARTIO_PREFIX}/lib/libpartio.dylib"
    )
  else()
    set_target_properties(Partio::partio PROPERTIES
      IMPORTED_LOCATION "${_PARTIO_PREFIX}/lib/libpartio.so"
    )
  endif()
endif()

if(TARGET Partio::partio AND NOT TARGET partio::partio)
  add_library(partio::partio INTERFACE IMPORTED)
  target_link_libraries(partio::partio INTERFACE Partio::partio)
endif()

set(Partio_FOUND TRUE)
set(partio_FOUND TRUE)
]=])

file(WRITE "${_config_dir}/PartioConfigVersion.cmake" "set(PACKAGE_VERSION \"${PARTIO_CONFIG_VERSION}\")\n\n")
file(APPEND "${_config_dir}/PartioConfigVersion.cmake" [=[
if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
  set(PACKAGE_VERSION_EXACT TRUE)
endif()

if(PACKAGE_FIND_VERSION VERSION_LESS PACKAGE_VERSION OR PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
  set(PACKAGE_VERSION_COMPATIBLE TRUE)
else()
  set(PACKAGE_VERSION_UNSUITABLE TRUE)
endif()
]=])

foreach(_alias_dir IN ITEMS "${_config_dir}" "${_lower_config_dir}")
  file(WRITE "${_alias_dir}/partio-config.cmake" [=[
include("${CMAKE_CURRENT_LIST_DIR}/../Partio/PartioConfig.cmake")
]=])
  file(WRITE "${_alias_dir}/partio-config-version.cmake" [=[
include("${CMAKE_CURRENT_LIST_DIR}/../Partio/PartioConfigVersion.cmake")
]=])
endforeach()
