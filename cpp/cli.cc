// Pure C++ CLI. The intended use is WASM.

#include <cstdio>
#include <cstdlib>
#include <iostream>

#include "boggler.h"
#include "trie.h"

void usage_and_die(int argc, char** argv) {
  fprintf(stderr, "Usage: %s <dictionary> <catdlinemaropets>\n", argv[0]);
  exit(1);
}

int main(int argc, char** argv) {
  if (argc != 3) {
    usage_and_die(argc, argv);
  }

  auto dict_file = argv[1];
  auto board = argv[2];

  auto t = Trie::CreateFromFile(dict_file);
  if (!t.get()) {
    std::cerr << "Unable to load dictionary " << dict_file << std::endl;
    return 1;
  }
  // std::cerr << "Loaded " << t->NumNodes() << " nodes" << std::endl;

  unique_ptr<Boggler<4, 4>> boggler(new Boggler<4, 4>(t.get()));
  // int score = boggler->Score(board);
  // if (score == -1) {
  //   std::cerr << "Unable to score board " << board << std::endl;
  //   return 1;
  // }
  auto words = boggler->FindWords(board);
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
  std::cout << std::endl;
}
