import argparse
import sys
import time

from boggle.args import add_standard_args, get_trie_from_args
from boggle.board_class_boggler import BoardClassBoggler
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.dimensional_bogglers import (
    LEN_TO_DIMS,
    OrderlyTreeBuilders,
    cpp_orderly_tree_builder,
)
from boggle.eval_tree import (
    ROOT_NODE,
    EvalNode,
    PyArena,
    create_eval_node_arena_py,
    eval_all,
)
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie


class OrderlyTreeBuilder(BoardClassBoggler):
    cell_to_order: dict[int, int]
    root: EvalNode
    cell_counts: list[int]

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}

    def BuildTree(self, arena: PyArena = None):
        root = EvalNode()
        root.letter = ROOT_NODE
        root.cell = 0  # irrelevant
        root.points = 0
        root.bound = 0
        self.root = root
        self.used_ = 0
        self.cell_counts = [0] * len(self.bd_)
        if arena:
            arena.add_node(root)

        for cell in range(len(self.bd_)):
            self.DoAllDescents(cell, 0, self.trie_, [], arena)
        self.root = None
        return root

    def SumUnion(self):
        # This _could_ be computed if there were a need.
        return 0

    # TODO: rename these methods
    def DoAllDescents(
        self, cell: int, length: int, t: PyTrie, choices: list[tuple[int, int]], arena
    ):
        choices.append((cell, 0))
        for j, char in enumerate(self.bd_[cell]):
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                choices[-1] = (cell, j)
                self.DoDFS(
                    cell,
                    length + (2 if cc == LETTER_Q else 1),
                    t.Descend(cc),
                    choices,
                    arena,
                )
        choices.pop()

    def DoDFS(
        self,
        cell: int,
        length: int,
        t: PyTrie,
        choices: list[tuple[int, int]],
        arena,
    ):
        self.used_ ^= 1 << cell

        for idx in self.neighbors[cell]:
            if not self.used_ & (1 << idx):
                self.DoAllDescents(idx, length, t, choices, arena)

        if t.IsWord():
            word_score = SCORES[length]
            orderly_choices = [*sorted(choices, key=lambda c: self.cell_to_order[c[0]])]
            self.root.add_word(orderly_choices, word_score, arena, self.cell_counts)

        self.used_ ^= 1 << cell

    def create_arena(self):
        return create_eval_node_arena_py()

    def create_vector_arena(self):
        return create_eval_node_arena_py()


mark = 1


def tree_stats(t: EvalNode) -> str:
    global mark
    mark += 1
    return f"{t.bound=}, {t.node_count()} nodes"


def main():
    parser = argparse.ArgumentParser(description="Lift all the way to breaking")
    add_standard_args(parser, python=True)
    parser.add_argument("cutoff", type=int, help="Best known score for filtering.")
    parser.add_argument("board", type=str, help="Board class to lift.")
    parser.add_argument(
        "lift_cells", type=str, nargs="?", help="Sequence of choices to make"
    )
    args = parser.parse_args()
    board = args.board
    lift_cells = eval(args.lift_cells) if args.lift_cells else None
    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    trie = get_trie_from_args(args)
    # etb = TreeBuilder(trie, dims)
    # assert etb.ParseBoard(board)
    # e_arena = etb.create_arena()
    # classic_tree = etb.BuildTree(e_arena, dedupe=True)

    builder = OrderlyTreeBuilder if args.python else cpp_orderly_tree_builder
    otb = builder(trie, dims)
    o_arena = otb.create_arena()
    assert otb.ParseBoard(board)
    arenas = []
    arenas.append(o_arena)
    start_s = time.time()
    orderly_tree = otb.BuildTree(o_arena)
    elapsed_s = time.time() - start_s

    # print("EvalTreeBuilder:    ", end="")
    # print(tree_stats(classic_tree))

    print(f"{elapsed_s:.02f}s OrderlyTreeBuilder: ", end="")
    print(tree_stats(orderly_tree))

    t = orderly_tree
    for cell, letter in lift_cells:
        arena = otb.create_arena()
        arenas.append(arena)
        start_s = time.time()
        choices = t.orderly_force_cell(cell, len(cells[cell]), arena)
        elapsed_s = time.time() - start_s
        t = choices[letter]
        cells[cell] = cells[cell][letter]
        bd = " ".join(cells)
        print(f"{cell}/{letter} {elapsed_s:.02f}s f -> {tree_stats(t)} {bd}")

    # scores = eval_all(t, cells)
    # print(scores)

    # print("")
    # t.print_json()


if __name__ == "__main__":
    main()
