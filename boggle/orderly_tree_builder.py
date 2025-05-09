"""Build an EvalTree in an "orderly" fashion.

This means that cells always appear in a set order, e.g. center outwards.
This typically produces much smaller trees with much tigher bounds than
the "natural" trees produced by a DFS over the board class.

See https://www.danvk.org/2025/02/21/orderly-boggle.html#orderly-trees
"""

import argparse
import time
from typing import Sequence

from boggle.arena import PyArena, create_eval_node_arena_py
from boggle.args import add_standard_args, get_trie_from_args
from boggle.board_class_boggler import BoardClassBoggler
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.dimensional_bogglers import (
    LEN_TO_DIMS,
    cpp_orderly_tree_builder,
)
from boggle.eval_node import ROOT_NODE, SumNode, countr_zero
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie


class OrderlyTreeBuilder(BoardClassBoggler):
    cell_to_order: dict[int, int]
    root: SumNode
    cell_counts: list[int]
    found_words: set[tuple[str, int, int]]
    num_letters_: list[int]

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}

    def BuildTree(self, arena: PyArena = None):
        root = SumNode()
        root.letter = ROOT_NODE
        root.points = 0
        root.bound = 0
        self.root = root
        self.used_ = 0
        self.used_ordered_ = 0
        self.cell_counts = [0] * len(self.bd_)
        self.found_words = set()
        self.num_letters = [len(cell) for cell in self.bd_]
        choices = [0] * len(self.bd_)
        if arena:
            arena.add_node(root)

        self.trie_.ResetMarks()
        for cell in range(len(self.bd_)):
            self.DoAllDescents(cell, 0, self.trie_, choices, arena)
        self.root = None
        self.trie_.ResetMarks()
        return root

    def SumUnion(self):
        # This _could_ be computed if there were a need.
        return 0

    def DoAllDescents(
        self, cell: int, length: int, t: PyTrie, choices: list[int], arena
    ):
        choices.append((cell, 0))
        for j, char in enumerate(self.bd_[cell]):
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                cell_order = self.cell_to_order[cell]
                choices[cell_order] = j
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
        choices: list[int],
        arena,
    ):
        self.used_ ^= 1 << cell
        self.used_ordered_ ^= 1 << self.cell_to_order[cell]

        for idx in self.neighbors[cell]:
            if not self.used_ & (1 << idx):
                self.DoAllDescents(idx, length, t, choices, arena)

        if t.IsWord():
            word_score = SCORES[length]
            mark_raw = t.Mark()
            is_dupe = False
            choice_mark = encode_choices(
                get_choices(choices, self.used_ordered_), self.num_letters
            )
            if choice_mark < (1 << 38):
                this_mark = self.used_ << 38 + choice_mark
                if mark_raw != 0:
                    # possible collision
                    m = mark_raw & (1 << 63 - 1)
                    if m == this_mark:
                        # definite collision
                        is_dupe = True
                    else:
                        # possible collision -- check the found_words set, too
                        this_key = (id(t), this_mark)
                        was_first = mark_raw & (1 << 63)
                        if was_first:
                            old_key = (id(t), m)
                            self.found_words.add(this_key)
                            self.found_words.add(old_key)
                            t.Mark(m)  # clear "was_first" bit
                        else:
                            is_dupe = this_key in self.found_words
                            if not is_dupe:
                                self.found_words.add(this_key)

                else:
                    t.Mark(this_mark + (1 << 63))

            if not is_dupe:
                self.root.add_word(
                    choices,
                    self.used_ordered_,
                    SPLIT_ORDER[self.dims],
                    word_score,
                    arena,
                    self.cell_counts,
                )

        self.used_ordered_ ^= 1 << self.cell_to_order[cell]
        self.used_ ^= 1 << cell

    def create_arena(self):
        return create_eval_node_arena_py()


def get_choices(
    choices: Sequence[int], used_ordered: int, split_order: Sequence[int]
) -> list[tuple[int, int]]:
    """Returns the choices in split order"""
    letters = list[tuple[int, int]]()
    while used_ordered:
        order_index = countr_zero(used_ordered)
        cell = split_order[order_index]
        letter = choices[order_index]

        # remove the cell from used_ordered
        used_ordered &= used_ordered - 1
        letters.append((cell, letter))
    return letters


def encode_choices(
    choices: Sequence[tuple[int, int]], num_letters: Sequence[int]
) -> int:
    idx = 0
    for cell, letter in choices:
        idx *= num_letters[cell]
        idx += letter
    return idx


mark = 1


def tree_stats(t: SumNode) -> str:
    global mark
    mark += 1
    return f"{t.bound=}, {t.node_count()} nodes"


def main():
    parser = argparse.ArgumentParser(description="Get the orderly bound for a board")
    add_standard_args(parser, python=True)
    parser.add_argument("board", type=str, help="Board class to bound.")
    args = parser.parse_args()
    board = args.board
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


if __name__ == "__main__":
    main()
