#!/usr/bin/env python

import argparse

from boggle.args import add_standard_args, get_trie_from_args
from boggle.dimensional_bogglers import LEN_TO_DIMS, BucketBogglers
from boggle.ibuckets import PyBucketBoggler


def main():
    parser = argparse.ArgumentParser(
        prog="Bucket Boggle Solver",
        description="Find upper bounds on classes of Boggle boards",
    )
    parser.add_argument(
        "board",
        type=str,
        help="Board class to break. Cells are space-delimited. "
        "If there are no spaces, it's assumed that each cell is one letter.",
    )
    parser.add_argument(
        "--print_words",
        action="store_true",
        help="Print all the words that can be found in a board class (sum/union)",
    )
    add_standard_args(parser, python=True)
    args = parser.parse_args()
    t = get_trie_from_args(args)

    board = args.board
    if " " not in board:
        board = " ".join([*board])
    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]

    if args.python:
        bb = PyBucketBoggler(t, dims)
    else:
        bb = BucketBogglers[dims](t)

    if args.print_words:
        assert args.python, "--print_words only supported with --python"
        bb.collect_words = True

    bb.ParseBoard(board)
    bound = bb.UpperBound(500_000)
    d = bb.Details()
    print(f"{bound} (max={d.max_nomark}, sum={d.sum_union}) {bb.as_string()}")

    if args.print_words:
        print("\n".join(sorted(bb.words)))


if __name__ == "__main__":
    main()
