#!/usr/bin/env python
"""Exchange a list of boards for their canonically-rotated variants."""

# XXX This script doesn't work at the moment, at least not for 3x4 boards.

import fileinput

from boggle.symmetry import canonicalize, list_to_matrix, transpose


def main():
    for line in fileinput.input():
        bd = canonicalize(list_to_matrix(line.strip()))
        print("".join(str(x) for row in transpose(bd) for x in row))


if __name__ == "__main__":
    main()
