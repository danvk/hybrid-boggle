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
from boggle.trie import PyTrie, make_lookup_table


class OrderlyTreeBuilder(BoardClassBoggler):
    cell_to_order: dict[int, int]
    root: SumNode
    cell_counts: list[int]
    found_words: set[tuple[str, int, int]]
    num_letters_: list[int]

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}
        self.split_order = SPLIT_ORDER[dims]
        self.lookup = make_lookup_table(trie)
        self.shift = 64 - 1 - dims[0] * dims[1]
        self.letter_counts = [0] * 26
        self.dupe_mask = 0

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
        self.num_overflow = 0
        self.letter_counts = [0] * 26
        self.dupe_mask = 0
        print(f"{self.num_letters=}")
        choices = [0] * len(self.bd_)
        if arena:
            arena.add_node(root)

        self.trie_.ResetMarks()
        for cell in range(len(self.bd_)):
            self.DoAllDescents(cell, 0, self.trie_, choices, arena)
            print(f"{len(self.found_words)=}")
        self.root = None
        self.trie_.ResetMarks()
        print(f"{len(self.found_words)=}, {self.num_overflow=}")
        assert self.letter_counts == [0] * 26
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
                old_count = self.letter_counts[cc]
                old_mask = self.dupe_mask  # TODO: can move out of loop
                self.letter_counts[cc] += 1
                if old_count == 1:
                    self.dupe_mask |= 1 << cc
                self.DoDFS(
                    cell,
                    length + (2 if cc == LETTER_Q else 1),
                    t.Descend(cc),
                    choices,
                    arena,
                )
                self.letter_counts[cc] -= 1
                self.dupe_mask = old_mask
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
            is_dupe = any(
                count > 1 for count in self.letter_counts
            ) and self.check_for_dupe(t, choices)

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

    def check_for_dupe(
        self,
        t: PyTrie,
        choices: list[int],
    ) -> bool:
        mark_raw = t.Mark()
        choice_mark = get_choice_mark(
            choices,
            self.used_ordered_,
            self.split_order,
            self.num_letters,
            1 << self.shift,
        )
        # word_order = "".join(self.bd_[cell][choice] for cell, choice in letters)
        # word = self.lookup[t]
        if not choice_mark:
            self.num_overflow += 1
            return False

        this_mark = (self.used_ordered_ << self.shift) + choice_mark
        if mark_raw == 0:
            m = this_mark + (1 << 63)
            # print(f"{word} set mark: {m} {word_order}")
            t.SetMark(m)
            return False

        # print(word, this_mark, word_order, letters, choice_mark)
        # possible collision
        m = mark_raw & ((1 << 63) - 1)
        # print(f"{mark_raw=} {m=}")
        # print(f"{word} Possible collision {this_mark} =? {m}")
        if m == this_mark:
            # definite collision
            # print(f"{word} Definite collision {word_order}")
            return True

        # possible collision -- check the found_words set, too
        this_key = (id(t), this_mark)
        was_first = mark_raw & (1 << 63)
        if was_first:
            old_key = (id(t), m)
            self.found_words.add(this_key)
            self.found_words.add(old_key)
            t.SetMark(m)  # clear "was_first" bit
            return False

        is_dupe = this_key in self.found_words
        if not is_dupe:
            self.found_words.add(this_key)
            if len(self.found_words) % 1_000_000 == 0:
                print(f"{len(self.found_words)=} {this_key}")
        return is_dupe

    def create_arena(self):
        return create_eval_node_arena_py()


def get_choice_mark(
    choices: Sequence[int],
    used_ordered: int,
    split_order: Sequence[int],
    num_letters: Sequence[int],
    max_value: int,
) -> int:
    idx = 0
    while used_ordered:
        order_index = countr_zero(used_ordered)
        cell = split_order[order_index]
        letter = choices[order_index]

        # remove the cell from used_ordered
        used_ordered &= used_ordered - 1
        idx *= num_letters[cell]
        idx += letter
    if idx > max_value:
        return 0
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
