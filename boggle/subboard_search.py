#!/usr/bin/env python
"""Evaluate all 4x4 boards that contain a 3x4 subboard.

For sindlatepers, the best this finds is:

  0 3335: sindlateperssidc

Good, but it's possible to do better!
"""

import heapq
import itertools
import sys

from cpp_boggle import Boggler, Trie
from tqdm import tqdm


def main():
    (board3,) = sys.argv[1:]
    assert len(board3) == 12

    t = Trie.CreateFromFile("wordlists/enable2k.txt")
    assert t
    boggler = Boggler(t)

    letters = [chr(ord("a") + i) for i in range(26)]
    assert len(letters) == 26
    assert letters[0] == "a"
    assert letters[-1] == "z"

    best = []
    for a, b, c, d in tqdm(itertools.product(*([letters] * 4)), total=26**4):
        bd = f"{board3}{a}{b}{c}{d}"
        score = boggler.Score(bd)
        if score < 1000:
            continue
        item = (score, bd)
        if len(best) < 100:
            heapq.heappush(best, item)
        else:
            heapq.heappushpop(best, item)

    for i, (score, bd) in enumerate(sorted(best, reverse=True)):
        print(f"{i:3d} {score}: {bd}")


if __name__ == "__main__":
    main()
