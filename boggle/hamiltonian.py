#!/usr/bin/env python
"""Enumerate Hamiltonian circuits of the Boggle board.

- 2x2: 6 possible paths
- 2x3: 28 = 20 + 8 possible paths
- 3x3: 220 = 138 + 50 + 32 possible paths
- 3x4: 2757 = 1309 + 612 + 470 + 366
- 4x4: 68115 = 37948 + 17681 + 12486

Best 4x4 boards with ENABLE2K:
- 17 letters: qaicdrneetasnnil ("quadricentennials")
- 16 letters: hclbaiaertnssese ("charitablenesses")

With YAWL:
- 17 letters: qressatstiseremr ("quartermistresses")
- 16 letters: usaupltreaiernsd ("supernaturalised")

This analysis cannot be done for OSPD5, SOWPODS, NASPA23, and TWL06 because
they don't contain 16-letter words. This makes sense for Scrabble word lists!
"""

import argparse

from tqdm import tqdm

from boggle.args import add_standard_args, get_trie_and_boggler_from_args
from boggle.neighbors import NEIGHBORS
from boggle.trie import bogglify_word


def rec(
    cell: int,
    num_left: int,
    used: list[bool],
    seq: list[int],
    neighbors,
    out: list[list[int]],
):
    if num_left == 0:
        # success! a hamiltonian circuit
        out.append([*seq])
        return

    # try each un-visited neighbor
    count = 0
    used[cell] = True
    for neighbor in neighbors[cell]:
        if not used[neighbor]:
            seq.append(neighbor)
            rec(neighbor, num_left - 1, used, seq, neighbors, out)
            seq.pop()

    used[cell] = False
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Find the highest-scoring board with a 16-letter word.",
    )
    add_standard_args(parser, python=True)
    parser.add_argument(
        "--require_q",
        action="store_true",
        help='Require a "qu" to form a w*h+1 letter word.',
    )

    args = parser.parse_args()
    _, boggler = get_trie_and_boggler_from_args(args)
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 5
    assert 3 <= h <= 5
    n = w * h

    uniq_starts = {
        (2, 2): (0,),
        (2, 3): (0, 1),
        (3, 3): (0, 1, 4),
        (3, 4): (0, 1, 4, 5),
        (4, 4): (0, 1, 5),
    }

    paths: list[list[int]] = []
    for start in uniq_starts[dims]:
        rec(start, n - 1, [False] * n, [start], NEIGHBORS[(w, h)], paths)
    print(f"{len(paths)} candidate paths for {w}x{h}")

    candidate_words: list[str] = []
    for word in open(args.dictionary):
        word = word.strip()
        word = bogglify_word(word)
        if word is not None and len(word) == n and ("q" in word or not args.require_q):
            candidate_words.append(word)

    print(f"{len(candidate_words)} candidate words")

    best = (0, "")
    for path in tqdm(paths, smoothing=0):
        for word in candidate_words:
            cells = [""] * n
            for i, cell in enumerate(path):
                cells[cell] = word[i]
            bd = "".join(cells)
            score = boggler.score(bd)
            if score > best[0]:
                best = (score, bd, word, path)
                print(best)

    print(best)


if __name__ == "__main__":
    main()
