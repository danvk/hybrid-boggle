#!/usr/bin/env python
"""Find all the words on a Boggle board and print them."""

import sys

from boggle.boggler import PyBoggler
from boggle.trie import make_py_trie


def main():
    (_, board) = sys.argv
    t = make_py_trie("boggle-words.txt")
    dims = {
        4: (2, 2),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(board)]
    boggler = PyBoggler(t, dims)
    boggler.print_words = True
    boggler.set_board(board)
    print("score:", boggler.score())


if __name__ == "__main__":
    main()
