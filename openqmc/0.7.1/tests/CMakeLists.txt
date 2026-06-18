cmake_minimum_required(VERSION 3.15)

project(openqmc_consumer LANGUAGES CXX)

option(OPENQMC_CONSUMER_EXPECT_HEADER_ONLY "Expect the header-only OpenQMC package flavor." OFF)

find_package(OpenQMC 0.7.1 CONFIG REQUIRED)

get_target_property(_openqmc_definitions OpenQMC::OpenQMC INTERFACE_COMPILE_DEFINITIONS)
if(NOT _openqmc_definitions)
    set(_openqmc_definitions)
endif()

if(OPENQMC_CONSUMER_EXPECT_HEADER_ONLY)
    if("OQMC_ENABLE_BINARY" IN_LIST _openqmc_definitions)
        message(FATAL_ERROR "Expected header-only OpenQMC target, but OQMC_ENABLE_BINARY is defined.")
    endif()
    if("OQMC_SHARED_LIBRARY" IN_LIST _openqmc_definitions)
        message(FATAL_ERROR "Expected header-only OpenQMC target, but OQMC_SHARED_LIBRARY is defined.")
    endif()
else()
    if(NOT "OQMC_ENABLE_BINARY" IN_LIST _openqmc_definitions)
        message(FATAL_ERROR "Expected binary OpenQMC target, but OQMC_ENABLE_BINARY is not defined.")
    endif()
    if(WIN32 AND NOT "OQMC_SHARED_LIBRARY" IN_LIST _openqmc_definitions)
        message(FATAL_ERROR "Expected Windows shared OpenQMC target, but OQMC_SHARED_LIBRARY is not defined.")
    endif()
endif()

add_executable(openqmc_consumer openqmc_consumer.cpp)
target_link_libraries(openqmc_consumer PRIVATE OpenQMC::OpenQMC)

enable_testing()
add_test(NAME openqmc_consumer COMMAND openqmc_consumer)
