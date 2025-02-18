#!/usr/bin/env python
"""Exchange a list of boards for their canonically-rotated variants.

This script won't necessarily agree with break_all on which variant is canonical,
but it will replace each board with an equivalent one that's consistent within
this script.
"""

import fileinput

from boggle.symmetry import canonicalize, list_to_matrix


def main():
    for line in fileinput.input():
        bd = canonicalize(list_to_matrix(line.strip()))
        print("".join(str(x) for row in bd for x in row))


if __name__ == "__main__":
    main()
