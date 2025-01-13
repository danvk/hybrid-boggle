#!/usr/bin/env python
"""Evaluate all 4x4 boards that contain a 3x4 subboard."""

import sys

from cpp_boggle import Boggler

from boggle.board_id import to_2d


def main():
    (board3,) = sys.argv[1:]
    assert len(board3) == 12

    bd33 = to_2d(board3, (3, 4))


if __name__ == "__main__":
    main()
