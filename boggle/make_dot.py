#!/usr/bin/env python


import argparse
import sys

from boggle.args import add_standard_args, get_trie_from_args
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.tree_builder import TreeBuilder
from boggle.trie import make_py_trie


def main():
    parser = argparse.ArgumentParser(
        prog="DOT renderer",
        description="Visualize what's going on with those trees.",
    )
    # TODO: don't set size, we just need the dictionary
    add_standard_args(parser)
    parser.add_argument(
        "--tree_builder",
        choices=("natural", "orderly"),
        default="orderly",
        help="Tree builder to use.",
    )
    parser.add_argument(
        "--compress", action="store_true", help="Compress EvalTree while lifting"
    )
    parser.add_argument("board", type=str, help="Board class to render.")
    parser.add_argument("lift_cells", nargs="*", help="Sequence of cells to lift")
    args = parser.parse_args()
    trie = make_py_trie(args.dictionary)
    board = args.board
    lift_cells = [int(s) for s in args.lift_cells]

    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    if args.tree_builder == "natural":
        etb = TreeBuilder(trie, dims)
    else:
        etb = OrderlyTreeBuilder(trie, dims)
    etb.ParseBoard(board)
    t = etb.BuildTree()  # dedupe=False)
    # assert_invariants(t, cells)
    # dedupe_subtrees(t)

    mark = 1

    # t0 = t.children[0]
    # t0t = t0.children[0]
    # t = t0t

    with open("tree.dot", "w") as out:
        # out.write(t.to_dot(cells, max_depth=2))
        out.write(t.to_dot(cells, trie=trie))
        out.write("\n")

    mark += 1
    sys.stderr.write(
        f"tree.dot node count: {t.node_count()}, uniq={t.unique_node_count(mark)} bound={t.bound}\n"
    )

    for i, cell in enumerate(lift_cells):
        mark += 1
        t = t.lift_choice(
            cell, len(cells[cell]), None, mark, dedupe=False, compress=True
        )
        mark += 1
        sys.stderr.write(
            f"lift{i}.dot {cell} -> bound={t.bound} node count: {t.node_count()}, uniq={t.unique_node_count(mark)}\n"
        )
        with open(f"lift{i}.dot", "w") as out:
            # out.write(t.to_dot(cells, max_depth=1 + i))
            out.write(t.to_dot(cells))
            out.write("\n")


if __name__ == "__main__":
    main()
