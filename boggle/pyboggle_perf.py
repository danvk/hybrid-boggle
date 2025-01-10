#!/usr/bin/env python

import random
import sys
import time

from boggle.boggler import LETTER_A, PyBoggler
from boggle.trie import make_py_trie


def random_board(n: int) -> str:
    return "".join(chr(LETTER_A + random.randint(0, 25)) for _ in range(n))


def main():
    (n_str,) = sys.argv[1:]
    n = int(n_str)

    t = make_py_trie("boggle-words.txt")
    dims = (4, 4)
    boggler = PyBoggler(t, dims)

    random.seed(0xB0881E)
    boards = [random_board(dims[0] * dims[1]) for _ in range(n)]
    total_score = 0
    start_s = time.time()
    for board in boards:
        boggler.set_board(board)
        total_score += boggler.score()
    end_s = time.time()

    elapsed_s = end_s - start_s
    pace = len(boards) / elapsed_s

    print(f"{total_score=}")
    print(f"{elapsed_s:.02f}s, {pace:.02f} bds/sec")


if __name__ == "__main__":
    main()
