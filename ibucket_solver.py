#!/usr/bin/env python

import sys
from example import Trie, BucketBoggler


def main():
    (board,) = sys.argv[1:]
    t = Trie.CreateFromFile("boggle-words.txt")
    bb = BucketBoggler(t)
    bb.ParseBoard(board)
    print(bb.as_string())
    print(bb.UpperBound(5000))


if __name__ == "__main__":
    main()
