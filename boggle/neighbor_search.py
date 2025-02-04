#!/usr/bin/env python
"""Try up to 4 letter changes on a board to try to improve it.

3568: perslatgcineders
"""

import heapq
import itertools
import math
import sys

from cpp_boggle import Boggler, Trie
from tqdm import tqdm


def main():
    (base_board,) = sys.argv[1:]
    assert len(base_board) == 16

    t = Trie.CreateFromFile("wordlists/enable2k.txt")
    assert t
    boggler = Boggler(t)

    letters = [chr(ord("a") + i) for i in range(26)]
    assert len(letters) == 26
    assert letters[0] == "a"
    assert letters[-1] == "z"

    n = len(base_board)
    all_indices = [*range(n)]

    best_score = boggler.Score(base_board)
    print(f"Starting from {best_score} {base_board}")

    seen = {base_board}
    best = [(best_score, base_board)]

    threshold = 0

    for k in (1, 2, 3, 4):
        print("")
        print(f"{k=}")
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
                score = boggler.Score(bd)
                if score < threshold:
                    continue

                seen.add(bd)
                item = (score, bd)
                if score > 3500:
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
