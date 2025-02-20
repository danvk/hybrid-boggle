#!/usr/bin/env python


import sys

from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.tree_builder import TreeBuilder
from boggle.trie import make_py_trie


def main():
    trie = make_py_trie("wordlists/enable2k.txt")
    (board, *lift_cell_strs) = sys.argv[1:]
    lift_cells = [int(s) for s in lift_cell_strs]

    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    etb = TreeBuilder(trie, dims)
    etb.ParseBoard(board)
    t = etb.BuildTree(dedupe=False)
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
