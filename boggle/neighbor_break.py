#!/usr/bin/env python
"""Use ibuckets to explore a larger radius around a given board."""

import heapq
import itertools
import math
import sys

from cpp_boggle import Boggler44, BucketBoggler44, Trie
from tqdm import tqdm

from boggle.breaker import Breaker


def main():
    (base_board,) = sys.argv[1:]
    assert len(base_board) == 16

    t1 = Trie.CreateFromFile("wordlists/enable2k.txt")
    assert t1
    boggler = Boggler44(t1)
    bb = BucketBoggler44(t1)
    breaker = Breaker(bb, (4, 4), 3500, num_splits=10)

    a_to_z = "".join(chr(ord("a") + i) for i in range(26))
    assert len(a_to_z) == 26
    assert a_to_z[0] == "a"
    assert a_to_z[-1] == "z"

    n = len(base_board)
    all_indices = [*range(n)]

    best_score = boggler.score(base_board)
    print(f"Starting from {best_score} {base_board}")

    seen = {base_board}
    best = [(best_score, base_board)]

    threshold = 0

    k = 5
    for indices in tqdm(itertools.combinations(all_indices, k), total=math.comb(n, k)):
        cells = [*base_board]
        for i in indices:
            cells[i] = a_to_z

        bb.ParseBoard(" ".join(cells))
        # print(cells)
        details = breaker.Break()
        print(
            details.elapsed_s,
            "s @",
            details.max_depth,
        )
        if not details.failures:
            continue

        for bd in details.failures:
            if bd in seen:
                continue
            score = boggler.score(bd)
            if score < threshold:
                continue

            seen.add(bd)
            item = (score, bd)
            print(item)
            if len(best) < 100:
                heapq.heappush(best, item)
            else:
                worst_score, _ = heapq.heappushpop(best, item)
                threshold = worst_score

    for i, (score, bd) in enumerate(sorted(best, reverse=True)):
        print(f"{i:3d} {score}: {bd}")


if __name__ == "__main__":
    main()
