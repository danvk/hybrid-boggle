#!/bin/bash
set -o errexit

emcc \
    -lembind \
    -sALLOW_MEMORY_GROWTH \
    -sEXPORTED_FUNCTIONS=FS \
    -sFORCE_FILESYSTEM=1 \
    -o wasm/boggle.js \
    --emit-tsd boggle.d.ts \
    cpp/wasm_boggle.cc cpp/trie.cc
