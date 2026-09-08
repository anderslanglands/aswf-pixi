if(NOT DEFINED ZSTD_LIB_DIR)
  message(FATAL_ERROR "ZSTD_LIB_DIR is required")
endif()

set(_zstd_implib "${ZSTD_LIB_DIR}/zstd.lib")
set(_llvm_zstd_implib "${ZSTD_LIB_DIR}/zstd.dll.lib")

if(EXISTS "${_zstd_implib}" AND NOT EXISTS "${_llvm_zstd_implib}")
  file(COPY_FILE "${_zstd_implib}" "${_llvm_zstd_implib}" ONLY_IF_DIFFERENT)
endif()
