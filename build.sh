#!/bin/bash
set -o errexit

cd cpp
c++ -Wall -shared -std=c++20 -fPIC -march=native \
    -Wno-sign-compare \
    -O3 \
    $(poetry run python -m pybind11 --includes) \
    cpp_boggle.cc trie.cc eval_node.cc \
    -o ../cpp_boggle$(python3-config --extension-suffix) \
    -undefined dynamic_lookup

# TODO: fix the sign-compare warnings
# For sampling profiling:
#     -g

# For instrumented profiling (instruction counts):
# -fprofile-instr-generate -fcoverage-mapping
