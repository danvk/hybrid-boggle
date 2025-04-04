"""Break a board class (prove it has no boards with >P points) using EvalTree.

This is the 2025 strategy, as described at:
https://www.danvk.org/2025/02/13/boggle2025.html

This performs several "force" operations on the tree to create smaller subtrees and
reduce the bound. After a few of these (determined by "switchover_score"),
it stops modifying the tree and does a DFS on the remaining choices until the board class
is fully broken.

Forcing cells uses memory to make the final bounding DFS dramatically faster, especially
for complex, hard-to-break board classes. On the other hand, forcing too many cells
wastes memory and is slower than the DFS (orderly_bound).
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
        d["depth"] = dict(self.depth.items())
        return d


@dataclass
class HybridBreakDetails(BreakDetails):
    bounds: dict[int, int]
    nodes: dict[int, int]
    depth: dict[int, int]
    boards_to_test: int
    expanded_to_test: int
    init_nodes: int
    total_nodes: int
    freed_nodes: int
    free_time_s: float
    n_bound: int
    n_force: int


class HybridTreeBreaker:
    """This uses orderly_force_cell at the top of the tree and orderly_bound at the bottom.

    This strikes a good balance of allocating memory only when it will save a lot of CPU.
    """

    def __init__(
        self,
        etb: OrderlyTreeBuilder,
        ungrouped_boggler: PyBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        switchover_score: int,
        log_breaker_progress: bool,
        letter_grouping: str = "",
        max_depth=None,
    ):
        self.etb = etb
        self.boggler = ungrouped_boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]
        self.switchover_score = switchover_score
        self.switchover_depth = max_depth or (dims[0] * dims[1] - 4)
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
            boards_to_test=0,
            expanded_to_test=0,
            init_nodes=0,
            depth=Counter(),
            nodes={},
            total_nodes=0,
            freed_nodes=0,
            free_time_s=0.0,
            n_bound=0,
            n_force=0,
        )
        self.mark = 1  # New mark for a fresh EvalTree
        self.elim_ = 0
        self.orig_reps_ = self.details_.num_reps = self.etb.NumReps()
        start_time_s = time.time()
        arena = self.etb.create_arena()
        tree = self.etb.BuildTree(arena)
        # num_children, num_nodes, num_singles = size_stats(tree)
        # print(num_children)
        # print(num_singles)
        # print(num_nodes)
        num_nodes = arena.num_nodes()
        if self.log_breaker_progress:
            print(f"root {tree.bound=}, {num_nodes} nodes")

        self.details_.secs_by_level[0] += time.time() - start_time_s
        self.details_.bounds[0] = tree.bound
        self.details_.init_nodes = arena.num_nodes()
        self.details_.nodes[0] = self.details_.init_nodes

        self.attack_tree(tree, 1, [])

        self.details_.elapsed_s = time.time() - start_time_s
        self.details_.total_nodes = arena.num_nodes()
        return self.details_

    def attack_tree(
        self,
        tree: EvalNode,
        level: int,
        choices: list[tuple[int, int]],
    ) -> None:
        if tree.bound <= self.best_score:
            self.details_.elim_level[level] += 1
        elif tree.bound <= self.switchover_score or level > self.switchover_depth:
            self.switch_to_score(tree, level, choices)
        else:
            self.force_and_filter(tree, level, choices)

    def force_and_filter(
        self,
        tree: EvalNode,
        level: int,
        choices: list[tuple[int, int]],
    ) -> None:
        # choices list parallels split_order
        assert len(choices) < len(self.cells)

        cell = self.split_order[len(choices)]
        num_lets = len(self.cells[cell])

        start_s = time.time()
        self.details_.n_force += 1
        arena = self.etb.create_arena()
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
                continue  # this can happen on truly dead-end paths
            choices[-1] = (cell, letter)
            self.attack_tree(tree, level + 1, choices)
        choices.pop()

    def switch_to_score(
        self, tree: EvalNode, level: int, choices: list[tuple[int, int]]
    ) -> None:
        start_s = time.time()
        remaining_cells = self.split_order[len(choices) :]
        # TODO: make this just return the boards
        self.details_.n_bound += 1
        self.details_.depth[level] += 1
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
        bound_elapsed_s = time.time() - start_s
        self.details_.secs_by_level[level] += bound_elapsed_s

        if not boards_to_test:
            if self.log_breaker_progress:
                print(
                    f"{self.details_.n_bound} {choices} -> {tree.bound=} {bound_elapsed_s:.03} s"
                )
            return

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

        if self.log_breaker_progress:
            print(
                f"{self.details_.n_bound} {choices} -> {tree.bound=} {bound_elapsed_s:.03}s / test {n_expanded} in {elapsed_s:.03}s"
            )
