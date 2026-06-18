cmake_minimum_required(VERSION 3.18)
project(OpenImageIOConsumer LANGUAGES CXX)

set(OPENIMAGEIO_EXPECTED_VERSION "3.0.19.1" CACHE STRING "Expected OpenImageIO version")
find_package(OpenImageIO ${OPENIMAGEIO_EXPECTED_VERSION} EXACT CONFIG REQUIRED)

add_executable(openimageio_consumer openimageio_consumer.cpp)
target_compile_definitions(
  openimageio_consumer
  PRIVATE OPENIMAGEIO_EXPECTED_VERSION="${OPENIMAGEIO_EXPECTED_VERSION}"
)
target_link_libraries(
  openimageio_consumer
  PRIVATE OpenImageIO::OpenImageIO OpenImageIO::OpenImageIO_Util
)
