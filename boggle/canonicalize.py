#!/usr/bin/env python
"""Exchange a list of boards for their canonically-rotated variants."""

# XXX This script doesn't work at the moment, at least not for 3x4 boards.

import fileinput

from boggle.symmetry import canonicalize, transpose


def list_to_matrix(letters):
    w, h = {4: (2, 2), 9: (3, 3), 12: (3, 4), 16: (4, 4)}[len(letters)]

    bd_2d = [[0 for _y in range(0, h)] for _x in range(0, w)]
    for i in range(0, len(letters)):
        bd_2d[i // h][i % h] = letters[i]
    return bd_2d


def main():
    for line in fileinput.input():
        bd = canonicalize(list_to_matrix(line.strip()))
        print("".join(str(x) for row in transpose(bd) for x in row))


if __name__ == "__main__":
    main()
