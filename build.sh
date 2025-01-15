#!/bin/bash
set -o errexit

cd cpp
c++ -Wall -shared -std=c++20 -fPIC \
    -O3 \
    $(poetry run python -m pybind11 --includes) \
    cpp_boggle.cc trie.cc boggler.cc eval_node.cc \
    -o ../cpp_boggle$(python3-config --extension-suffix) \
    -undefined dynamic_lookup
