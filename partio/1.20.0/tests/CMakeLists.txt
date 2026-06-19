cmake_minimum_required(VERSION 3.15)
project(partio_consumer LANGUAGES CXX)

enable_testing()

find_package(Partio REQUIRED)

add_executable(partio_consumer partio_consumer.cpp)
target_compile_features(partio_consumer PRIVATE cxx_std_17)
target_link_libraries(partio_consumer PRIVATE Partio::partio)

add_test(NAME partio_consumer COMMAND partio_consumer)
