#!/usr/bin/env python
"""Find all the words on a Boggle board using a C++ Trie."""

import fileinput
from example import Trie


SCORES = (0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11)


class Boggler:
    def __init__(self, trie):
        self.trie = trie
        self.runs = 0
        self.cells = [0] * 16

    def set_board(self, bd: str):
        assert len(bd) == 16
        for i, let in enumerate(bd):
            assert 'a' <= let <= 'z'
            self.cells[i] = ord(let) - ord('a')

    def __str__(self):
        return ''.join(chr(ord('a') + let) for let in self.cells)



def main():
    t = Trie.CreateFromFile("words")
    print(f"Loaded {t.Size()} words")
    for line in fileinput.input():
        board = line.strip()
        print(board)


if __name__ == '__main__':
    main()
