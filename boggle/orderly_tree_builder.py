import argparse

from boggle.args import add_standard_args, get_trie_from_args
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.eval_tree import (
    ROOT_NODE,
    EvalNode,
    EvalTreeBoggler,
    create_eval_node_arena_py,
)
from boggle.ibuckets import PyBucketBoggler
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie


# TODO: decide if this really needs to inherit PyBucketBoggler
class OrderlyTreeBuilder(PyBucketBoggler):
    cell_to_order: dict[int, int]
    root: EvalNode

    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)
        self.cell_to_order = {cell: i for i, cell in enumerate(SPLIT_ORDER[dims])}

    def UpperBound(self, bailout_score):
        raise NotImplementedError()

    def BuildTree(self, arena=None):
        root = EvalNode()
        root.letter = ROOT_NODE
        root.cell = 0  # irrelevant
        root.points = 0
        self.root = root
        self.used_ = 0

        for cell in range(len(self.bd_)):
            self.DoAllDescents(cell, 0, self.trie_, [])
        root.set_computed_fields_for_testing(self.bd_)
        self.root = None
        return root

    # TODO: rename these methods
    def DoAllDescents(
        self, cell: int, length: int, t: PyTrie, choices: list[tuple[int, int]]
    ):
        choices.append((cell, 0))
        for j, char in enumerate(self.bd_[cell]):
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                choices[-1] = (cell, j)
                self.DoDFS(
                    cell, length + (2 if cc == LETTER_Q else 1), t.Descend(cc), choices
                )
        choices.pop()

    def DoDFS(
        self,
        cell: int,
        length: int,
        t: PyTrie,
        choices: list[tuple[int, int]],
    ):
        self.used_ ^= 1 << cell

        for idx in self.neighbors[cell]:
            if not self.used_ & (1 << idx):
                self.DoAllDescents(idx, length, t, choices)

        if t.IsWord():
            word_score = SCORES[length]
            # TODO: sort by split order
            orderly_choices = [*sorted(choices, key=lambda c: self.cell_to_order[c[0]])]
            self.root.add_word(orderly_choices, word_score)

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
    parser.add_argument("board", type=str, help="Board class to lift.")
    args = parser.parse_args()
    board = args.board
    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    trie = get_trie_from_args(args)
    etb = EvalTreeBoggler(trie, dims)
    assert etb.ParseBoard(board)
    e_arena = etb.create_arena()
    classic_tree = etb.BuildTree(e_arena, dedupe=True)

    otb = OrderlyTreeBuilder(trie, dims)
    o_arena = otb.create_arena()
    assert otb.ParseBoard(board)
    orderly_tree = otb.BuildTree(o_arena)

    print(orderly_tree.to_dot(cells))

    print("EvalTreeBuilder:")
    print(tree_stats(classic_tree))

    print("OrderlyTreeBuilder:")
    print(tree_stats(orderly_tree))


if __name__ == "__main__":
    main()
