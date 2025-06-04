#!/usr/bin/env python
"""Try up to 4 letter changes on a board to try to improve it.

3568: perslatgcineders
"""

import argparse
import heapq
import itertools
import math
import sys

from cpp_boggle import Boggler44, Trie
from tqdm import tqdm

from boggle.args import add_standard_args, get_trie_from_args
from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import LEN_TO_DIMS, cpp_boggler


def main():
    parser = argparse.ArgumentParser(
        prog="neighbor_search",
        description="Exhaustively search a neighborhood around a Boggle board",
    )
    parser.add_argument(
        "board",
        type=str,
        help="Seed board",
    )
    parser.add_argument(
        "--max_distance", default=4, type=int, help="Maximum edit distance to search"
    )
    parser.add_argument(
        "--pool_size",
        default=10,
        type=int,
        help="Number of high-scoring boards to track for each edit distance",
    )
    add_standard_args(parser, python=True)
    args = parser.parse_args()
    t = get_trie_from_args(args)
    base_board = args.board
    dims = LEN_TO_DIMS[len(base_board)]
    if args.python:
        boggler = PyBoggler(t, dims)
    else:
        boggler = cpp_boggler(t, dims)

    letters = [chr(ord("a") + i) for i in range(26)]
    assert len(letters) == 26
    assert letters[0] == "a"
    assert letters[-1] == "z"

    n = len(base_board)
    all_indices = [*range(n)]

    best_score = boggler.score(base_board)
    print(f"Starting from {best_score} {base_board}")

    seen = {base_board}

    # for k in (1, 2, 3, 4):
    for k in range(1, args.max_distance + 1):
        print("")
        print(f"{k=}")
        best = []
        threshold = 0
        for indices in tqdm(
            itertools.combinations(all_indices, k), total=math.comb(n, k)
        ):
            # print(indices)
            letters = [chr(ord("a") + i) for i in range(26)]
            for letters in itertools.combinations_with_replacement(letters, k):
                cells = [*base_board]
                for i, c in zip(indices, letters):
                    cells[i] = c
                bd = "".join(cells)
                if bd in seen:
                    continue
                score = boggler.score(bd)
                if score < threshold:
                    continue

                seen.add(bd)
                item = (score, bd)
                # if score > 3500:
                #     print(item)
                if len(best) < args.pool_size:
                    heapq.heappush(best, item)
                else:
                    worst_score, _ = heapq.heappushpop(best, item)
                    threshold = worst_score

        for i, (score, bd) in enumerate(sorted(best, reverse=True)):
            print(f"{i:3d} {score}: {bd}")


if __name__ == "__main__":
    main()
