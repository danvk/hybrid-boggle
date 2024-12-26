#!/usr/bin/env python

import sys
from dataclasses import dataclass

from example import Trie, BucketBoggler


@dataclass
class BreakDetails:
    max_depth: int
    num_reps: int
    start_time_s: float
    elapsed_s: float
    failures: list[str]


class Breaker:
    def __init__(self, boggler: BucketBoggler, best_score):
        self.bb = boggler
        self.best_score = best_score

    def FromId(self, classes, idx: int):
        board = from_board_id(classes, idx)
        return self.bb.ParseBoard(board)

    def Break() -> BreakDetails:
        pass

    def PickABucket(level: int) -> list[str]:
        pass

    def SplitBucket(level: int) -> None:
        pass

    def AttackBoard(level: int, num: int, out_of: int) -> None:
        pass


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


def is_canonical(num_classes: int, idx: int):
    if idx < 0:
        return False
    bd = [[0 for x in range(0, 3)] for y in range(0, 3)]
    left = idx
    for i in range(0, 9):
        bd[i//3][i%3] = left % num_classes
        left //= num_classes
    assert left == 0
    for rot in (0, 1):
        # TODO: can probably express this all more concisely in Python
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
            for j in range(0, 3):
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
    max_index = 9 ** num_classes

    bb = BucketBoggler(t)
    breaker = Breaker(bb, best_score)

    good_boards = []
    for idx in range(0, max_index):
        if idx % 100 == 0:
            print("{idx} classes broken")
        if not is_canonical(num_classes, idx):
            continue

        breaker.FromId(classes, idx)
        details = breaker.Break()
        if details.failures:
            for failure in details.failures:
                print(f"Found unbreakable board: {failure}")
            good_boards += details.failures

    print("All failures:")
    print("\n".join(good_boards))

if __name__ == "__main__":
    main()
