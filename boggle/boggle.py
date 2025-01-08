#!/usr/bin/env python
"""Find all the words on a Boggle board using a C++ Trie."""

import fileinput
import sys
import time

from cpp_boggle import Boggler as CppBoggler
from cpp_boggle import Trie as CppTrie

from boggle.neighbors import NEIGHBORS

SCORES = (0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11)
LETTER_A = ord("a")
LETTER_Q = ord("q") - LETTER_A


class PyBoggler:
    """Hybrid or pure-Python Boggler (depending on the Trie)."""

    def __init__(self, trie, dims: tuple[int, int]):
        self._trie = trie
        self._runs = 0
        w, h = dims
        self._n = w * h
        self._cells = [0] * self._n
        self._used = [False] * self._n
        self._score = 0
        self.print_words = False
        self._neighbors = NEIGHBORS[dims]
        assert not self._trie.IsWord()

    def set_board(self, bd: str):
        assert len(bd) == self._n
        for i, let in enumerate(bd):
            if let == ".":
                self._cells[i] = -1
            else:
                assert "a" <= let <= "z"
                self._cells[i] = ord(let) - LETTER_A

    def __str__(self):
        return "".join(chr(ord("a") + let) if let != -1 else "." for let in self._cells)

    def score(self):
        # This allows the same Trie to be used by multiple bogglers, e.g. for boggle_test.py
        self._runs = 1 + self._trie.Mark()
        self._trie.SetMark(self._runs)
        self._score = 0
        t = self._trie
        for i in range(0, self._n):
            c = self._cells[i]
            if c == -1:
                continue
            d = t.Descend(c)
            if d:
                self.do_dfs(i, 0, d)
        return self._score

    def do_dfs(self, i: int, length: int, t):
        c = self._cells[i]
        self._used[i] = True
        length += 1 if c != LETTER_Q else 2
        if t.IsWord():
            if t.Mark() != self._runs:
                t.SetMark(self._runs)
                self._score += SCORES[length]
                if self.print_words:
                    print(self._trie.__class__.ReverseLookup(self._trie, t))

        for idx in self._neighbors[i]:
            if not self._used[idx]:
                cc = self._cells[idx]
                if cc == -1:
                    continue
                d = t.Descend(cc)
                if d:
                    self.do_dfs(idx, length, d)

        self._used[i] = False


def main():
    t = CppTrie.CreateFromFile("boggle-words.txt")
    # t = make_py_trie("boggle-words.txt")

    b = CppBoggler(t)
    # print(f"Loaded {t.Size()} words")
    start_s = time.time()
    n = 0
    for line in fileinput.input():
        board = line.strip()
        # b.set_board(board)
        # print(f"{board}: {b.score()}")
        _score = b.Score(board)
        # print(f"{board}: {score}")
        n += 1
    end_s = time.time()
    elapsed_s = end_s - start_s
    rate = n / elapsed_s
    sys.stderr.write(f"{n} boards in {elapsed_s:.2f}s = {rate:.2f} boards/s\n")


if __name__ == "__main__":
    main()
