"""Build an EvalTree in an "orderly" fashion.

This means that cells always appear in a set order, e.g. center outwards.
This typically produces much smaller trees with much tigher bounds than
the "natural" trees produced by a DFS over the board class.

See https://www.danvk.org/2025/02/21/orderly-boggle.html#orderly-trees
"""

import argparse
import json
import time

from boggle.arena import PyArena, create_eval_node_arena_py
from boggle.args import add_standard_args, get_trie_from_args
from boggle.board_class_boggler import BoardClassBoggler
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.dimensional_bogglers import (
    LEN_TO_DIMS,
    cpp_orderly_tree_builder,
)
from boggle.eval_node import SumNode
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie, make_lookup_table


class OrderlyTreeBuilder(BoardClassBoggler):
    cell_to_order: dict[int, int]
    root: SumNode
    num_letters_: list[int]

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}
        self.split_order = SPLIT_ORDER[dims]
        self.lookup = make_lookup_table(trie)
        self.letter_counts = [0] * 26
        self.dupe_mask = 0
        self.raw_multiboggle = False

    def build_tree(self, arena: PyArena = None):
        root = SumNode()
        root.points = 0
        root.bound = 0
        self.root = root
        self.used_ = 0
        self.used_ordered_ = 0
        self.num_letters = [len(cell) for cell in self.bd_]
        self.letter_counts = [0] * 26
        # This tracks whether any of the 26 letters has been used more than once.
        # If so, we need to check for duplicate paths to the same word. This check
        # has minimal effect on performance, but it does save memory.
        self.dupe_mask = 0
        choices = [0] * len(self.bd_)
        if arena:
            arena.add_node(root)

        for cell in range(len(self.bd_)):
            self.do_all_descents(cell, 0, self.trie_, choices, arena)
        self.root = None
        assert self.letter_counts == [0] * 26
        root.decode_points_and_bound()
        return root

    def do_all_descents(
        self, cell: int, length: int, t: PyTrie, choices: list[int], arena
    ):
        choices.append((cell, 0))
        old_mask = self.dupe_mask
        for j, char in enumerate(self.bd_[cell]):
            cc = ord(char) - LETTER_A
            if t.starts_word(cc):
                cell_order = self.cell_to_order[cell]
                choices[cell_order] = j
                old_count = self.letter_counts[cc]
                self.letter_counts[cc] += 1
                if old_count == 1:
                    self.dupe_mask |= 1 << cc
                self.do_dfs(
                    cell,
                    length + (2 if cc == LETTER_Q else 1),
                    t.descend(cc),
                    choices,
                    arena,
                )
                self.letter_counts[cc] -= 1
                self.dupe_mask = old_mask
        choices.pop()

    def do_dfs(
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
                self.do_all_descents(idx, length, t, choices, arena)

        if t.is_word():
            word_score = SCORES[length]
            word_node = self.root.add_word(
                choices,
                self.used_ordered_,
                SPLIT_ORDER[self.dims],
                arena,
            )
            if self.raw_multiboggle:
                word_node.points += word_score
            elif self.dupe_mask > 0:
                # The C++ version uses a binary encoding, but we just stuff everything in a set.
                if word_node.bound:
                    word_node.bound.add(t.word_id)
                    assert word_node.points == word_score
                else:
                    word_node.bound = {t.word_id}
                    word_node.points = word_score
            else:
                word_node.points += word_score
                assert word_node.bound == 0

        self.used_ordered_ ^= 1 << self.cell_to_order[cell]
        self.used_ ^= 1 << cell

    def create_arena(self):
        return create_eval_node_arena_py()


mark = 1


def tree_stats(t: SumNode) -> str:
    global mark
    mark += 1
    return f"{t.bound=}, {t.node_count()} nodes"


def range_to_sum_node(words: Sequence[WordPath], depth: int) -> SumNode:
    # If there are points on _this_ node, they'll be on a unique first node.
    n = words[0]
    points = 0
    if len(n.path) == depth:
        points = n.points
        words = words[1:]

    # Find intervals for each distinct cell
    child_cells = []
    child_range_starts = []
    child_range_ends = []
    last_cell = None
    for i, word in enumerate(words):
        cell = word.path[depth][0]
        if cell != last_cell:
            child_cells.append(cell)
            child_range_starts.append(i)
            child_range_ends.append(i)
            last_cell = cell
        else:
            child_range_ends[-1] = i

    children = [
        range_to_choice_node(cell, words[start : end + 1], depth)
        for cell, start, end in zip(child_cells, child_range_starts, child_range_ends)
    ]
    node = SumNode()
    node.points = points
    node.children = children
    node.bound = node.points + sum(child.bound for child in node.children)
    return node


def range_to_choice_node(cell: int, words: Sequence[WordPath], depth: int) -> SumNode:
    # Find intervals for each distinct letter
    child_letters = []
    child_range_starts = []
    child_range_ends = []
    last_letter = None
    for i, word in enumerate(words):
        letter = word.path[depth][1]
        if letter != last_letter:
            child_letters.append(letter)
            child_range_starts.append(i)
            child_range_ends.append(i)
            last_letter = letter
        else:
            child_range_ends[-1] = i

    children = [
        range_to_sum_node(words[start : end + 1], depth + 1)
        for start, end in zip(child_range_starts, child_range_ends)
    ]

    letter_mask = 0
    for letter in child_letters:
        letter_mask |= 1 << letter

    node = ChoiceNode()
    node.cell = cell
    node.child_letters = letter_mask
    node.children = children
    node.bound = max(child.bound for child in node.children)
    return node


def main():
    parser = argparse.ArgumentParser(description="Get the orderly bound for a board")
    add_standard_args(parser, python=True)
    parser.add_argument("board", type=str, help="Board class to bound.")
    parser.add_argument(
        "--raw_multiboggle",
        action="store_true",
        help="Do not dedupe words on SumNodes. (Requires --python)",
    )
    args = parser.parse_args()
    if args.raw_multiboggle:
        assert args.python, "--raw_multiboggle require --python"
    board = args.board
    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    trie = get_trie_from_args(args)
    # etb = TreeBuilder(trie, dims)
    # assert etb.parse_board(board)
    # e_arena = etb.create_arena()
    # classic_tree = etb.build_tree(e_arena, dedupe=True)

    builder = OrderlyTreeBuilder if args.python else cpp_orderly_tree_builder
    otb = builder(trie, dims)
    if args.raw_multiboggle:
        otb.raw_multiboggle = True
    o_arena = otb.create_arena()
    assert otb.parse_board(board)
    arenas = []
    arenas.append(o_arena)
    start_s = time.time()
    orderly_tree = otb.build_tree(o_arena)
    elapsed_s = time.time() - start_s

    # print("EvalTreeBuilder:    ", end="")
    # print(tree_stats(classic_tree))

    print(f"{elapsed_s:.02f}s OrderlyTreeBuilder: ", end="")
    print(tree_stats(orderly_tree))
    print(f"{orderly_tree.word_count()=}")
    # print(json.dumps(orderly_tree.to_json(), indent=True))


if __name__ == "__main__":
    main()
