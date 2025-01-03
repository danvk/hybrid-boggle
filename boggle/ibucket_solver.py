#!/usr/bin/env python

import sys
import time

from cpp_boggle import BucketBoggler33, Trie

from boggle.boggle import make_py_trie
from boggle.ibuckets import PyBucketBoggler
from boggle.ibuckets_tree import TreeBucketBoggler
from boggle.max_tree import print_tabular


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


def try_all(bb, force_cell=-1):
    print(bb.as_string())
    with Timer("root"):
        score = bb.UpperBound(500_000)
        d = bb.Details()
        print("root", score, d.max_nomark, d.sum_union)

    cells = bb.as_string().split(" ")
    for i, cell in enumerate(cells):
        if (force_cell != -1 and i != force_cell) or len(cell) == 1:
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


def try_all2(bb, cell1: int, cell2: int):
    cells = bb.as_string().split(" ")
    max_cell = 0
    for choice1 in cells[cell1]:
        for choice2 in cells[cell2]:
            cp = [*cells]
            cp[cell1] = choice1
            cp[cell2] = choice2
            assert bb.ParseBoard(" ".join(cp))
            score = bb.UpperBound(500_000)
            d = bb.Details()
            print(
                f"{cell1}={choice1}, {cell2}={choice2}",
                score,
                d.max_nomark,
                d.sum_union,
            )
            max_cell = max(max_cell, score)
    print(f"max (explicit): {max_cell}")


def main():
    (board,) = sys.argv[1:]
    t = Trie.CreateFromFile("boggle-words.txt")
    bb = BucketBoggler33(t)
    bb.ParseBoard(board)
    cell = 4
    print("C++")
    try_all(bb, cell)

    # print("---")

    pyt = make_py_trie("boggle-words.txt")
    pbb = PyBucketBoggler(pyt)
    pbb.ParseBoard(board)
    print("Python")
    try_all(pbb, cell)

    print("---\nTree boggler\n")
    tbb = TreeBucketBoggler(pyt)
    tbb.ParseBoard(board)
    with Timer("no force"):
        score = tbb.UpperBound(500_000, set())
        d = tbb.Details()
        print("no force", score, d.max_nomark, d.sum_union)

    with Timer("force 4"):
        score = tbb.UpperBound(500_000, {cell})
        d = tbb.Details()
        print("force 4", score, d.max_nomark, d.sum_union)

    with Timer("force 1, 4"):
        score = tbb.UpperBound(500_000, {1, 4})
        d = tbb.Details()
        print("force 1, 4", score, d.max_nomark, d.sum_union)

    print_tabular(tbb.max_tree)

    with Timer("try_all2"):
        pbb.ParseBoard(board)
        try_all2(pbb, 1, 4)


def main_profile():
    pyt = make_py_trie("boggle-words.txt")
    tbb = TreeBucketBoggler(pyt)
    board = "aeiou chkmpt lnrsy lnrsy lnrsy aeiou aeiou aeiou bdfgjvwxz"
    tbb.ParseBoard(board)
    score = tbb.UpperBound(500_000, {1, 4})
    d = tbb.Details()
    print("force 1, 4", score, d.max_nomark, d.sum_union)


if __name__ == "__main__":
    # main_profile()
    main()
