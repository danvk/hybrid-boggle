#!/usr/bin/env python

import sys
import time

from cpp_boggle import BucketBoggler33, Trie

from boggle.boggle import make_py_trie
from boggle.ibuckets import PyBucketBoggler


class Timer:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        self.time = (time.perf_counter() - self.start) * 1e3
        self.readout = f"{self.label}: {self.time:.3f} ms"
        print(self.readout)


def main_old():
    (board,) = sys.argv[1:]
    t = Trie.CreateFromFile("boggle-words.txt")
    assert t.FindWord("qinqennia") is not None
    bb = BucketBoggler33(t)
    bb.ParseBoard(board)
    print(bb.as_string())
    with Timer("C++"):
        print(bb.UpperBound(500_000))
    d = bb.Details()
    print(d.max_nomark, d.sum_union)

    pyt = make_py_trie("boggle-words.txt")
    assert pyt.FindWord("qinqennia") is not None
    assert pyt.StartsWord(ord("q") - ord("a"))
    qt = pyt.Descend(ord("q") - ord("a"))
    assert qt is not None
    assert qt.StartsWord(ord("i") - ord("a"))
    pbb = PyBucketBoggler(pyt)
    pbb.ParseBoard(board)
    print(pbb.as_string())
    with Timer("py"):
        print(pbb.UpperBound(500_000))
    d = pbb.details_
    print(d.max_nomark, d.sum_union)


def try_all(bb):
    print(bb.as_string())
    with Timer("root"):
        score = bb.UpperBound(500_000)
        d = bb.Details()
        print("root", score, d.max_nomark, d.sum_union)

    cells = bb.as_string().split(" ")
    for i, cell in enumerate(cells):
        if len(cell) == 1:
            continue
        max_cell = 0
        with Timer(f"force {i}"):
            for c in cell:
                cp = [*cells]
                cp[i] = c
                assert bb.ParseBoard(" ".join(cp))
                score = bb.UpperBound(500_000)
                d = bb.Details()
                print(f"{i}/{c}", score, d.max_nomark, d.sum_union)
                max_cell = max(max_cell, score)
        print(f"{i}: {max_cell}")


def main():
    (board,) = sys.argv[1:]
    t = Trie.CreateFromFile("boggle-words.txt")
    bb = BucketBoggler33(t)
    bb.ParseBoard(board)
    print("C++")
    try_all(bb)

    print("---")

    pyt = make_py_trie("boggle-words.txt")
    pbb = PyBucketBoggler(pyt)
    pbb.ParseBoard(board)
    print("Python")
    try_all(pbb)


if __name__ == "__main__":
    main()
