# Bucketed Boggle in Python

import math
from dataclasses import dataclass

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_lookup_table


@dataclass
class ScoreDetails:
    max_nomark: int
    sum_union: int
    bailout_cell: int


class PyBucketBoggler:
    trie_: PyTrie
    bd_: list[str]
    runs_: int
    used_: int
    details_: ScoreDetails
    neighbors: list[list[int]]
    collect_words: bool
    cells: list[int]

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        self.trie_ = trie
        self.runs_ = 0
        self.used_ = 0
        self.bd_ = []
        self.details_ = None
        self.neighbors = NEIGHBORS[dims]
        self.dims = dims
        self.collect_words = False
        self.words = None
        self.lookup_table = None
        self.cells = []
        self.target_word = None

    def ParseBoard(self, board: str):
        cells = board.split(" ")
        if len(cells) != self.dims[0] * self.dims[1] or not all(cells):
            return False
        # '.' is an explicit "don't go here," which is useful for testing.
        self.bd_ = [b if b != "." else "" for b in cells]
        return True

    def NumReps(self) -> int:
        return math.prod(len(cell) for cell in self.bd_)

    def as_string(self):
        return " ".join(b if b else "." for b in self.bd_)

    def Details(self):
        return self.details_

    def UpperBound(self, bailout_score: int):
        self.details_ = ScoreDetails(0, 0, -1)
        self.used_ = 0
        self.runs_ = self.trie_.Mark() + 1
        self.trie_.SetMark(self.runs_)
        self.words = None
        if self.collect_words:
            self.words = []
            if not self.lookup_table:
                self.lookup_table = make_lookup_table(self.trie_)

        for i in range(len(self.bd_)):
            max_score = self.DoAllDescents(i, 0, self.trie_)
            self.details_.max_nomark += max_score
            if (
                self.details_.max_nomark > bailout_score
                and self.details_.sum_union > bailout_score
            ):
                self.details_.bailout_cell = i
                break
        return min(self.details_.max_nomark, self.details_.sum_union)

    def DoAllDescents(self, idx: int, length: int, t: PyTrie):
        max_score = 0
        for char in self.bd_[idx]:
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                tscore = self.DoDFS(
                    idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                )
                max_score = max(max_score, tscore)
        return max_score

    def DoDFS(self, i: int, length: int, t: PyTrie):
        score = 0
        self.used_ ^= 1 << i

        for idx in self.neighbors[i]:
            if not self.used_ & (1 << idx):
                score += self.DoAllDescents(idx, length, t)

        if t.IsWord():
            word_score = SCORES[length]
            score += word_score
            if self.collect_words:
                word = self.lookup_table[t]
                self.words.append(word)
            if t.Mark() != self.runs_:
                self.details_.sum_union += word_score
                t.SetMark(self.runs_)

        self.used_ ^= 1 << i
        return score


class PyBucketBoggler22(PyBucketBoggler):
    def __init__(self, trie: PyTrie):
        super().__init__(trie, (2, 2))


class PyBucketBoggler23(PyBucketBoggler):
    def __init__(self, trie: PyTrie):
        super().__init__(trie, (2, 3))
