#!/usr/bin/env python

import sys

from cpp_boggle import BucketBoggler33, Trie

from boggle.boggle import make_py_trie
from boggle.ibuckets import PyBucketBoggler

i = 0


def neighbors():
    global i
    out = [[] for _ in range(0, 9)]

    def HIT(x, y):
        out[i].append(3 * x + y)
        out[i].sort()

    def HIT3x(x, y):
        HIT(x, y)
        HIT(x + 1, y)
        HIT(x + 2, y)

    def HIT3y(x, y):
        HIT(x, y)
        HIT(x, y + 1)
        HIT(x, y + 2)

    def HIT8(x, y):
        HIT3x(x - 1, y - 1)
        HIT(x - 1, y)
        HIT(x + 1, y)
        HIT3x(x - 1, y + 1)

    i = 0 * 3 + 0
    HIT(0, 1)
    HIT(1, 0)
    HIT(1, 1)
    i = 0 * 3 + 1
    HIT(0, 0)
    HIT3y(1, 0)
    HIT(0, 2)
    i = 0 * 3 + 2
    HIT(0, 1)
    HIT(1, 1)
    HIT(1, 2)
    i = 1 * 3 + 0
    HIT(0, 0)
    HIT(2, 0)
    HIT3x(0, 1)
    i = 1 * 3 + 1
    HIT8(1, 1)
    i = 1 * 3 + 2
    HIT3x(0, 1)
    HIT(0, 2)
    HIT(2, 2)
    i = 2 * 3 + 0
    HIT(1, 0)
    HIT(1, 1)
    HIT(2, 1)
    i = 2 * 3 + 1
    HIT3y(1, 0)
    HIT(2, 0)
    HIT(2, 2)
    i = 2 * 3 + 2
    HIT(1, 2)
    HIT(1, 1)
    HIT(2, 1)

    print("C++", out)


def main():
    neighbors()
    (board,) = sys.argv[1:]
    t = Trie.CreateFromFile("boggle-words.txt")
    assert t.FindWord("qinqennia") is not None
    bb = BucketBoggler33(t)
    bb.ParseBoard(board)
    print(bb.as_string())
    print(bb.UpperBound(5000))

    pyt = make_py_trie("boggle-words.txt")
    assert pyt.FindWord("qinqennia") is not None
    assert pyt.StartsWord(ord("q") - ord("a"))
    qt = pyt.Descend(ord("q") - ord("a"))
    assert qt is not None
    assert qt.StartsWord(ord("i") - ord("a"))
    pbb = PyBucketBoggler(pyt)
    pbb.ParseBoard(board)
    print(pbb.as_string())
    print(pbb.UpperBound(5000))


if __name__ == "__main__":
    main()
