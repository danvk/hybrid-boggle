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

  register_vector<int>("VectorInt");
  register_vector<vector<int>>("VectorVectorInt");

  using BB3 = Boggler<3, 3>;
  class_<BB3>("Boggler33").constructor<Trie*>().function("find_words", &BB3::FindWords);

  using BB4 = Boggler<4, 4>;
  class_<BB4>("Boggler44").constructor<Trie*>().function("find_words", &BB4::FindWords);

  using BB5 = Boggler<5, 5>;
  class_<BB5>("Boggler55").constructor<Trie*>().function("find_words", &BB5::FindWords);
}
