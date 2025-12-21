#!/bin/bash
set -ex
rm -rf cpp/build
cmake -S cpp -B cpp/build
cmake --build cpp/build
cp cpp/build/cpp_boggle*.so .