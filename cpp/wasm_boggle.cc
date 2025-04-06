#include <emscripten/bind.h>

#include "boggler.h"
#include "trie.h"

using namespace emscripten;

EMSCRIPTEN_BINDINGS(wasm_boggle) {
  class_<Trie>("Trie")
      .constructor<>()
      .function("num_nodes", &Trie::NumNodes)
      .function("size", &Trie::Size)
      .class_function("CreateFromFile", &Trie::CreateFromFileStr);

  register_vector<int>("vector<int>");
  register_vector<vector<int>>("vector<vector<int>>");

  using BB = Boggler<4, 4>;
  class_<BB>("Boggler").constructor<Trie*>().function("find_words", &BB::FindWords);
}
