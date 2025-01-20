#!/usr/bin/env python
"""Find the highest-scoring board via exhaustive search.

This is only really feasible for very small (2x2) boards.
For 2x2, the best board is:

  A S
  E T

with 18 points on it.
"""

import itertools

from tqdm import tqdm

from boggle.boggler import PyBoggler
from boggle.trie import make_py_trie


def main():
    t = make_py_trie("boggle-words.txt")
    boggler = PyBoggler(t, (2, 2))

    atoz = "".join(chr(x) for x in range(ord("a"), ord("z") + 1))
    boards = itertools.product(atoz, repeat=4)

    best_score = 0
    # best_board = None
    for board in tqdm(boards, total=26**4):
        boggler.set_board("".join(board))
        score = boggler.score()
        if score > best_score:
            print(score, board)
            best_score = score
            # best_board = board


if __name__ == "__main__":
    main()
