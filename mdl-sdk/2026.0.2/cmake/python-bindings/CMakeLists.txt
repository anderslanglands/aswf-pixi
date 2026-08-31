cmake_minimum_required(VERSION 3.20)

project(mdl_sdk_python_bindings LANGUAGES CXX)

set(MDL_SDK_SOURCE_DIR "" CACHE PATH "Path to the unpacked MDL SDK source tree")
set(MDL_PYTHON_INSTALL_DIR "" CACHE PATH "Directory where Python modules are installed")

if(NOT MDL_SDK_SOURCE_DIR)
    message(FATAL_ERROR "MDL_SDK_SOURCE_DIR is required")
endif()
if(NOT MDL_PYTHON_INSTALL_DIR)
    message(FATAL_ERROR "MDL_PYTHON_INSTALL_DIR is required")
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
find_program(SWIG_EXECUTABLE NAMES swig REQUIRED)

set(_binding_dir "${MDL_SDK_SOURCE_DIR}/src/prod/bindings/mdl_python")
set(_include_dir "${MDL_SDK_SOURCE_DIR}/include")
set(_shared_dir "${MDL_SDK_SOURCE_DIR}/examples/mdl_sdk/shared")
set(_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(_python_out_dir "${CMAKE_CURRENT_BINARY_DIR}/python")

execute_process(
    COMMAND "${Python3_EXECUTABLE}"
        -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX') or '.pyd')"
    OUTPUT_VARIABLE _python_ext_suffix
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)

file(MAKE_DIRECTORY
    "${_generated_dir}/processed_headers"
    "${_python_out_dir}"
)

file(GLOB_RECURSE _mdl_headers
    LIST_DIRECTORIES false
    CONFIGURE_DEPENDS
    "${_include_dir}/*.h"
)

add_custom_command(
    OUTPUT "${_generated_dir}/processed_headers.d"
    COMMAND "${Python3_EXECUTABLE}"
        "${_binding_dir}/instantiate_templates_inline.py"
        "${_binding_dir}/mdl_python_swig.i"
        ""
        "${_include_dir}"
        "${_generated_dir}/processed_headers"
        "${_generated_dir}/processed_headers.d"
    DEPENDS
        "${_binding_dir}/instantiate_templates_inline.py"
        "${_binding_dir}/mdl_python_swig.i"
        ${_mdl_headers}
    VERBATIM
)

add_custom_command(
    OUTPUT
        "${_generated_dir}/mdl_python_swig.cpp"
        "${_python_out_dir}/pymdlsdk.py"
    COMMAND "${SWIG_EXECUTABLE}"
        -c++ -python -doxygen
        -w564
        -DSWIGWORDSIZE64
        -I-
        "-I${_binding_dir}"
        "-I${_generated_dir}/processed_headers"
        "-I${_binding_dir}/swig_library"
        "-I${_include_dir}"
        -MMD -MP -MF "${_generated_dir}/mdl_python_swig.cpp.tmp.d"
        -cppext cpp
        -o "${_generated_dir}/mdl_python_swig.cpp"
        -outdir "${_python_out_dir}"
        -module pymdlsdk
        "${_binding_dir}/mdl_python_swig.i"
    COMMAND "${Python3_EXECUTABLE}"
        "${_binding_dir}/post_swig.py"
        -outdir "${_python_out_dir}"
        -module pymdlsdk
    DEPENDS
        "${_generated_dir}/processed_headers.d"
        "${_binding_dir}/mdl_python_swig.i"
        "${_binding_dir}/swig_library/mi_neuraylib_deprecated.i"
        "${_binding_dir}/swig_library/mi_neuraylib_enums.i"
        "${_binding_dir}/post_swig.py"
    VERBATIM
)

add_library(_pymdlsdk MODULE
    "${_binding_dir}/mdl_python.cpp"
    "${_binding_dir}/mdl_python.h"
    "${_generated_dir}/mdl_python_swig.cpp"
)

target_compile_features(_pymdlsdk PRIVATE cxx_std_17)
if(MSVC)
    target_compile_options(_pymdlsdk PRIVATE /bigobj)
endif()
target_include_directories(_pymdlsdk PRIVATE
    "${_binding_dir}"
    "${_include_dir}"
    "${_shared_dir}"
)
target_link_libraries(_pymdlsdk PRIVATE Python3::Module ${CMAKE_DL_LIBS})
set_target_properties(_pymdlsdk PROPERTIES
    PREFIX ""
    OUTPUT_NAME "_pymdlsdk"
    SUFFIX "${_python_ext_suffix}"
    LIBRARY_OUTPUT_DIRECTORY "${_python_out_dir}"
    RUNTIME_OUTPUT_DIRECTORY "${_python_out_dir}"
)

install(
    FILES
        "${_binding_dir}/pymdl.py"
        "${_python_out_dir}/pymdlsdk.py"
    DESTINATION "${MDL_PYTHON_INSTALL_DIR}"
)
install(
    TARGETS _pymdlsdk
    LIBRARY DESTINATION "${MDL_PYTHON_INSTALL_DIR}"
    RUNTIME DESTINATION "${MDL_PYTHON_INSTALL_DIR}"
)
