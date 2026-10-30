cmake_minimum_required(VERSION 3.19)
project(openshadinglanguage_consumer LANGUAGES CXX)

find_package(OSL REQUIRED)

add_executable(openshadinglanguage_consumer openshadinglanguage_consumer.cpp)
target_link_libraries(openshadinglanguage_consumer PRIVATE
    OSL::oslquery
    OSL::oslexec)
target_compile_features(openshadinglanguage_consumer PRIVATE cxx_std_17)
