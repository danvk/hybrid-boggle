#!/usr/bin/env python
"""Score boggle boards."""

import argparse
import fileinput
import sys
import time

from boggle.args import add_standard_args, get_trie_and_boggler_from_args


def main():
    parser = argparse.ArgumentParser(description="Lift all the way to breaking")
    add_standard_args(parser, python=True)
    parser.add_argument(
        "files", metavar="FILE", nargs="*", help="Files containing boards, or stdin"
    )
    parser.add_argument(
        "--print_words",
        action="store_true",
        help="Print all the words that can be found on each board.",
    )

    args = parser.parse_args()
    _, boggler = get_trie_and_boggler_from_args(args)

    if args.print_words:
        assert args.python, "--print_words only supported with --python"
        boggler.collect_words = True

    start_s = time.time()
    n = 0
    for line in fileinput.input(files=args.files):
        board = line.strip()
        score = boggler.score(board)
        print(f"{board}: {score}")
        if args.print_words:
            print("\n".join(sorted(boggler.words)))
        n += 1
    end_s = time.time()
    elapsed_s = end_s - start_s
    rate = n / elapsed_s
    sys.stderr.write(f"{n} boards in {elapsed_s:.2f}s = {rate:.2f} boards/s\n")


if __name__ == "__main__":
    main()
