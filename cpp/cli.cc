// Pure C++ CLI. The intended use is WASM.

#include <cstdio>
#include <cstdlib>
#include <iostream>

#include "boggler.h"
#include "trie.h"

void usage_and_die(int argc, char** argv) {
  fprintf(
      stderr,
      "Usage: %s <dictionary> <multiboggle=0 or 1> <catdlinemaropets>\n",
      argv[0]
  );
  exit(1);
}

int main(int argc, char** argv) {
  if (argc != 4) {
    usage_and_die(argc, argv);
  }

  auto dict_file = argv[1];
  auto multiboggle_str = argv[2];
  auto board = argv[3];

  bool multiboggle = string(multiboggle_str) == "1";

  auto t = Trie::CreateFromFile(dict_file);
  if (!t.get()) {
    std::cerr << "Unable to load dictionary " << dict_file << std::endl;
    return 1;
  }
  // std::cerr << "Loaded " << t->NumNodes() << " nodes" << std::endl;

  unique_ptr<Boggler<4, 4>> boggler(new Boggler<4, 4>(t.get()));
  auto words = boggler->FindWords(board, multiboggle);
  char buf[17];
  for (auto seq : words) {
    int i = 0;
    for (; i < seq.size(); i++) {
      int idx = seq[i];
      buf[i] = board[idx];
    }
    buf[i] = '\0';
    std::cout << buf << ":";
    for (auto idx : seq) {
      int x = idx / 4;
      int y = idx % 4;
      std::cout << " " << x << y;
    }
    std::cout << "\n";
  }
  std::flush(std::cout);
}
