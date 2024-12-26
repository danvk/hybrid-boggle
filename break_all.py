#!/usr/bin/env python

import random
import sys
from dataclasses import dataclass
import time
from typing import Sequence

from tqdm import tqdm

from example import Trie, BucketBoggler


@dataclass
class BreakDetails:
    max_depth: int
    num_reps: int
    start_time_s: float
    elapsed_s: float
    failures: list[str]

SPLIT_ORDER = ( 4, 5, 3, 1, 7, 0, 2, 6, 8 )

class Breaker:
    def __init__(self, boggler: BucketBoggler, best_score):
        self.bb = boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0

    def FromId(self, classes, idx: int):
        board = from_board_id(classes, idx)
        return self.bb.ParseBoard(board)

    def Break(self) -> BreakDetails:
        self.details_ = BreakDetails(
            max_depth=0,
            num_reps=0,
            elapsed_s=0.0,
            start_time_s=0.0,
            failures=[],
        )
        self.elim_ = 0
        self.orig_reps_ = self.bb.NumReps()
        self.details_.start_time_s = time.time()
        self.AttackBoard()
        self.details_.elapsed_s = time.time() - self.details_.start_time_s
        self.details_.num_reps = self.orig_reps_
        # TODO: debug output
        return self.details_

    def PickABucket(self, level: int) -> list[str]:
        pick = -1
        splits = []

        # TODO: lots of comments in C++ source with ideas for exploration here.
        for order in SPLIT_ORDER:
            # TODO: could do this all in Python to avoid C++ <-> Py
            if len(self.bb.Cell(order)) > 1:
                pick = order
                break

        cell = self.bb.Cell(pick)
        cell_len = len(cell)
        if cell_len == 26:
            # TODO: is this ever useful?
            splits = ['aeiou', 'sy', 'bdfgjkmpvwxzq', 'chlnrt']
        elif cell_len >= 9:
            splits = [''.join(split) for split in even_split(cell, 4)]
        else:
            splits = [*cell]

        return pick, splits

    def SplitBucket(self, level: int) -> None:
        cell, splits = self.PickABucket(level)
        if cell == -1:
            # it's just a board
            board = self.bb.as_string().replace(' ', '')
            print(f"Unable to break board: {board}")
            self.details_.failures.append(board)
            return

        bd = self.bb.as_string().split(' ')
        for i, split in enumerate(splits):
            bd[cell] = split
            # TODO: C++ version uses ParseBoard() + Cell() here.
            assert self.bb.ParseBoard(' '.join(bd))
            self.AttackBoard(level + 1, i + 1, len(splits))

    def AttackBoard(self, level: int = 0, num: int = 1, out_of: int = 1) -> None:
        # TODO: debug output
        # reps = self.bb.NumReps()
        if self.bb.UpperBound(self.best_score) <= self.best_score:
            self.elim_ += self.bb.NumReps()
            self.details_.max_depth = max(self.details_.max_depth, level)
        else:
            self.SplitBucket(level)


# TODO: there's probably a more concise way to express this.
def even_split[T](xs: Sequence[T], num_buckets: int) -> list[list[T]]:
    splits = [[]]
    length = len(xs)
    for i, x in enumerate(xs):
        if num_buckets * i >= (len(splits) * length):
            splits.append([])
        splits[-1].append(x)
    return splits


def from_board_id(classes: list[str], idx: int) -> str:
    num_classes = len(classes)
    board: list[str] = []
    left = idx
    for i in range(0, 9):
        board.append(classes[left % num_classes])
        left //= num_classes
    assert left == 0
    return ' '.join(board)


def board_id(bd: list[list[int]], num_classes: int) -> int:
    id = 0
    for i in range(8, -1, -1):
        id *= num_classes
        id += bd[i//3][i%3]
    return id


def swap(ary, a, b):
    ax, ay = a
    bx, by = b
    ary[ax][ay], ary[bx][by] = ary[bx][by], ary[ax][ay]


# TODO: can probably express this all more concisely in Python
def is_canonical(num_classes: int, idx: int):
    if idx < 0:
        return False
    bd = [[0 for _x in range(0, 3)] for _y in range(0, 3)]
    left = idx
    for i in range(0, 9):
        bd[i//3][i%3] = left % num_classes
        left //= num_classes
    assert left == 0

    for rot in (0, 1):
        # ABC    CBA
        # DEF -> FED
        # GHI    IHG
        for i in range(0, 3):
            swap(bd, (0, i), (2, i))
        if board_id(bd, num_classes) < idx:
            return False

        # CBA    IHG
        # FED -> FED
        # IHG    CBA
        for i in range(0, 3):
            swap(bd, (i, 0), (i, 2))
        if board_id(bd, num_classes) < idx:
            return False

        # IHG    GHI
        # FED -> DEF
        # CBA    ABC
        for i in range(0, 3):
            swap(bd, (0, i), (2, i))
        if board_id(bd, num_classes) < idx:
            return False

        if rot == 1:
            break

        # GHI    ABC    ADG
        # DEF -> DEF -> BEH
        # ABC    GHI    CFI
        for i in range(0, 3):
            swap(bd, (i, 0), (i, 2))
        for i in range(0, 3):
            for j in range(0, i):
                swap(bd, (i, j), (j, i))

        if board_id(bd, num_classes) < idx:
            return False

    return True


def main():
    (_, classes_str, score_str, dict_file) = sys.argv
    best_score = int(score_str)
    assert best_score > 0
    t = Trie.CreateFromFile(dict_file)
    assert t
    classes = classes_str.split(' ')
    num_classes = len(classes)
    max_index = num_classes ** 9
    print(classes)
    print(max_index)

    bb = BucketBoggler(t)
    breaker = Breaker(bb, best_score)

    # This gets a more useful, accurate error bar than filter inside the main loop.
    canonical_indices = [
        idx for idx in range(0, max_index) if is_canonical(num_classes, idx)
    ]
    random.shuffle(canonical_indices)

    num_non_canonical = 0
    good_boards = []
    for idx in tqdm(canonical_indices):
        breaker.FromId(classes, idx)
        details = breaker.Break()
        if details.failures:
            for failure in details.failures:
                print(f"Found unbreakable board: {failure}")
            good_boards += details.failures

    print(f"Non-canonical boards: {num_non_canonical} / {max_index}")
    print("All failures:")
    print("\n".join(good_boards))

if __name__ == "__main__":
    main()
