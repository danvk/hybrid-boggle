import argparse
import time

from boggle.args import add_standard_args, get_trie_from_args
from boggle.board_class_boggler import BoardClassBoggler
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS, OrderlyTreeBuilders
from boggle.eval_tree import (
    ROOT_NODE,
    EvalNode,
    create_eval_node_arena_py,
    dedupe_subtrees,
)
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie


class OrderlyTreeBuilder(BoardClassBoggler):
    cell_to_order: dict[int, int]
    root: EvalNode

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}

    def BuildTree(self, arena=None, dedupe=False):
        root = EvalNode()
        root.letter = ROOT_NODE
        root.cell = 0  # irrelevant
        root.points = 0
        self.root = root
        self.used_ = 0

        for cell in range(len(self.bd_)):
            self.DoAllDescents(cell, 0, self.trie_, [], arena)
        num_letters = [len(cell) for cell in self.bd_]
        node_cache = {} if dedupe else None
        root.set_computed_fields_and_dedupe(num_letters, node_cache)
        node_cache = None
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
            self.root.add_word(orderly_choices, word_score, arena)

        self.used_ ^= 1 << cell

    def create_arena(self):
        return create_eval_node_arena_py()


mark = 1


def tree_stats(t: EvalNode) -> str:
    global mark
    mark += 1
    return f"{t.bound=}, {t.node_count()} nodes, {t.unique_node_count(mark)} unique"


def main():
    parser = argparse.ArgumentParser(description="Lift all the way to breaking")
    add_standard_args(parser, python=True)
    parser.add_argument("cutoff", type=int, help="Best known score for filtering.")
    parser.add_argument("board", type=str, help="Board class to lift.")
    parser.add_argument("--num_lifts", type=int, default=0)
    parser.add_argument(
        "--dedupe", action="store_true", help="De-dupe nodes after building"
    )
    args = parser.parse_args()
    board = args.board
    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    trie = get_trie_from_args(args)
    # etb = TreeBuilder(trie, dims)
    # assert etb.ParseBoard(board)
    # e_arena = etb.create_arena()
    # classic_tree = etb.BuildTree(e_arena, dedupe=True)

    # otb = OrderlyTreeBuilder(trie, dims)
    if args.python:
        otb = OrderlyTreeBuilder(trie, dims)
    else:
        otb = OrderlyTreeBuilders[dims](trie)
    o_arena = otb.create_arena()
    assert otb.ParseBoard(board)
    start_s = time.time()
    orderly_tree = otb.BuildTree(o_arena, args.dedupe)
    elapsed_s = time.time() - start_s
    print(f"{elapsed_s:.02f}s BuildTree: ", end="")
    print(tree_stats(orderly_tree))

    global mark
    # mark += 1
    # start_s = time.time()
    # dedupe_subtrees(orderly_tree, mark)
    # elapsed_s = time.time() - start_s
    # print(elapsed_s)
    # print(f"{elapsed_s:.02f}s dedupe:    ", end="")
    # print(tree_stats(orderly_tree))

    t = orderly_tree
    splits = SPLIT_ORDER[dims]
    for i, cell in enumerate(splits[: args.num_lifts]):
        print(f"lift {cell}")
        mark += 1
        start_s = time.time()
        t = t.lift_choice(
            cell, len(cells[cell]), o_arena, mark, dedupe=True, compress=True
        )
        elapsed_s = time.time() - start_s
        if t.bound <= args.cutoff:
            print(
                f"{elapsed_s:.02f} Fully broken! {t.bound} <= {args.cutoff} {tree_stats(t)}"
            )
            break
        t.filter_below_threshold(args.cutoff)
        print(f"{elapsed_s:.02f}s #{i} f -> {tree_stats(t)}")


if __name__ == "__main__":
    main()
