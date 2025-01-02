# Bucketed Boggle in Python

import itertools
from dataclasses import dataclass

from boggle.boggle import LETTER_A, LETTER_Q, SCORES, PyTrie, reverse_lookup

PRINT_WORDS = True


def init_neighbors33():
    def idx(x: int, y: int):
        return 3 * x + y

    def pos(idx: int):
        return (idx // 3, idx % 3)

    ns: list[list[int]] = []
    for i in range(0, 9):
        x, y = pos(i)
        n = []
        for dx in range(-1, 2):
            nx = x + dx
            if nx < 0 or nx > 2:
                continue
            for dy in range(-1, 2):
                ny = y + dy
                if ny < 0 or ny > 2:
                    continue
                if nx == 0 and ny == 0:
                    continue
                n.append(idx(nx, ny))
        ns.append(n)
    return ns


NEIGHBORS = init_neighbors33()
print(NEIGHBORS)


@dataclass
class ScoreDetails:
    max_nomark: int
    sum_union: int


class PyBucketBoggler:
    trie_: PyTrie
    bd_: list[str]
    runs_: int
    used_: int
    details_: ScoreDetails

    def __init__(self, trie: PyTrie):
        self.trie_ = trie
        self.runs_ = 0
        self.used_ = 0
        self.bd_ = []
        self.details = ScoreDetails(0, 0)

    def ParseBoard(self, board: str):
        self.bd_ = board.split(" ")
        assert len(self.bd_) == 9

    def NumReps(self):
        return itertools.product(len(cell) for cell in self.bd_)

    def as_string(self):
        return " ".join(self.bd_)

    def Cell(self, i: int):
        return self.bd_[i]

    def SetCell(self, i: int, chars: str):
        self.bd_[i] = chars

    def UpperBound(self, bailout_score: int):
        self.details_ = ScoreDetails(0, 0)
        self.used_ = 0
        self.runs_ += 1
        for i in range(0, 9):
            # print(i)
            max_score = self.DoAllDescents(i, 0, self.trie_)
            self.details_.max_nomark += max_score
            if (
                self.details_.max_nomark > bailout_score
                and self.details.sum_union > bailout_score
            ):
                break
        return min(self.details_.max_nomark, self.details_.sum_union)

    def DoAllDescents(self, idx: int, length: int, t: PyTrie):
        max_score = 0
        for char in self.bd_[idx]:
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                # print(" %s" % char)
                tscore = self.DoDFS(
                    idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                )
                max_score = max(max_score, tscore)
        return max_score

    def DoDFS(self, i: int, length: int, t: PyTrie):
        score = 0
        self.used_ ^= 1 << i

        for idx in NEIGHBORS[i]:
            if not self.used_ & (1 << idx):
                score += self.DoAllDescents(idx, length, t)

        if t.IsWord():
            word_score = SCORES[length]
            score += word_score
            if PRINT_WORDS:
                word = reverse_lookup(self.trie_, t)
                print(" +%2d (%d,%d) %s" % (word_score, idx // 3, idx % 3, word))
            if t.Mark() != self.runs_:
                self.details_.sum_union += word_score
                t.SetMark(self.runs_)

        self.used_ ^= 1 << i
        return score
