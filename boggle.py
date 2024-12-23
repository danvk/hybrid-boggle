#!/usr/bin/env python
"""Find all the words on a Boggle board using a C++ Trie."""

import fileinput
from example import Trie


SCORES = (0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11)
LETTER_Q = ord('q') - ord('a')

class Boggler:
    def __init__(self, trie):
        self._trie = trie
        self._runs = 0
        self._cells = [0] * 16
        self._used = [False] * 16
        self._score = 0

    def set_board(self, bd: str):
        assert len(bd) == 16
        for i, let in enumerate(bd):
            assert 'a' <= let <= 'z'
            self._cells[i] = ord(let) - ord('a')

    def __str__(self):
        return ''.join(chr(ord('a') + let) for let in self._cells)

    def score(self):
        self._score = 0
        self._runs += 1
        self._used = [False] * 16
        t = self._trie
        for i in range(0, 16):
            c = self._cells[i]
            if t.StartsWord(c):
                self.do_dfs(i, 0, t.Descend(c))
        return self._score

    def do_dfs(self, i: int, length: int, t):
        c = self._cells[i]
        self._used[i] = True
        length += 1 if c != LETTER_Q else 2
        if t.IsWord():
            if t.Mark() != self._runs:
                t.SetMark(self._runs)
                self._score += SCORES[length]

        x = i % 4
        y = i // 4
        for dx in range(-1, 2):
            nx = x + dx
            if nx < 0 or nx > 3:
                continue
            for dy in range(-1, 2):
                ny = y + dy
                if ny < 0 or ny > 3:
                    continue
                idx = 4 * nx + ny
                if not self._used[idx]:
                    cc = self._cells[idx]
                    if t.StartsWord(cc):
                        self.do_dfs(idx, length, t.Descend(cc))

        self._used[i] = False


def main():
    t = Trie.CreateFromFile("boggle-words.txt")
    b = Boggler(t)
    print(f"Loaded {t.Size()} words")
    for line in fileinput.input():
        board = line.strip()
        b.set_board(board)
        print(b)
        print(b.score())


if __name__ == '__main__':
    main()
