#!/usr/bin/env python
"""Find all the words on a Boggle board and print them."""

import sys

from boggle.boggle import HybridBoggler, make_py_trie


def main():
    (_, board) = sys.argv
    t = make_py_trie("boggle-words.txt")
    boggler = HybridBoggler(t)
    boggler.print_words = True
    if len(board) == 9:
        (a, b, c, d, e, f, g, h, i) = board
        board = "".join((a, b, c, ".", d, e, f, ".", g, h, i, ".", ".", ".", ".", "."))
        print(board)
    boggler.set_board(board)
    print("score:", boggler.score())


if __name__ == "__main__":
    main()
