#!/usr/bin/env python
"""Find the highest-scoring board via exhaustive search.

Exhaustive search over all boards is only really feasible for very
small (2x2) boards. For 2x2, the best board is:

  A S
  E T

with 18 points on it.

For larger boards, it's possible to search within a board class.
"""

import argparse
import itertools
import math

from tqdm import tqdm

from boggle.args import add_standard_args, get_trie_and_boggler_from_args


def main_class():
    parser = argparse.ArgumentParser(
        prog="Exhaustive search within a board class",
        description="Find all the boggle boards above a certain score within a class.",
    )
    add_standard_args(parser, python=True)

    parser.add_argument("cutoff", type=int, help="Minimum score to keep.")
    parser.add_argument("board", type=str, help="Board class to exhaustively search.")
    args = parser.parse_args()

    cutoff = args.cutoff
    board = args.board
    cells = board.split(" ")
    total = math.prod(len(c) for c in cells)

    _t, boggler = get_trie_and_boggler_from_args(args)

    for letters in tqdm(itertools.product(*cells), total=total):
        board = "".join(letters)
        score = boggler.score(board)
        if score < cutoff:
            continue
        print(f"{score}\t{board}")


if __name__ == "__main__":
    main_class()
