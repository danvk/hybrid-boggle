#!/bin/bash
# For a full rebuild, rm -rf cpp/build before running this.
set -ex
cmake -S cpp -B cpp/build
cmake --build cpp/build
cp cpp/build/cpp_boggle*.so .
