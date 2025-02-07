#!/usr/bin/env python
"""Find the highest-scoring board via exhaustive search.

This is only really feasible for very small (2x2) boards.
For 2x2, the best board is:

  A S
  E T

with 18 points on it.
"""

import itertools
import sys

from cpp_boggle import Trie
from tqdm import tqdm

from boggle.dimensional_bogglers import cpp_boggler
from boggle.trie import make_py_trie


def main():
    # t = make_py_trie("boggle-words.txt")
    t = Trie.CreateFromFile("boggle-words.txt")
    assert t
    size = int(sys.argv[1])
    w, h = dims = size // 10, size % 10
    # boggler = PyBoggler(t, dims)
    boggler = cpp_boggler(t, dims)

    atoz = "".join(chr(x) for x in range(ord("a"), ord("z") + 1))
    boards = itertools.product(atoz, repeat=w * h)

    best_score = 0
    # best_board = None
    for board in tqdm(boards, total=26 ** (w * h)):
        bd = "".join(board)
        score = boggler.score(bd)
        if score > best_score:
            print(score, bd)
            best_score = score
            # best_board = board


if __name__ == "__main__":
    main()
