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
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.split_order import SPLIT_ORDER


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
    n_bound: int


class HybridTreeBreaker:
    """This uses force_cell at the top of the tree and score_with_forces at the bottom.

    This strikes a good balance of allocating memory only when it will save a lot of CPU.
    """

    def __init__(
        self,
        etb: OrderlyTreeBuilder,
        ungrouped_boggler: PyBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        switchover_level: int | list[tuple[int, int]],
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
            freed_nodes=0,
            free_time_s=0.0,
            n_bound=0,
        )
        self.mark = 1  # New mark for a fresh EvalTree
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
            # TODO: this crashes in C++, which no longer has an EvalNode::unique_node_count method.
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

        self.attack_tree(tree, 1, [], arena)

        self.details_.elapsed_s = time.time() - start_time_s
        self.details_.total_nodes = arena.num_nodes()
        return self.details_

    def attack_tree(
        self,
        tree: EvalNode,
        level: int,
        choices: list[tuple[int, int]],
        arena,
    ) -> None:
        if tree.bound <= self.best_score:
            self.details_.elim_level[level] += 1
        elif level >= self.switchover_level:
            self.switch_to_score(tree, level, choices, arena)
        else:
            self.force_and_filter(tree, level, choices, arena)

    def force_and_filter(
        self,
        tree: EvalNode,
        level: int,
        choices: list[tuple[int, int]],
        arena,
    ) -> None:
        # choices list parallels split_order
        assert len(choices) < len(self.cells)

        cell = self.split_order[len(choices)]
        num_lets = len(self.cells[cell])

        start_s = time.time()
        self.mark += 1
        trees = tree.orderly_force_cell(
            cell,
            num_lets,
            arena,
        )
        self.details_.secs_by_level[level] += time.time() - start_s
        # self.details_.bounds[level] = tree.bound

        if not isinstance(trees, list):
            print("choice was not really a choice")
            tagged_trees = [(0, trees)]
        else:
            assert len(trees) == num_lets
            tagged_trees = enumerate(trees)

        choices.append(None)
        for letter, tree in tagged_trees:
            if not tree:
                continue  # TODO: how does this happen?
            choices[-1] = (cell, letter)
            self.attack_tree(tree, level + 1, choices, arena)
        choices.pop()

    def switch_to_score(
        self, tree: EvalNode, level: int, choices: list[tuple[int, int]], arena
    ) -> None:
        start_s = time.time()
        remaining_cells = self.split_order[len(choices) :]
        # TODO: make this just return the boards
        self.details_.n_bound += 1
        # print(choices, tree.bound)
        score_boards, bound_level, elim_level = tree.orderly_bound(
            self.best_score, self.cells, remaining_cells, choices
        )
        # for i, ev in enumerate(elim_level):
        #     bv = bound_level[i]
        #     self.details_.bound_elim_level[i + len(choices)] += ev
        #     self.details_.bound_level[i + len(choices)] += bv
        # print(time.time() - start_s, seq, tree.bound, this_failures)
        boards_to_test = [board for _score, board in score_boards]
        elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level] += elapsed_s

        if not boards_to_test:
            return

        if self.log_breaker_progress:
            print(f"Found {len(boards_to_test)} to test.")

        self.details_.boards_to_test += len(boards_to_test)
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
        self.details_.expanded_to_test += n_expanded
        if self.log_breaker_progress and self.rev_letter_grouping:
            print(f"Evaluated {n_expanded} boards.")
