#!/bin/bash
set -o errexit

cd cpp
c++ -O3 -Wall -shared -std=c++20 -fPIC \
    $(poetry run python -m pybind11 --includes) \
    cpp_boggle.cc trie.cc boggler.cc eval_node.cc \
    -o ../cpp_boggle$(python3-config --extension-suffix) \
    -undefined dynamic_lookup
