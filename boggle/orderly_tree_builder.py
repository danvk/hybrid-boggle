"""Build an EvalTree in an "orderly" fashion.

This means that cells always appear in a set order, e.g. center outwards.
This typically produces much smaller trees with much tigher bounds than
the "natural" trees produced by a DFS over the board class.

See https://www.danvk.org/2025/02/21/orderly-boggle.html#orderly-trees
"""

import argparse
import itertools
import random
import time
from dataclasses import dataclass
from typing import Sequence

from boggle.arena import PyArena, create_eval_node_arena_py
from boggle.args import add_standard_args, get_trie_from_args
from boggle.board_class_boggler import BoardClassBoggler
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.dimensional_bogglers import (
    LEN_TO_DIMS,
    cpp_orderly_tree_builder,
)
from boggle.eval_node import ChoiceNode, SumNode, countr_zero
from boggle.make_dot import to_dot
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie, make_id_lookup_table, make_lookup_table


@dataclass(order=True)
class WordPath:
    path: list[tuple[int, int]]
    word_id: int
    points: int
    cell_mask: int
    has_force: bool


@dataclass
class TreeBuilderStats:
    collect_s: float
    sortw_s: float
    dedupe_s: float
    sort_s: float
    resort_s: float
    build_s: float
    n_paths: int
    n_paths_uniq: int
    n_uniq: int


class OrderlyTreeBuilder(BoardClassBoggler):
    cell_to_order: dict[int, int]
    root: SumNode
    num_letters_: list[int]
    words_: list[WordPath]
    stats_: TreeBuilderStats

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}
        self.split_order = SPLIT_ORDER[dims]
        self.lookup = make_lookup_table(trie)
        self.raw_multiboggle = False
        self.words_ = []
        self.stats_ = None
        self.dedupe_forced = False

    def build_tree(self, arena: PyArena = None):
        stats = TreeBuilderStats(
            collect_s=0,
            sortw_s=0,
            dedupe_s=0,
            sort_s=0,
            resort_s=0,
            build_s=0,
            n_paths=0,
            n_paths_uniq=0,
            n_uniq=0,
        )
        self.used_ = 0
        self.used_ordered_ = 0
        self.num_letters = [len(cell) for cell in self.bd_]
        self.is_forced_ = [self.dedupe_forced and len(cell) == 1 for cell in self.bd_]
        choices = [0] * len(self.bd_)

        start = time.time()
        for cell in range(len(self.bd_)):
            self.do_all_descents(cell, 0, self.trie_, choices, arena)
        end = time.time()
        stats.collect_s = end - start
        stats.n_paths = len(self.words_)
        if not self.words_:
            return SumNode()

        print(f"Big list: {stats.n_paths}")

        start = end
        self.words_.sort(key=lambda wp: (wp.word_id, len(wp.path), wp.path))
        end = time.time()
        stats.sortw_s = end - start
        # print_word_list(self.trie_, self.words_)
        if self.raw_multiboggle:
            unique_words = self.words_
        elif self.dedupe_forced:
            start = end
            unique_words = dedupe_word_list(self.words_)
            end = time.time()
            stats.dedupe_s = end - start
            stats.n_paths_uniq = len(unique_words)
        else:
            unique_words = self.words_

        # print(f" #uniq: {stats.n_uniq}")
        if not self.raw_multiboggle:
            # TODO: does tree building even work without uniquing?
            start = end
            unique_words.sort()
            end = time.time()
            stats.sort_s = end - start
            unique_words = unique_word_list(unique_words)
            stats.n_uniq = len(unique_words)
        # print_word_list(self.trie_, unique_words)

        start = end
        root = range_to_sum_node(unique_words, 0, arena)
        end = time.time()
        stats.build_s = end - start

        self.words_ = unique_words
        start = end
        self.words_.sort(key=lambda wp: wp.word_id)
        end = time.time()
        stats.resort_s = end - start

        self.stats_ = stats
        return root

    def do_all_descents(
        self, cell: int, length: int, t: PyTrie, choices: list[int], arena
    ):
        choices.append((cell, 0))
        for j, char in enumerate(self.bd_[cell]):
            cc = ord(char) - LETTER_A
            if t.starts_word(cc):
                cell_order = self.cell_to_order[cell]
                choices[cell_order] = j
                self.do_dfs(
                    cell,
                    length + (2 if cc == LETTER_Q else 1),
                    t.descend(cc),
                    choices,
                    arena,
                )
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
            path = decode(
                self.used_ordered_, choices, SPLIT_ORDER[self.dims], self.is_forced_
            )
            cell_mask = sum(1 << cell for cell, _ in path)
            self.words_.append(
                WordPath(
                    path=path,
                    word_id=t.word_id,
                    points=SCORES[length],
                    cell_mask=cell_mask,
                    has_force=len(path) < length,
                )
            )

        self.used_ordered_ ^= 1 << self.cell_to_order[cell]
        self.used_ ^= 1 << cell

    def create_arena(self):
        return create_eval_node_arena_py()

    def get_stats(self):
        return self.stats_


def decode(
    used_ordered: int,
    choices: Sequence[int],
    split_order: Sequence[int],
    is_forced: Sequence[bool],
):
    out = []
    while used_ordered:
        order_index = countr_zero(used_ordered)
        cell = split_order[order_index]
        letter = choices[order_index]

        # remove the cell from used_ordered
        used_ordered &= used_ordered - 1
        if not is_forced[cell]:
            out.append((cell, letter))
    return out


def unique_word_list(xs: Sequence[WordPath]):
    out: list[WordPath] = []
    last_path = None
    last_word_id = None
    for x in xs:
        if x.path != last_path:
            out.append(x)
            last_path = x.path
            last_word_id = x.word_id
        elif x.word_id != last_word_id:
            out[-1].points += x.points
            last_word_id = x.word_id
    return out


def is_subset(sub: WordPath, super: WordPath) -> bool:
    if super.cell_mask & sub.cell_mask != sub.cell_mask:
        return False

    s = sub.path
    p = super.path
    i = 0
    j = 0
    while i < len(s):
        if j >= len(p):
            return False
        if s[i][0] == p[j][0]:
            if s[i][1] == p[j][1]:
                i += 1
                j += 1
            else:
                return False
        else:
            j += 1
    return True


def dedupe_word_list(xs: Sequence[WordPath]):
    """For each distinct word, filter out redundant paths.

    A path is redundant if some subset of it can be used to find the same word.
    This can happen if one letter has already been forced, in which case it's
    "free" -- we don't need to choose it. Hence you could wind up with both
    {2=E, 3=E} and {1=F, 2=E, 3=E} as paths to "FEE" if 0=F has already been forced.
    In this case the longer path is redundant and can be removed for a lower bound.
    """
    out: list[WordPath] = []
    for _, raw_wps in itertools.groupby(xs, key=lambda wp: wp.word_id):
        raw_wps = list(raw_wps)
        out += dedupe_paths_for_word(raw_wps)

    return out


n_forced = 0
n_unforced = 0
has_printed = False
global_trie = None


def dedupe_paths_for_word(raw_wps: Sequence[WordPath]):
    # has_mismatch = forced_paths and min(len(wp.path) for wp in forced_paths) != max(
    #     len(wp.path) for wp in forced_paths
    # )

    # if has_mismatch or (has_printed < 10 and random.random() < 0.1):
    #     has_printed += 1
    #     word_id = raw_wps[0].word_id
    #     lookup = make_id_lookup_table(global_trie)
    #     print(f"{word_id} = {lookup[word_id]}")
    #     print(f"forced ({len(forced_paths)}):")
    #     print_word_list(global_trie, forced_paths)
    #     print(f"\nunforced ({len(unforced_paths)}):")
    #     print_word_list(global_trie, unforced_paths)

    # identical paths should be next to each other thanks to the sorting and can be collapsed.
    out = [raw_wps[0]]
    for wp in raw_wps[1:]:
        if out[-1].path == wp.path:
            continue
        out.append(wp)

    # check for subsets, but only in shorter paths
    start_len = 0
    this_len = 0
    is_valid = [True] * len(out)
    for i, wp in enumerate(out):
        if i == 0 or len(wp.path) > this_len:
            start_len = i
            this_len = len(wp.path)
            continue
        for shorter_wp in out[:start_len]:
            if is_subset(shorter_wp, wp):
                is_valid[i] = False

    valids = [wp for ok, wp in zip(is_valid, out) if ok]
    return valids


mark = 1


def tree_stats(t: SumNode) -> str:
    global mark
    mark += 1
    return f"{t.bound=}, {t.node_count()} nodes"


def range_to_sum_node(words: Sequence[WordPath], depth: int, arena: PyArena) -> SumNode:
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
        if depth >= len(word.path):
            print(depth, word.path)
        cell = word.path[depth][0]
        if cell != last_cell:
            child_cells.append(cell)
            child_range_starts.append(i)
            child_range_ends.append(i)
            last_cell = cell
        else:
            child_range_ends[-1] = i

    children = [
        range_to_choice_node(cell, words[start : end + 1], depth, arena)
        for cell, start, end in zip(child_cells, child_range_starts, child_range_ends)
    ]
    node = SumNode()
    node.points = points
    node.children = {cell: child for cell, child in zip(child_cells, children)}
    node.bound = node.points + sum(child.bound for child in node.children.values())
    return node


def range_to_choice_node(
    cell: int, words: Sequence[WordPath], depth: int, arena: PyArena
) -> SumNode:
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
        range_to_sum_node(words[start : end + 1], depth + 1, arena)
        for start, end in zip(child_range_starts, child_range_ends)
    ]

    letter_mask = 0
    for letter in child_letters:
        letter_mask |= 1 << letter

    node = ChoiceNode()
    node.child_letters = letter_mask
    node.children = children
    node.bound = max(child.bound for child in node.children) if children else 0
    return node


def print_word_list(trie: PyTrie, words: Sequence[WordPath]):
    word_id_to_word = make_id_lookup_table(trie)
    for i, word in enumerate(words):
        w = word_id_to_word[word.word_id]
        print(f"{i:3d} {word.path} ({word.points}) {w}")

    # by_word = dict[str, list[WordPath]]()
    # for w in words:
    #     word = word_id_to_word[w.word_id]
    #     by_word.setdefault(word, [])
    #     by_word[word].append(w)
    # for i, (word, wps) in enumerate(by_word.items()):
    #     print(f"{i:3d} {word}")
    #     for wp in wps:
    #         print(f"    {wp.path} ({wp.points})")


def main():
    parser = argparse.ArgumentParser(description="Get the orderly bound for a board")
    add_standard_args(parser, python=True)
    parser.add_argument("board", type=str, help="Board class to bound.")
    parser.add_argument(
        "--raw_multiboggle",
        action="store_true",
        help="Do not dedupe words on SumNodes. (Requires --python)",
    )
    parser.add_argument(
        "--dedupe_forced",
        action="store_true",
        help="Deduplicate redundant words from forced cells in the board.",
    )
    args = parser.parse_args()
    if args.raw_multiboggle:
        assert args.python, "--raw_multiboggle require --python"
    board = args.board
    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    trie = get_trie_from_args(args)
    global global_trie
    global_trie = trie

    # etb = TreeBuilder(trie, dims)
    # assert etb.parse_board(board)
    # e_arena = etb.create_arena()
    # classic_tree = etb.build_tree(e_arena, dedupe=True)

    builder = OrderlyTreeBuilder if args.python else cpp_orderly_tree_builder
    otb = builder(trie, dims)
    if args.raw_multiboggle:
        otb.raw_multiboggle = args.raw_multiboggle
    otb.dedupe_forced = args.dedupe_forced
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
    # print_word_list(trie, otb.words_)
    print(f"arena nodes: {o_arena.num_nodes()}")
    print(f"arena bytes: {o_arena.bytes_allocated()}")
    stats = otb.get_stats()
    print(f"  collect: {stats.collect_s:.04} s")
    print(f"  sort_w: {stats.sortw_s:.04} s")
    print(f"  dedupe: {stats.dedupe_s:.04} s")
    print(f"  sort: {stats.sort_s:.04} s")
    print(f"  build: {stats.build_s:.04} s")
    print(f"  n_paths: {stats.n_paths}")
    print(f"  n_paths_uniq: {stats.n_paths_uniq}")
    print(f"  n_uniq: {stats.n_uniq}")

    print(f"  {n_forced=}")
    print(f"  {n_unforced=}")

    # if isinstance(orderly_tree, SumNode):
    #     with open("tree.dot", "w") as out:
    #         out.write(to_dot(orderly_tree, cells=cells))
    # with open("tree.txt", "w") as out:
    #     out.write(eval_node_to_string(orderly_tree, cells))


if __name__ == "__main__":
    main()
