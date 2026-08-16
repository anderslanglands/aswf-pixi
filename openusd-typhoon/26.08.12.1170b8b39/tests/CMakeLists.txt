cmake_minimum_required(VERSION 3.20)
project(openusd_consumer LANGUAGES CXX)

find_package(pxr REQUIRED CONFIG)
if(NOT TARGET usdMtlx)
    message(FATAL_ERROR "OpenUSD pxr config did not export the usdMtlx target")
endif()

add_executable(openusd_consumer openusd_consumer.cpp)
target_link_libraries(openusd_consumer PRIVATE usd usdMtlx)
target_compile_features(openusd_consumer PRIVATE cxx_std_17)

enable_testing()
add_test(NAME openusd_consumer COMMAND openusd_consumer)
