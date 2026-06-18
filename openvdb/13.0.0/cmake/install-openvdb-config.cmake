if(NOT DEFINED OPENVDB_CONFIG_PREFIX)
    message(FATAL_ERROR "OPENVDB_CONFIG_PREFIX is not set")
endif()

if(NOT DEFINED OPENVDB_CONFIG_VERSION)
    message(FATAL_ERROR "OPENVDB_CONFIG_VERSION is not set")
endif()

set(_openvdb_config_dir "${OPENVDB_CONFIG_PREFIX}/lib/cmake/OpenVDB")
file(MAKE_DIRECTORY "${_openvdb_config_dir}")

file(WRITE "${_openvdb_config_dir}/OpenVDBConfig.cmake" [=[
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")
include("${CMAKE_CURRENT_LIST_DIR}/FindOpenVDB.cmake")
]=])

file(WRITE "${_openvdb_config_dir}/OpenVDBConfigVersion.cmake" "set(PACKAGE_VERSION \"${OPENVDB_CONFIG_VERSION}\")\n\n")
file(APPEND "${_openvdb_config_dir}/OpenVDBConfigVersion.cmake" [=[
if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
    set(PACKAGE_VERSION_EXACT TRUE)
endif()

if(PACKAGE_FIND_VERSION VERSION_LESS_EQUAL PACKAGE_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
else()
    set(PACKAGE_VERSION_UNSUITABLE TRUE)
endif()
]=])
