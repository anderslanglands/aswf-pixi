cmake_minimum_required(VERSION 3.15)

project(imath_consumer LANGUAGES CXX)

find_package(Imath CONFIG REQUIRED)

add_executable(imath_consumer imath_consumer.cpp)
target_link_libraries(imath_consumer PRIVATE Imath::Imath)
