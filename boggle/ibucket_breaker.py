"""Break a board class (prove it has no boards with >P points) using ibuckets.

This is the 2009 strategy, as described at:
https://www.danvk.org/2025/02/10/boggle34.html#how-did-i-find-the-optimal-3x3-board-in-2009

This strategy uses almost no memory, but it's considerably slower than HybridTreeBreaker.
"""

import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence

from boggle.breaker import BreakDetails
from boggle.ibuckets import PyBucketBoggler
from boggle.split_order import SPLIT_ORDER


@dataclass
class IBucketBreakDetails(BreakDetails):
    by_level: Counter[int]

    def asdict(self):
        d = super().asdict()
        d["by_level"] = dict(self.by_level.items())
        return d


class IBucketBreaker:
    """Break by recursively splitting cells and evaluating with ibuckets.

    This is simple and allocates no memory, but does lots of repeated work.
    """

    def __init__(
        self,
        boggler: PyBucketBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        num_splits: int,
    ):
        self.bb = boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]
        self.num_splits = num_splits

    def SetBoard(self, board: str):
        return self.bb.ParseBoard(board)

    def Break(self) -> IBucketBreakDetails:
        self.details_ = IBucketBreakDetails(
            num_reps=0,
            elapsed_s=0.0,
            failures=[],
            by_level=Counter(),
            elim_level=Counter(),
            secs_by_level=defaultdict(float),
            # root_score_bailout=None,
        )
        self.elim_ = 0
        self.orig_reps_ = self.bb.NumReps()
        start_time_s = time.time()
        self.AttackBoard()

        self.details_.elapsed_s = time.time() - start_time_s
        self.details_.num_reps = self.orig_reps_
        # TODO: debug output
        return self.details_

    def PickABucket(self, level: int):
        pick = -1
        splits = []

        cells = self.bb.as_string().split(" ")

        # TODO: lots of comments in C++ source with ideas for exploration here.
        for order in self.split_order:
            if len(cells[order]) > 1:
                pick = order
                break

        if pick == -1:
            return pick, splits, cells

        cell = cells[pick]
        cell_len = len(cell)
        if cell_len == 26:
            # TODO: is this ever useful?
            splits = ["bdfgjqvwxz", "aeiou", "lnrsy", "chkmpt"]
            # splits = ["aeiou", "sy", "bdfgjkmpvwxzq", "chlnrt"]
        elif cell_len >= 9:
            splits = ["".join(split) for split in even_split(cell, self.num_splits)]

        else:
            splits = [*cell]

        return pick, splits, cells

    def SplitBucket(self, level: int) -> None:
        cell, splits, cells = self.PickABucket(level)
        if cell == -1:
            # it's just a board
            board = "".join(cells)
            # print(f"Unable to break board: {board}")
            self.details_.failures.append(board)
            return

        for i, split in enumerate(splits):
            bd = [*cells]
            bd[cell] = split
            # C++ version uses ParseBoard() + Cell() here.
            assert self.bb.ParseBoard(" ".join(bd))
            self.AttackBoard(level + 1, i + 1, len(splits))

    def AttackBoard(self, level: int = 0, num: int = 1, out_of: int = 1) -> None:
        # TODO: debug output
        # reps = self.bb.NumReps()

        self.details_.by_level[level] += 1
        start_s = time.time()
        ub = self.bb.UpperBound(self.best_score)
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level] += elapsed_s
        if level == 0:
            # self.details_.root_score_bailout = (ub, self.bb.Details().bailout_cell)
            self.details_.root_bound = ub
        if ub <= self.best_score:
            self.elim_ += self.bb.NumReps()
            # self.details_.max_depth = max(self.details_.max_depth, level)
            self.details_.elim_level[level] += 1
        else:
            self.SplitBucket(level)


# TODO: there's probably a more concise way to express this.
# Or maybe not https://stackoverflow.com/a/54802737/388951
def even_split[T](xs: Sequence[T], num_buckets: int) -> list[list[T]]:
    splits = [[]]
    length = len(xs)
    for i, x in enumerate(xs):
        if num_buckets * i >= (len(splits) * length):
            splits.append([])
        splits[-1].append(x)
    return splits
