#!/usr/bin/env python
"""Find all the words on a Boggle board and print them."""

import sys

from boggle.boggler import PyBoggler
from boggle.trie import make_py_trie


def main():
    (_, board) = sys.argv
    t = make_py_trie("wordlists/enable2k.txt")
    dims = {
        4: (2, 2),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(board)]
    boggler = PyBoggler(t, dims)
    boggler.print_words = True
    print("score:", boggler.score(board))


if __name__ == "__main__":
    main()
