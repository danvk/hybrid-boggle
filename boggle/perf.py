#!/usr/bin/env python
"""I/O-free performance test.

On my M2 Macbook:

$ poetry run python -m boggle.perf --size 44 1000000 --random_seed 808813
total_score=41134010
4.67s, 214206.42 bds/sec
"""

import argparse
import random
import time

from boggle.args import add_standard_args, get_trie_and_boggler_from_args
from boggle.boggler import LETTER_A


def random_board(n: int) -> str:
    return "".join(chr(LETTER_A + random.randint(0, 25)) for _ in range(n))


def main():
    parser = argparse.ArgumentParser(
        prog="Boggler perf test",
        description="Measure the speed of board evaluation, free from I/O.",
    )
    add_standard_args(parser, random_seed=True, python=True)
    parser.add_argument("num_boards", type=int, help="Number of boards to evaluate")
    args = parser.parse_args()
    if args.random_seed >= 0:
        random.seed(args.random_seed)

    n = args.num_boards
    t, boggler = get_trie_and_boggler_from_args(args)

    w, h = args.size // 10, args.size % 10
    print(f"Generating {n} {w}x{h} boards...")
    boards = [random_board(w * h) for _ in range(n)]
    total_score = 0
    print("Scoring boards...")
    start_s = time.time()
    for board in boards:
        total_score += boggler.score(board)
    end_s = time.time()

    elapsed_s = end_s - start_s
    pace = len(boards) / elapsed_s

    print(f"{total_score=}")
    print(f"{elapsed_s:.02f}s, {pace:.02f} bds/sec")


if __name__ == "__main__":
    main()
