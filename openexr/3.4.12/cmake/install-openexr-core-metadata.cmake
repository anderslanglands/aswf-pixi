if(NOT DEFINED OPENEXR_CORE_METADATA_PREFIX)
  message(FATAL_ERROR "OPENEXR_CORE_METADATA_PREFIX is required")
endif()

set(_prefix "${OPENEXR_CORE_METADATA_PREFIX}")
set(_version "3.4.12")
set(_api_suffix "-3_4")

file(MAKE_DIRECTORY "${_prefix}/lib/cmake/OpenEXRCore")
file(MAKE_DIRECTORY "${_prefix}/lib/pkgconfig")

file(WRITE "${_prefix}/lib/cmake/OpenEXRCore/OpenEXRCoreConfig.cmake" [=[
include(CMakeFindDependencyMacro)

find_dependency(Imath)

get_filename_component(_OPENEXRCORE_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

if(NOT TARGET OpenEXRCore::OpenEXRCore)
  add_library(OpenEXRCore::OpenEXRCore SHARED IMPORTED)
  set_target_properties(OpenEXRCore::OpenEXRCore PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_OPENEXRCORE_PREFIX}/include;${_OPENEXRCORE_PREFIX}/include/OpenEXR"
    INTERFACE_LINK_LIBRARIES "Imath::Imath"
  )

  if(WIN32)
    set_target_properties(OpenEXRCore::OpenEXRCore PROPERTIES
      IMPORTED_IMPLIB "${_OPENEXRCORE_PREFIX}/lib/OpenEXRCore-3_4.lib"
      IMPORTED_LOCATION "${_OPENEXRCORE_PREFIX}/bin/OpenEXRCore-3_4.dll"
      INTERFACE_COMPILE_DEFINITIONS "OPENEXR_DLL"
    )
  elseif(APPLE)
    set_target_properties(OpenEXRCore::OpenEXRCore PROPERTIES
      IMPORTED_LOCATION "${_OPENEXRCORE_PREFIX}/lib/libOpenEXRCore-3_4.dylib"
    )
  else()
    set_target_properties(OpenEXRCore::OpenEXRCore PROPERTIES
      IMPORTED_LOCATION "${_OPENEXRCORE_PREFIX}/lib/libOpenEXRCore-3_4.so"
    )
  endif()
endif()

set(OpenEXRCore_FOUND TRUE)
]=])

file(WRITE "${_prefix}/lib/cmake/OpenEXRCore/OpenEXRCoreConfigVersion.cmake" "set(PACKAGE_VERSION \"${_version}\")

if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
  set(PACKAGE_VERSION_EXACT TRUE)
endif()

if(PACKAGE_FIND_VERSION VERSION_LESS PACKAGE_VERSION OR PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
  set(PACKAGE_VERSION_COMPATIBLE TRUE)
endif()
")

file(WRITE "${_prefix}/lib/pkgconfig/OpenEXRCore.pc" "prefix=\${pcfiledir}/../..
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include
OpenEXR_includedir=\${includedir}/OpenEXR

Name: OpenEXRCore
Description: OpenEXR C core library
Version: ${_version}

Libs: -L\${libdir} -lOpenEXRCore${_api_suffix}
Cflags: -I\${includedir} -I\${OpenEXR_includedir}
Requires: Imath
")
