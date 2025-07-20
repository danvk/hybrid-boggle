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
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

from boggle.arena import PyArena
from boggle.boggler import PyBoggler
from boggle.eval_node import SumNode
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.split_order import SPLIT_ORDER


def counter_to_array(c: Counter):
    if not c:
        return []
    m = max(c.keys())
    return [c.get(k, 0) for k in range(0, m + 1)]


def float_dict_to_array(c: defaultdict[int, float]):
    if not c:
        return []
    m = max(c.keys())
    return [round(c.get(k, 0), 5) for k in range(0, m + 1)]


@dataclass
class BreakDetails:
    """details shared between hybrid and ibuckets."""

    num_reps: int
    elapsed_s: float
    failures: list[str]
    elim_level: Counter[int]
    secs_by_level: defaultdict[int, float]

    def asdict(self):
        d = dataclasses.asdict(self)
        d["elapsed_s"] = round(self.elapsed_s, 5)
        d["elim_level"] = counter_to_array(self.elim_level)
        d["secs_by_level"] = float_dict_to_array(self.secs_by_level)
        return d


@dataclass
class HybridBreakDetails(BreakDetails):
    bounds: dict[int, int]
    """Maximum bound at each depth."""
    depth: Counter[int]
    """This is the switchover depth"""
    boards_to_test: int
    """Number of boards that made it through to the Boggler"""
    init_nodes: int
    """Number of nodes in the initial orderly tree"""
    total_nodes: int
    """Total nodes ever allocated (not necessarily all at once)"""
    tree_bytes: int
    """Number of bytes used by the initial orderly tree"""
    n_paths: int
    n_paths_uniq: int
    tree_secs: list[float]
    total_bytes: int
    """Max bytes ever used while breaking"""
    n_bound: int
    """Number of calls to orderly_bound"""
    n_force: int
    """Number of calls to orderly_force"""
    max_multi: int
    """Highest-observed bound (multiboggle score) from orderly_bound"""
    bound_secs: defaultdict[int, float]
    """Seconds spent in orderly_bound, by level"""
    test_secs: float
    """Seconds spent evaluating individual boards."""
    best_board: Optional[tuple[int, str]]
    """Highest-scoring board that was evaluated (if any did)"""

    def asdict(self):
        d = super().asdict()
        d["bounds"] = counter_to_array(self.bounds)[1:]
        d["depth"] = counter_to_array(self.depth)
        d["bound_secs"] = float_dict_to_array(self.bound_secs)
        d["test_secs"] = round(self.test_secs, 5)
        d["tree_secs"] = [round(v, 3) for v in d["tree_secs"]]
        return d


class HybridTreeBreaker:
    """This uses orderly_force_cell at the top of the tree and orderly_bound at the bottom.

    This strikes a good balance of allocating memory only when it will save a lot of CPU.
    """

    def __init__(
        self,
        etb: OrderlyTreeBuilder,
        boggler: PyBoggler,
        dims: tuple[int, int],
        best_score: int,
        *,
        switchover_score: int,
        log_breaker_progress: bool,
        max_depth=None,
    ):
        self.etb = etb
        self.boggler = boggler
        self.best_score = best_score
        self.details_ = None
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]
        self.switchover_score = switchover_score
        self.switchover_depth = max_depth or (dims[0] * dims[1] - 4)
        self.log_breaker_progress = log_breaker_progress
        self.bound_stats = Counter()

    def SetBoard(self, board: str):
        return self.etb.parse_board(board)

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
            tree_secs=[],
            init_nodes=0,
            depth=Counter(),
            total_nodes=0,
            tree_bytes=0,
            total_bytes=0,
            n_bound=0,
            n_force=0,
            n_paths=0,
            n_paths_uniq=0,
            max_multi=0,
            bound_secs=defaultdict(float),
            test_secs=0.0,
            best_board=None,
        )
        self.orig_reps_ = self.details_.num_reps = self.etb.num_reps()
        start_time_s = time.time()
        arena = self.etb.create_arena()
        tree = self.etb.build_tree(arena)
        ts = self.etb.get_stats()
        self.details_.tree_secs = [ts.collect_s, ts.sort_s, ts.build_s]
        self.details_.n_paths = ts.n_paths
        self.details_.n_paths_uniq = ts.n_uniq
        num_nodes = arena.num_nodes()
        if self.log_breaker_progress:
            print(f"root {tree.bound=}, {num_nodes} nodes")

        self.details_.secs_by_level[0] += time.time() - start_time_s
        self.details_.init_nodes = arena.num_nodes()
        self.details_.tree_bytes = arena.bytes_allocated()

        self.attack_tree(tree, 1, [], arena)

        self.details_.elapsed_s = time.time() - start_time_s
        self.details_.total_nodes = arena.num_nodes()
        self.details_.total_bytes = arena.bytes_allocated()
        # with open("/tmp/bound-stats.json", "w") as out:
        #     json.dump(
        #         {",".join(str(v) for v in k): v for k, v in self.bound_stats.items()},
        #         out,
        #     )
        return self.details_

    def attack_tree(
        self,
        tree: SumNode,
        level: int,
        choices: list[tuple[int, int]],
        arena: PyArena,
    ) -> None:
        self.details_.bounds[level] = max(
            self.details_.bounds.get(level, 0), tree.bound
        )
        if tree.bound < self.best_score:
            self.details_.elim_level[level] += 1
        elif tree.bound <= self.switchover_score or level > self.switchover_depth:
            self.switch_to_score(tree, level, choices, arena)
        else:
            self.force_and_filter(tree, level, choices, arena)

    def force_and_filter(
        self,
        tree: SumNode,
        level: int,
        choices: list[tuple[int, int]],
        arena: PyArena,
    ) -> None:
        # choices list parallels split_order
        assert len(choices) < len(self.cells)

        cell = self.split_order[len(choices)]
        num_lets = len(self.cells[cell])

        start_s = time.time()
        self.details_.n_force += 1
        arena_level = arena.save_level()
        trees = tree.orderly_force_cell(cell, num_lets, arena, max_depth=2)
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
            self.attack_tree(tree, level + 1, choices, arena)
        choices.pop()
        arena.reset_level(arena_level)

    def switch_to_score(
        self,
        tree: SumNode,
        level: int,
        choices: list[tuple[int, int]],
        arena: PyArena,
    ) -> None:
        start_s = time.time()
        remaining_cells = self.split_order[len(choices) :]
        # TODO: make this just return the boards
        self.details_.n_bound += 1
        self.details_.depth[level] += 1
        score_boards = tree.orderly_bound(
            self.best_score, self.cells, remaining_cells, choices, arena
        )
        # self.bound_stats[stats] += 1
        boards_to_test = [board for _score, board in score_boards]
        bound_elapsed_s = time.time() - start_s
        self.details_.bound_secs[level] += bound_elapsed_s

        if not boards_to_test:
            if self.log_breaker_progress:
                time_fmt = time.strftime("%Y-%m-%d %H:%M:%S")
                print(
                    f"{time_fmt} {self.details_.n_bound} {choices} -> {tree.bound=} {bound_elapsed_s:.03} s"
                )
            return

        max_multi = max(score for score, _board in score_boards)
        self.details_.max_multi = max(self.details_.max_multi, max_multi)
        self.details_.boards_to_test += len(boards_to_test)
        start_s = time.time()
        best_board = self.details_.best_board or (-1, "")
        for board in boards_to_test:
            true_score = self.boggler.score(board)
            # print(f"{board}: {tree.bound} -> {true_score}")
            if true_score >= self.best_score:
                print(f"Unable to break board: {board} {true_score}")
                self.details_.failures.append(board)
            if true_score > best_board[0]:
                best_board = (true_score, board)
        elapsed_s = time.time() - start_s
        self.details_.test_secs += elapsed_s
        self.details_.best_board = best_board

        if self.log_breaker_progress:
            time_fmt = time.strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{time_fmt} {self.details_.n_bound} {choices} -> {tree.bound=} {bound_elapsed_s:.03}s / test {len(boards_to_test)} in {elapsed_s:.03}s"
            )


# Invoked as a script, this merges multiple output NDJSON files into a single summary.
if __name__ == "__main__":
    out = None
    for file in sys.argv[1:]:
        for line_num, line in enumerate(open(file)):
            details = json.loads(line)
            if not out:
                out = details
                continue
            for k, v in details.items():
                if k not in out:
                    out[k] = v
                elif k == "id":
                    out[k] = max(v, out[k])
                elif isinstance(v, (float, int)):
                    out[k] += v
                elif k == "failures":
                    out[k] += v
                elif k == "best_board":
                    if out[k] is None or (v and v[0] > out[k][0]):
                        out[k] = v
                elif isinstance(v, list):
                    if len(out[k]) < len(v):
                        out[k] += [0] * (len(v) - len(out[k]))
                    for i, val in enumerate(v):
                        out[k][i] += val
                elif isinstance(v, dict):
                    for sk, val in v.items():
                        out[k][sk] = out[k].get(sk, 0) + val
                else:
                    raise ValueError(f"{file}:{line_num} {k}: {v}")
    print(json.dumps(out))
