#!/usr/bin/env python

import sys
import time
from collections import Counter

import numpy as np
from cpp_boggle import BucketBoggler34, Trie
from tqdm import tqdm

from boggle.break_all import Bogglers
from boggle.breaker import IBucketBreaker
from boggle.ibuckets import PyBucketBoggler
from boggle.ibuckets_tree import TreeBucketBoggler
from boggle.trie import make_py_trie


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
    dims = {
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(board)]

    bb = Bogglers[dims](t)
    # bb.PrintNeighbors()
    if " " not in board:
        board = " ".join([*board])
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
    pbb = PyBucketBoggler(pyt, dims=dims)
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


def try_all2(bb: PyBucketBoggler, cell1: int, cell2: int):
    cells = bb.as_string().split(" ")
    max_cell = 0
    for choice1 in cells[cell1]:
        for choice2 in cells[cell2]:
            cp = [*cells]
            cp[cell1] = choice1
            cp[cell2] = choice2
            assert bb.ParseBoard(" ".join(cp))
            score = bb.UpperBound(500_000)
            # d = bb.Details()
            # print(
            #     f"{cell1}={choice1}, {cell2}={choice2}",
            #     score,
            #     d.max_nomark,
            #     d.sum_union,
            # )
            max_cell = max(max_cell, score)
    print(f"max (explicit): {max_cell}")


def try_all_tree(bb: TreeBucketBoggler):
    print(bb.as_string())
    cells = bb.as_string().split(" ")
    max_cell = 0
    i = 4
    with Timer(f"force {i}"):
        for c in cells[4]:
            cp = [*cells]
            cp[4] = c
            assert bb.ParseBoard(" ".join(cp))

            with Timer(f"force {i}={c}"):
                score = bb.UpperBound({0, 1, 2, 3, 5, 6, 7, 8})
            # d = bb.Details()
            print(f"{i}/{c}", score)
            max_cell = max(max_cell, score)
    print(f"{i}: {max_cell}")


def mopup(bb: BucketBoggler34, root: str, tbb: TreeBucketBoggler):
    # Iterate over all the remaining board classes and break them.
    root_bd = root.split(" ")
    best_score = 1500
    breaker = IBucketBreaker(bb, (3, 4), best_score=best_score, num_splits=26)
    max_tree = tbb.max_tree
    cells = max_tree.cells
    unbroken = np.argwhere(max_tree.data >= best_score)
    for n, multi_idx in tqdm(enumerate(unbroken), smoothing=0, total=len(unbroken)):
        bd = [*root_bd]
        for i, v in enumerate(multi_idx):
            bd[cells[i]] = root_bd[cells[i]][v]
        bd_str = " ".join(bd)
        breaker.bb.ParseBoard(bd_str)
        # print(
        #     n,
        #     "/",
        #     len(unbroken),
        #     bd_str,
        #     breaker.bb.NumReps(),
        #     max_tree.data[tuple(multi_idx)],
        # )
        details = breaker.Break()
        if details.failures:
            print(details.failures)
        # if details.max_depth > 1:
        #     print(f"max_depth={details.max_depth}")


def print_counter(c: Counter[str]):
    for k in sorted(c.keys()):
        print(f"{k}: {c[k]}")


def main():
    (board,) = sys.argv[1:]
    t = Trie.CreateFromFile("boggle-words.txt")
    bb = BucketBoggler34(t)
    bb.ParseBoard(board)
    cell = 5
    print("C++")
    try_all(bb, cell)

    bb.ParseBoard(board)
    # with Timer("C++ BucketBoggler explicit"):
    #     try_all2(bb, cell, 8)

    print("---")

    pyt = make_py_trie("boggle-words.txt")
    pbb = PyBucketBoggler(pyt, (3, 4))
    pbb.ParseBoard(board)
    print("Python")
    # try_all(pbb, cell)
    pyt.ResetMarks()

    print("---\nTree boggler\n")
    tbb = TreeBucketBoggler(pyt, (3, 4), 2)
    tbb.ParseBoard(board)

    # with Timer("no force"):
    #     score = tbb.UpperBound(set())
    #     print("no force", score)
    #
    # with Timer(f"force {cell}"):
    #     score = tbb.UpperBound({cell})
    #     print("force 4", score)
    with Timer("force depth 5, 8"):
        score = tbb.UpperBound({5, 8})
        print("force depth 5, 8", score)
    print_counter(tbb.universe.counts)

    tbb.universe.reset_counts()
    with Timer("force depth 2"):
        # score = tbb.UpperBound({cell, 8})
        score = tbb.UpperBound({0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11})
        print("force depth 2", score)
    print_counter(tbb.universe.counts)

    tbb.universe.reset_counts()
    # with Timer("tree"):
    #     score = tbb.UpperBound({1, 2, 4, 5, 6, 7, 8, 10})
    # print(f"tree bucket boggler score: {score}")
    # num_elim = (tbb.max_tree.data < 1500).sum()
    # count = tbb.max_tree.data.size
    # num_left = count - num_elim
    # print(f"num left: {num_left} / {count}")
    # print_counter(tbb.universe.counts)
    # with Timer("mopup"):
    #     mopup(bb, board, tbb)
    # tbb.universe.print(tbb.max_tree)

    # try_all_tree(tbb)

    if False:
        with Timer("force 1, 4, 7"):
            score = tbb.UpperBound(500_000, {1, 4, 7})
            d = tbb.Details()
            print("force 1, 4, 7", score, d.max_nomark, d.sum_union)

        with Timer("force 1, 4, 7, 3"):
            score = tbb.UpperBound(500_000, {1, 4, 7, 3})
            d = tbb.Details()
            print("force 1, 4, 7, 3", score, d.max_nomark, d.sum_union)

        with Timer("force 1, 4, 7, 3, 5"):
            score = tbb.UpperBound(500_000, {1, 4, 7, 3, 5})
            d = tbb.Details()
            print("force 1, 4, 7, 3, 5", score, d.max_nomark, d.sum_union)

        with Timer("force 1, 4, 7, 3, 5, 0"):
            score = tbb.UpperBound(500_000, {1, 4, 7, 3, 5, 0})
            d = tbb.Details()
            print("force 1, 4, 7, 3, 5, 0", score, d.max_nomark, d.sum_union)

        with Timer("force 1, 4, 7, 3, 5, 0, 6, 8, 2"):
            score = tbb.UpperBound(500_000, {1, 4, 7, 3, 5, 0, 6, 8, 2})
            d = tbb.Details()
            print("force 1, 4, 7, 3, 5, 0, 6, 8, 2", score)

    # tbb.universe.print(tbb.max_tree)

    # with Timer("try_all2"):
    #     pbb.ParseBoard(board)
    #     try_all2(pbb, 1, 4)


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
    # main()
    main_old()
