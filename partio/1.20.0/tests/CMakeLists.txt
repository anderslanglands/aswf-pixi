cmake_minimum_required(VERSION 3.15)
project(partio_consumer LANGUAGES CXX)

enable_testing()

find_package(partio 1.20.0 CONFIG REQUIRED)

foreach(partio_target IN ITEMS Partio::partio partio::partio)
    if(NOT TARGET ${partio_target})
        message(FATAL_ERROR "Expected ${partio_target} to be exported by partio config package")
    endif()
endforeach()

add_executable(partio_consumer partio_consumer.cpp)
target_compile_features(partio_consumer PRIVATE cxx_std_17)
target_link_libraries(partio_consumer PRIVATE partio::partio)

add_test(NAME partio_consumer COMMAND partio_consumer)
