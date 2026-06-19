cmake_minimum_required(VERSION 3.15)
project(seexpr_consumer LANGUAGES CXX)

find_package(seexpr2 CONFIG REQUIRED)
find_package(Threads REQUIRED)

find_library(
    SEEXPR2_LIBRARY
    NAMES SeExpr2
    PATHS "${SeExpr2_LIBRARY_DIRS}"
    REQUIRED
    NO_DEFAULT_PATH
)

add_executable(seexpr_consumer seexpr_consumer.cpp)
target_compile_features(seexpr_consumer PRIVATE cxx_std_11)
target_include_directories(seexpr_consumer PRIVATE "${SeExpr2_INCLUDE_DIRS}")
target_link_libraries(seexpr_consumer PRIVATE "${SEEXPR2_LIBRARY}" Threads::Threads ${CMAKE_DL_LIBS})
