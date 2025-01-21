#!/usr/bin/env python
"""Find all the words on a Boggle board using a C++ Trie."""

import fileinput
import sys
import time

from cpp_boggle import Boggler44 as CppBoggler
from cpp_boggle import Trie as CppTrie


def main():
    t = CppTrie.CreateFromFile("boggle-words.txt")
    # t = make_py_trie("boggle-words.txt")

    b = CppBoggler(t)
    print(f"Loaded {t.Size()} words")
    start_s = time.time()
    n = 0
    for line in fileinput.input():
        board = line.strip()
        # b.set_board(board)
        # print(f"{board}: {b.score()}")
        _score = b.score(board)
        # print(f"{board}: {score}")
        n += 1
    end_s = time.time()
    elapsed_s = end_s - start_s
    rate = n / elapsed_s
    sys.stderr.write(f"{n} boards in {elapsed_s:.2f}s = {rate:.2f} boards/s\n")


if __name__ == "__main__":
    main()
