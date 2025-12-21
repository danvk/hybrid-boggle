cmake_minimum_required(VERSION 3.14)
project(cpp_boggle)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wno-sign-compare -Wshadow -Werror -O3 -march=native")

# On macOS, we need to add this flag to support python modules.
if(APPLE)
  set(CMAKE_SHARED_LINKER_FLAGS "-undefined dynamic_lookup")
endif()

# Abseil
include(FetchContent)
FetchContent_Declare(
  abseil-cpp
  GIT_REPOSITORY https://github.com/abseil/abseil-cpp.git
  GIT_TAG 20230125.3
)
set(ABSL_PROPAGATE_CXX_STD ON)
FetchContent_MakeAvailable(abseil-cpp)

FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG v2.10.0
)
FetchContent_MakeAvailable(pybind11)

find_package(Python REQUIRED)

pybind11_add_module(cpp_boggle
    cpp_boggle.cc
    trie.cc
    arena.cc
    eval_node.cc
    symmetry.cc
)

target_link_libraries(cpp_boggle PRIVATE absl::hash absl::flat_hash_set)
