#!/usr/bin/env python
"""Find the highest-scoring board via exhaustive search.

This is only really feasible for very small (2x2) boards.
For 2x2, the best board is:

  A S
  E T

with 18 points on it.
"""

import heapq
import itertools
import math
import sys

from cpp_boggle import Boggler34, Trie
from tqdm import tqdm

from boggle.boggler import PyBoggler
from boggle.trie import make_py_trie


def main_class():
    t = Trie.CreateFromFile("boggle-words.txt")
    (board,) = sys.argv[1:]
    cells = board.split(" ")
    assert len(cells) == 3 * 4
    b = Boggler34(t)

    best_score = 0
    total = math.prod(len(c) for c in cells)
    top100 = []
    threshold = 0

    for letters in tqdm(itertools.product(*cells), total=total):
        board = "".join(letters)
        score = b.score(board)
        if score < threshold:
            continue

        if len(top100) < 100:
            heapq.heappush(top100, (score, board))
        else:
            worst_score, _ = heapq.heappushpop(top100, (score, board))
            threshold = worst_score
        if score > best_score:
            best_score = score
            print(f"New best board: {board} {best_score}")

    for i, (score, bd) in enumerate(sorted(top100, reverse=True)):
        print(f"{i:3d} {score}: {bd}")


def main22():
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
    # main22()
    main_class()
