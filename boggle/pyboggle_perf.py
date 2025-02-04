#!/usr/bin/env python
"""I/O-free performance test"""

import random
import sys
import time

from cpp_boggle import Trie

from boggle.boggler import LETTER_A, PyBoggler
from boggle.dimensional_bogglers import cpp_boggler
from boggle.trie import make_py_trie


def random_board(n: int) -> str:
    return "".join(chr(LETTER_A + random.randint(0, 25)) for _ in range(n))


def main():
    (n_str,) = sys.argv[1:]
    n = int(n_str)

    dims = (4, 4)

    # TODO: set up --size, --python args
    if True:
        t = make_py_trie("wordlists/enable2k.txt")
        boggler = PyBoggler(t, dims)
    else:
        t = Trie.CreateFromFile("wordlists/enable2k.txt")
        boggler = cpp_boggler(t, dims)

    random.seed(0xB0881E)
    boards = [random_board(dims[0] * dims[1]) for _ in range(n)]
    total_score = 0
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
