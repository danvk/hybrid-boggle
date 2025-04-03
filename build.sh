#!/bin/bash

c++ --version | grep Apple > /dev/null
if [[ $? == 0 ]]; then
    EXTRA_FLAGS="-undefined dynamic_lookup"
else
    EXTRA_FLAGS=""
fi

set -o errexit
cd cpp
c++ -Wall -shared -std=c++20 -fPIC -march=native \
    -Wno-sign-compare \
    -Wshadow \
    -O3 \
    $(poetry run python -m pybind11 --includes) \
    cpp_boggle.cc trie.cc eval_node.cc \
    -o ../cpp_boggle$(python3-config --extension-suffix) \
    $EXTRA_FLAGS

c++ -Wall -std=c++20 -march=native -Wno-sign-compare -Wshadow cli.cc trie.cc -o boggle_cli

# TODO: fix the sign-compare warnings
# For sampling profiling:
#     -g

# For instrumented profiling (instruction counts):
# -fprofile-instr-generate -fcoverage-mapping
