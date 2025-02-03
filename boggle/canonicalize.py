#!/usr/bin/env python
"""Exchange a list of boards for their canonically-rotated variants."""

import fileinput
import math

from boggle.symmetry import canonicalize


def list_to_matrix(letters):
    n = math.sqrt(len(letters))
    assert n == int(n)
    n = int(n)
    bd_2d = [[0 for _x in range(0, n)] for _y in range(0, n)]
    for i in range(0, len(letters)):
        bd_2d[i // n][i % n] = letters[i]
    return bd_2d


def main():
    for line in fileinput.input():
        bd = canonicalize(list_to_matrix(line.strip()))
        print("".join(str(x) for row in bd for x in row))


if __name__ == "__main__":
    main()
