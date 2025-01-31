#!/usr/bin/env python
"""Score boggle boards."""

import argparse
import fileinput
import sys
import time

from cpp_boggle import Trie

from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import Bogglers
from boggle.trie import make_py_trie


def main():
    parser = argparse.ArgumentParser(description="Lift all the way to breaking")
    parser.add_argument(
        "--size",
        type=int,
        choices=(22, 33, 34, 44),
        default=33,
        help="Size of the boggle board.",
    )
    parser.add_argument(
        "--dictionary",
        type=str,
        default="boggle-words.txt",
        help="Path to dictionary file with one word per line. Words must be "
        '"bogglified" via make_boggle_dict.py to convert "qu" -> "q".',
    )
    parser.add_argument(
        "--python",
        action="store_true",
        help="Use Python implementation of ibuckets instead of C++.",
    )
    parser.add_argument(
        "files", metavar="FILE", nargs="*", help="Files containing boards, or stdin"
    )

    args = parser.parse_args()
    w, h = dims = args.size // 10, args.size % 10

    if args.python:
        t = make_py_trie(args.dictionary)
        assert t
        boggler = PyBoggler(t, dims)
    else:
        t = Trie.CreateFromFile(args.dictionary)
        assert t
        boggler = Bogglers[dims](t)

    start_s = time.time()
    n = 0
    for line in fileinput.input(files=args.files):
        board = line.strip()
        # b.set_board(board)
        # print(f"{board}: {b.score()}")
        score = boggler.score(board)
        print(f"{board}: {score}")
        n += 1
    end_s = time.time()
    elapsed_s = end_s - start_s
    rate = n / elapsed_s
    sys.stderr.write(f"{n} boards in {elapsed_s:.2f}s = {rate:.2f} boards/s\n")


if __name__ == "__main__":
    main()
