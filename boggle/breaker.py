import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence

from cpp_boggle import BucketBoggler33, BucketBoggler34, BucketBoggler44

from boggle.eval_tree import EvalNode, EvalTreeBoggler

type BucketBoggler = BucketBoggler33 | BucketBoggler34 | BucketBoggler44


@dataclass
class BreakDetails:
    max_depth: int
    num_reps: int
    start_time_s: float
    elapsed_s: float
    failures: list[str]
    elim_level: Counter[int]
    by_level: Counter[int]
    secs_by_level: defaultdict[int, float]
    root_score_bailout: tuple[int, int]


class IBucketBreaker:
    """Break by recursively splitting cells and evaluating with ibuckets.

    This is simple and allocates no memory, but does lots of repeated work.
    """

    def __init__(
        self,
        boggler: BucketBoggler,
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

    def Break(self) -> BreakDetails:
        self.details_ = BreakDetails(
            max_depth=0,
            num_reps=0,
            elapsed_s=0.0,
            start_time_s=0.0,
            failures=[],
            by_level=Counter(),
            elim_level=Counter(),
            secs_by_level=defaultdict(float),
            root_score_bailout=None,
        )
        self.elim_ = 0
        self.orig_reps_ = self.bb.NumReps()
        self.details_.start_time_s = time.time()
        self.AttackBoard()

        self.details_.elapsed_s = time.time() - self.details_.start_time_s
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
            self.details_.root_score_bailout = (ub, self.bb.Details().bailout_cell)
        if ub <= self.best_score:
            self.elim_ += self.bb.NumReps()
            self.details_.max_depth = max(self.details_.max_depth, level)
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


class HybridTreeBreaker:
    """This uses force_cell at the top of the tree and score_with_forces at the bottom.

    This strikes a good balance of allocating memory only when it will save a lot of CPU.
    """

    def __init__(
        self,
        boggler: EvalTreeBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        # TODO: ideally this should depend on the node_count of the tree.
        switchover_level: int,
    ):
        self.etb = boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]
        self.switchover_level = switchover_level

    def SetBoard(self, board: str):
        return self.etb.ParseBoard(board)

    def Break(self) -> BreakDetails:
        # TODO: this is kind of roundabout
        self.cells = self.etb.as_string().split(" ")
        self.details_ = BreakDetails(
            max_depth=0,
            num_reps=0,
            elapsed_s=0.0,
            start_time_s=0.0,
            failures=[],
            by_level=Counter(),
            elim_level=Counter(),
            secs_by_level=defaultdict(float),
            root_score_bailout=None,
        )
        self.elim_ = 0
        self.orig_reps_ = self.etb.NumReps()
        self.details_.start_time_s = time.time()
        tree = self.etb.BuildTree()
        self.details_.secs_by_level[0] += time.time() - self.details_.start_time_s
        self.AttackTree(tree, 0, [None for _ in self.cells])
        self.details_.elapsed_s = time.time() - self.details_.start_time_s
        self.details_.num_reps = self.orig_reps_
        # TODO: debug output
        return self.details_

    def PickABucket(self, tree: EvalNode) -> int:
        pick = -1
        choice_mask = tree.choice_mask
        for order in self.split_order:
            if choice_mask & (1 << order):
                pick = order
                break

        return pick

    def SplitBucket(self, tree: EvalNode, level: int, choices: list[str]) -> None:
        cell = self.PickABucket(tree)
        if cell == -1:
            # it's just a board
            # TODO: evaluate this as a regular board
            board = "".join(choices)
            print(f"Unable to break board {board}: {tree.bound}")
            self.details_.failures.append(board)
            return

        n = len(self.cells[cell])

        start_s = time.time()
        trees = tree.force_cell(cell, n)
        self.details_.secs_by_level[level] += time.time() - start_s

        if isinstance(trees, EvalNode):
            print("choice was not really a choice")
            tagged_trees = [("*", trees)]
        else:
            assert len(trees) == n
            tagged_trees = zip(self.cells[cell], trees)

        for letter, tree in tagged_trees:
            choices[cell] = letter
            self.AttackTree(tree, level + 1, choices)
        choices[cell] = None

    def AttackTree(
        self,
        tree: EvalNode,
        level: int,
        choices: list[str],
    ) -> None:
        self.details_.by_level[level] += 1
        ub = tree.bound
        if ub <= self.best_score:
            # self.elim_ += self.ebb.NumReps()
            self.details_.max_depth = max(self.details_.max_depth, level)
            self.details_.elim_level[level] += 1
        else:
            if level >= self.switchover_level:
                score_choices = [
                    -1 if ch is None else self.cells[i].index(ch)
                    for i, ch in enumerate(choices)
                ]
                self.SplitBucketScore(tree, level, score_choices)
            else:
                self.SplitBucket(tree, level, choices)

    # These methods come from TreeScoreBreaker
    def AttackTreeScore(self, tree: EvalNode, level: int, choices: list[int]) -> None:
        self.details_.by_level[level] += 1
        start_s = time.time()
        ub = tree.score_with_forces(choices)
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level] += elapsed_s
        if ub <= self.best_score:
            # self.elim_ += self.bb.NumReps()
            self.details_.max_depth = max(self.details_.max_depth, level)
            self.details_.elim_level[level] += 1
        else:
            self.SplitBucketScore(tree, level, choices)

    def SplitBucketScore(self, tree: EvalNode, level: int, choices: list[int]) -> None:
        cell = self.PickABucketScore(choices)

        if cell == -1:
            # it's just a board
            board = "".join(self.cells[cell][idx] for cell, idx in enumerate(choices))
            print(f"Unable to break board: {board}")
            self.details_.failures.append(board)
            return

        for idx, letter in enumerate(self.cells[cell]):
            choices[cell] = idx
            self.AttackTreeScore(tree, level + 1, choices)
        choices[cell] = -1

    def PickABucketScore(self, choices: list[int]) -> int:
        for order in self.split_order:
            if choices[order] == -1:
                return order
        return -1


def print_details(d: BreakDetails):
    print(f"max_depth: {d.max_depth}")
    print(f"num_reps: {d.num_reps}")
    print(f"elapsed_s: {d.elapsed_s}")
    print(f"root score: {d.root_score_bailout}")
    print(f"failures: {d.failures}")
    print("by_level:")
    for k in sorted(d.by_level.keys()):
        elim = d.elim_level[k]
        ev = d.by_level[k]
        print(f"  {k:2d}: {elim} broken ({ev} evals)")
    print("secs_by_level:")
    total_s = sum(d.secs_by_level.values())
    for k, v in sorted(d.secs_by_level.items()):
        print(f"  {k:2d}: {v:.4f} / {v / total_s:.2%}")


def merge_details(a: BreakDetails, b: BreakDetails) -> BreakDetails:
    return BreakDetails(
        max_depth=max(a.max_depth, b.max_depth),
        num_reps=a.num_reps + b.num_reps,
        start_time_s=a.start_time_s,
        elapsed_s=a.elapsed_s + b.elapsed_s,
        failures=a.failures + b.failures,
        elim_level=a.elim_level + b.elim_level,
        by_level=a.by_level + b.by_level,
        secs_by_level=defaultdict(
            float,
            {
                k: a.secs_by_level[k] + b.secs_by_level[k]
                for k in set(a.secs_by_level) | set(b.secs_by_level)
            },
        ),
        root_score_bailout=None,
    )


SPLIT_ORDER_33 = (4, 5, 3, 1, 7, 0, 2, 6, 8)


def to_idx(x, y):
    return x * 4 + y


SPLIT_ORDER_34 = tuple(
    to_idx(x, y)
    for x, y in (
        (1, 1),
        (1, 2),  # middle
        (0, 1),
        (2, 1),
        (0, 2),
        (2, 2),  # middle sides
        (1, 0),
        (1, 3),  # top/bottom middle
        (0, 0),
        (2, 0),
        (0, 3),
        (2, 3),  # corners
    )
)
assert len(SPLIT_ORDER_34) == 12

SPLIT_ORDER_44 = tuple(
    to_idx(x, y)
    for x, y in (
        (1, 1),
        (1, 2),
        (2, 1),
        (2, 2),  # middle
        (0, 1),
        (3, 1),
        (0, 2),
        (3, 2),  # middle sides
        (1, 0),
        (1, 3),
        (2, 0),
        (2, 3),  # top/bottom middle
        (0, 0),
        (3, 0),
        (0, 3),
        (3, 3),  # corners
    )
)
assert len(SPLIT_ORDER_44) == 16
assert len(set(SPLIT_ORDER_44)) == 16

SPLIT_ORDER = {
    (3, 3): SPLIT_ORDER_33,
    (3, 4): SPLIT_ORDER_34,
    (4, 4): SPLIT_ORDER_44,
}
