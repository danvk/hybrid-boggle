import dataclasses
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence

from cpp_boggle import (
    BucketBoggler33,
    BucketBoggler34,
    BucketBoggler44,
    create_eval_node_arena,
)

from boggle.boggler import PyBoggler
from boggle.eval_tree import (
    EvalNode,
    EvalTreeBoggler,
    create_eval_node_arena_py,
)

type BucketBoggler = BucketBoggler33 | BucketBoggler34 | BucketBoggler44


@dataclass
class BreakDetails:
    num_reps: int
    elapsed_s: float
    failures: list[str]
    elim_level: Counter[int]
    secs_by_level: defaultdict[int, float]

    def asdict(self):
        d = dataclasses.asdict(self)
        d["elim_level"] = dict(self.elim_level.items())
        d["secs_by_level"] = dict(self.secs_by_level.items())
        return d


@dataclass
class IBucketBreakDetails(BreakDetails):
    by_level: Counter[int]

    def asdict(self):
        d = super().asdict()
        d["by_level"] = dict(self.by_level.items())
        return d


@dataclass
class HybridBreakDetails(BreakDetails):
    sum_union: int
    bounds: dict[int, int]
    boards_to_test: int
    init_nodes: int
    total_nodes: int
    num_filtered: dict[int, int]


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


class HybridTreeBreaker:
    """This uses lift_choice at the top of the tree and score_with_forces at the bottom.

    This strikes a good balance of allocating memory only when it will save a lot of CPU.
    """

    def __init__(
        self,
        etb: EvalTreeBoggler,
        boggler: PyBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        # TODO: ideally this should depend on the node_count of the tree.
        switchover_level: int,
    ):
        self.etb = etb
        self.boggler = boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]
        self.switchover_level = switchover_level
        # TODO: EvalTreeBoggler could have a method to produce an arena.
        self.create_arena = (
            create_eval_node_arena_py
            if isinstance(boggler, EvalTreeBoggler)
            else create_eval_node_arena
        )

    def SetBoard(self, board: str):
        return self.etb.ParseBoard(board)

    def Break(self) -> HybridBreakDetails:
        # TODO: this is kind of roundabout
        self.cells = self.etb.as_string().split(" ")
        self.num_letters = [len(c) for c in self.cells]
        self.details_ = HybridBreakDetails(
            num_reps=0,
            elapsed_s=0.0,
            failures=[],
            elim_level=Counter(),
            secs_by_level=defaultdict(float),
            bounds={},
            sum_union=0,
            boards_to_test=0,
            init_nodes=0,
            total_nodes=0,
            num_filtered={},
        )
        self.mark = 1  # New mark for a fresh EvalTree
        self.lifted_cells_ = []
        self.elim_ = 0
        self.orig_reps_ = self.details_.num_reps = self.etb.NumReps()
        start_time_s = time.time()
        arena = self.create_arena()
        tree = self.etb.BuildTree(arena, dedupe=True)
        self.details_.secs_by_level[0] += time.time() - start_time_s
        self.details_.bounds[0] = tree.bound
        self.details_.sum_union = self.etb.Details().sum_union
        self.details_.init_nodes = arena.num_nodes()

        self.AttackTree(tree, 1, arena)
        self.details_.elapsed_s = time.time() - start_time_s
        self.details_.total_nodes = arena.num_nodes()
        return self.details_

    def pick_cell(self, tree: EvalNode) -> int:
        for cell in self.split_order:
            if cell not in self.lifted_cells_:
                return cell
        return -1

    def lift_and_filter(self, tree: EvalNode, level: int, arena) -> None:
        cell = self.pick_cell(tree)
        if cell == -1:
            self.try_remaining_boards(tree)
            return

        num_lets = len(self.cells[cell])

        start_s = time.time()
        self.mark += 1
        tree = tree.lift_choice(
            cell, num_lets, arena, self.mark, dedupe=True, compress=True
        )
        self.details_.secs_by_level[level] += time.time() - start_s
        self.details_.bounds[level] = tree.bound
        self.lifted_cells_.append(cell)
        # with open(f"/tmp/subtrees-{level}.txt", "w") as out:
        #     for t, seq in tree.max_subtrees():
        #         choices = ["." for _ in self.cells]
        #         for cell, letter in seq:
        #             choices[cell] = self.cells[cell][letter]
        #         board = "".join(choices)
        #         out.write(f"{board}\n")
        # print(f"{level} num max_subtrees:", sum(1 for _ in tree.max_subtrees()))
        # assert includes_board(
        #     tree.max_subtrees(), self.cells, "perslatesind"
        # ), f"Missed on {level}"

        if tree.bound >= self.best_score:
            n_filtered = tree.filter_below_threshold(self.best_score)
            if n_filtered:
                self.details_.num_filtered[level] = n_filtered
            # print(f"f -> {cell=} {tree.bound=}, {tree.unique_node_count()} unique nodes")
        # print(
        #     f"{level=} {cell=} {tree.bound=}, {tree.unique_node_count()} unique nodes"
        # )

        self.AttackTree(tree, level + 1, arena)

    def AttackTree(self, tree: EvalNode, level: int, arena) -> None:
        ub = tree.bound
        if ub <= self.best_score:
            # self.elim_ += self.ebb.NumReps()
            # self.details_.max_depth = max(self.details_.max_depth, level)
            self.details_.elim_level[level] += 1
        else:
            if level >= self.switchover_level:
                self.switch_to_score(tree, level, arena)
            else:
                self.lift_and_filter(tree, level, arena)

    def switch_to_score(self, tree: EvalNode, level: int, arena) -> None:
        # This reduces the amount of time we use max memory, but it's a ~5% perf hit.
        # start_s = time.time()
        # arena.mark_and_sweep(tree)
        # elapsed_s = time.time() - start_s
        # self.details_.secs_by_level[f"{level:02}mark_and_sweep"] += elapsed_s
        start_s = time.time()
        # TODO: move this call into bound_remaining_boards()
        tree.set_choice_point_mask(self.num_letters)
        elapsed_s = time.time() - start_s
        # self.details_.secs_by_level[f"{level:02}set_point_choice_mask"] += elapsed_s
        start_s = time.time()
        boards_to_test = tree.bound_remaining_boards(
            self.cells, self.best_score, self.split_order
        )
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level] += elapsed_s

        if not boards_to_test:
            return

        # print(f"{len(boards_to_test)=}")
        # with open("/tmp/boards-to-test.txt", "w") as out:
        #     for board in boards_to_test:
        #         out.write(f"{board}\n")x

        self.details_.boards_to_test = len(boards_to_test)
        start_s = time.time()
        for board in boards_to_test:
            true_score = self.boggler.score(board)
            # print(choices, board, tree.bound, "->", true_score)
            if true_score >= self.best_score:
                print(f"Unable to break board: {board} {true_score}")
                self.details_.failures.append(board)
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level + 1] += elapsed_s

    def try_remaining_boards(self, tree: EvalNode):
        """We have a fully-lifted tree that isn't broken. Try all boards explicitly."""
        # print("num max_subtrees:", sum(1 for _ in tree.max_subtrees()))
        # assert includes_board(tree.max_subtrees(), self.cells, "perslatesind")
        for t, seq in tree.max_subtrees():
            choices = [-1 for _ in self.cells]
            for cell, letter in seq:
                assert choices[cell] == -1
                choices[cell] = letter
            board = "".join(self.cells[cell][idx] for cell, idx in enumerate(choices))
            true_score = self.boggler.score(board)
            # print(choices, board, t.bound, "->", true_score)
            if true_score >= self.best_score:
                print(f"Unable to break board: {board} {true_score}")
                self.details_.failures.append(board)


# Do the max_subtrees include a particular board?
# Helpful for tracking down incorrect omissions.
def includes_board(max_subtrees, cells: list[str], board: str):
    for t, seq in max_subtrees:
        all_match = True
        for cell, letter in seq:
            if cells[cell][letter] != board[cell]:
                all_match = False
                break
        if all_match:
            return True
    return False


def print_details(d: IBucketBreakDetails):
    # print(f"max_depth: {d.max_depth}")
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
        print(f"  {k}: {v:.4f} / {v / total_s:.2%}")
        # print(f"  {k:2d}: {v:.4f} / {v / total_s:.2%}")


def merge_details(
    a: IBucketBreakDetails, b: IBucketBreakDetails
) -> IBucketBreakDetails:
    return IBucketBreakDetails(
        # max_depth=max(a.max_depth, b.max_depth),
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
        # root_score_bailout=None,
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
    (2, 2): (0, 1, 2, 3),
    (3, 3): SPLIT_ORDER_33,
    (3, 4): SPLIT_ORDER_34,
    (4, 4): SPLIT_ORDER_44,
}
