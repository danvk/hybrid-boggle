#!/usr/bin/env python
"""Find all the words on a Boggle board using a C++ Trie."""

import fileinput
import sys
import time

from cpp_boggle import Boggler as CppBoggler, Trie as CppTrie

SCORES = (0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11)
LETTER_Q = ord("q") - ord("a")
LETTER_A = ord("a")


def idx(x: int, y: int):
    return 4 * x + y


def pos(idx: int):
    return (idx // 4, idx % 4)


NEIGHBORS = []
for i in range(0, 16):
    x, y = pos(i)
    n = []
    for dx in range(-1, 2):
        nx = x + dx
        if nx < 0 or nx > 3:
            continue
        for dy in range(-1, 2):
            ny = y + dy
            if ny < 0 or ny > 3:
                continue
            n.append(idx(nx, ny))
    NEIGHBORS.append(n)


class HybridBoggler:
    def __init__(self, trie):
        self._trie = trie
        self._runs = 0
        self._cells = [0] * 16
        self._used = [False] * 16
        self._score = 0

    def set_board(self, bd: str):
        assert len(bd) == 16
        for i, let in enumerate(bd):
            assert "a" <= let <= "z"
            self._cells[i] = ord(let) - ord("a")

    def __str__(self):
        return "".join(chr(ord("a") + let) for let in self._cells)

    def score(self):
        self._score = 0
        self._runs += 1
        t = self._trie
        for i in range(0, 16):
            c = self._cells[i]
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
                # print(Trie.ReverseLookup(self._trie, t))

        for idx in NEIGHBORS[i]:
            if not self._used[idx]:
                cc = self._cells[idx]
                d = t.Descend(cc)
                if d:
                    self.do_dfs(idx, length, d)

        self._used[i] = False


class PyTrie:
    def __init__(self):
        self.is_word = False
        self.mark = 0
        self.children = [None] * 26

    def StartsWord(self, i):
        return self.children[i] is not None

    def Descend(self, i):
        return self.children[i]

    def IsWord(self):
        return self.is_word

    def Mark(self):
        return self.mark

    def SetMark(self, mark):
        self.mark = mark

    # ---

    def SetIsWord(self):
        self.is_word = True

    def AddWord(self, word):
        if word == "":
            self.SetIsWord()
            return self
        c = ord(word[0]) - LETTER_A
        try:
            if not self.StartsWord(c):
                self.children[c] = PyTrie()
        except IndexError:
            print(c, word)
            raise
        return self.Descend(c).AddWord(word[1:])

    def Size(self):
        return (1 if self.IsWord() else 0) + sum(c.Size() for c in self.children if c)

    def NumNodes(self):
        return 1 + sum(c.NumNodes() for c in self.children if c)


def make_py_trie(dict_input: str):
    t = PyTrie()
    for word in open(dict_input):
        word = word.strip()
        t.AddWord(word)
    return t


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
