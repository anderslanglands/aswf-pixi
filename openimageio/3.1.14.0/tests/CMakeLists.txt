cmake_minimum_required(VERSION 3.18)
project(OpenImageIOConsumer LANGUAGES CXX)

find_package(OpenImageIO 3.1.14.0 CONFIG REQUIRED)

add_executable(openimageio_consumer openimageio_consumer.cpp)
target_link_libraries(
  openimageio_consumer
  PRIVATE OpenImageIO::OpenImageIO OpenImageIO::OpenImageIO_Util
)
