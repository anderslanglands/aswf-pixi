cmake_minimum_required(VERSION 3.20)

project(libuhdr_consumer LANGUAGES CXX)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBUHDR REQUIRED IMPORTED_TARGET libuhdr)

add_executable(libuhdr_consumer libuhdr_consumer.cpp)
target_compile_features(libuhdr_consumer PRIVATE cxx_std_17)
target_link_libraries(libuhdr_consumer PRIVATE PkgConfig::LIBUHDR)
