"""Break a board class (prove it has no boards with >P points) using EvalTree.

This is the 2025 strategy, as described at:
https://www.danvk.org/2025/02/13/boggle2025.html

This performs several "lift" operations on the tree to synchronize choices across
subtrees and reduce the bound. After a few of these (the number is the "switchover_level"),
it stops modifying the tree and does a DFS on the remaining choices until the board class
is fully broken (this done in "bound_remaining_boards").

Lifting uses a lot of memory but can make bound_remaining_boards dramatically faster,
especially for complex, hard-to-break board classes. On the other hand, lifting too many
times wastes memory and is slower than bound_remaining_boards. There is a sweet spot for
each board class.
"""

import dataclasses
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

from boggle.boggler import PyBoggler
from boggle.eval_tree import (
    EvalNode,
)
from boggle.letter_grouping import get_letter_map, reverse_letter_map, ungroup_letters
from boggle.split_order import SPLIT_ORDER
from boggle.tree_builder import TreeBuilder


@dataclass
class BreakDetails:
    """Details shared between hybrid and ibuckets."""

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
class HybridBreakDetails(BreakDetails):
    sum_union: int
    bounds: dict[int, int]
    nodes: dict[int, int]
    boards_to_test: int
    expanded_to_test: int
    init_nodes: int
    total_nodes: int
    freed_nodes: int
    free_time_s: float
    num_filtered: dict[int, int]


class HybridTreeBreaker:
    """This uses lift_choice at the top of the tree and score_with_forces at the bottom.

    This strikes a good balance of allocating memory only when it will save a lot of CPU.
    """

    def __init__(
        self,
        etb: TreeBuilder,
        ungrouped_boggler: PyBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        switchover_level: int | list[tuple[int, int]],
        free_after_lift: bool,
        log_breaker_progress: bool,
        letter_grouping: str = "",
    ):
        self.etb = etb
        self.boggler = ungrouped_boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]
        self.switchover_level_input = switchover_level
        self.free_after_lift = free_after_lift
        self.log_breaker_progress = log_breaker_progress
        self.rev_letter_grouping = (
            reverse_letter_map(get_letter_map(letter_grouping))
            if letter_grouping
            else None
        )

    def SetBoard(self, board: str):
        return self.etb.ParseBoard(board)

    def Break(self) -> HybridBreakDetails:
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
            expanded_to_test=0,
            init_nodes=0,
            nodes={},
            total_nodes=0,
            num_filtered={},
            freed_nodes=0,
            free_time_s=0.0,
        )
        self.mark = 1  # New mark for a fresh EvalTree
        self.lifted_cells_ = []
        self.elim_ = 0
        self.orig_reps_ = self.details_.num_reps = self.etb.NumReps()
        start_time_s = time.time()
        arena = self.etb.create_arena()
        tree = self.etb.BuildTree(arena)
        if isinstance(tree, EvalNode):
            num_nodes = tree.node_count()
        else:
            num_nodes = arena.num_nodes()
        if self.log_breaker_progress:
            self.mark += 1
            print(
                f"root {tree.bound=}, {num_nodes} nodes, {tree.unique_node_count(self.mark)} unique nodes"
            )

        if isinstance(self.switchover_level_input, int):
            self.switchover_level = self.switchover_level_input
        else:
            self.switchover_level = 0
            for level, size in self.switchover_level_input:
                if num_nodes >= size:
                    self.switchover_level = level

        self.details_.secs_by_level[0] += time.time() - start_time_s
        self.details_.bounds[0] = tree.bound
        self.details_.sum_union = self.etb.SumUnion()
        self.details_.init_nodes = arena.num_nodes()
        self.details_.nodes[0] = self.details_.init_nodes

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

        if tree.bound >= self.best_score:
            n_filtered = tree.filter_below_threshold(self.best_score)
            if n_filtered:
                self.details_.num_filtered[level] = n_filtered
        if self.log_breaker_progress:
            self.mark += 1
            count = tree.unique_node_count(self.mark)
            print(f"{level=} {cell=} {tree.bound=}, {count} unique nodes")
            self.details_.nodes[level] = count

        self.AttackTree(tree, level + 1, arena)

    def AttackTree(self, tree: EvalNode, level: int, arena) -> None:
        ub = tree.bound
        if ub <= self.best_score:
            self.details_.elim_level[level] += 1
        else:
            if level >= self.switchover_level:
                self.switch_to_score(tree, level, arena)
            else:
                self.lift_and_filter(tree, level, arena)

    def switch_to_score(self, tree: EvalNode, level: int, arena) -> None:
        # This reduces the amount of time we use max memory, but it's a ~5% perf hit.
        # start_s = time.time()
        if self.free_after_lift:
            self.mark += 1
            start_s = time.time()
            self.details_.freed_nodes = arena.mark_and_sweep(tree, self.mark)
            self.details_.free_time_s = time.time() - start_s
        start_s = time.time()
        # TODO: move this call into bound_remaining_boards()
        tree.set_choice_point_mask(self.num_letters)
        elapsed_s = time.time() - start_s
        start_s = time.time()
        boards_to_test = tree.bound_remaining_boards(
            self.cells, self.best_score, self.split_order
        )
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level] += elapsed_s

        if not boards_to_test:
            return

        if self.log_breaker_progress:
            print(f"Found {len(boards_to_test)} to test.")

        self.details_.boards_to_test = len(boards_to_test)
        start_s = time.time()
        it = (
            boards_to_test
            if not self.rev_letter_grouping
            else (
                b
                for board in boards_to_test
                for b in ungroup_letters(board, self.rev_letter_grouping)
            )
        )
        n_expanded = 0
        for board in it:
            n_expanded += 1
            true_score = self.boggler.score(board)
            # print(f"{board}: {tree.bound} -> {true_score}")
            if true_score >= self.best_score:
                print(f"Unable to break board: {board} {true_score}")
                self.details_.failures.append(board)
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level + 1] += elapsed_s
        self.details_.expanded_to_test = n_expanded
        if self.log_breaker_progress and self.rev_letter_grouping:
            print(f"Evaluated {n_expanded} boards.")

    def try_remaining_boards(self, tree: EvalNode):
        """We have a fully-lifted tree that isn't broken. Try all boards explicitly."""
        assert (
            not self.rev_letter_grouping
        ), "Full lifting with --letter_grouping is not implemented"
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
