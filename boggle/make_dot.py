#!/usr/bin/env python


import sys

from boggle.eval_tree import EvalTreeBoggler
from boggle.trie import make_py_trie


def main():
    trie = make_py_trie("wordlists/enable2k.txt")
    (board, *lift_cell_strs) = sys.argv[1:]
    lift_cells = [int(s) for s in lift_cell_strs]

    cells = board.split(" ")
    dims = {
        4: (2, 2),
        6: (2, 3),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(cells)]
    etb = EvalTreeBoggler(trie, dims)
    etb.ParseBoard(board)
    t = etb.BuildTree(dedupe=True)
    # assert_invariants(t, cells)
    # dedupe_subtrees(t)

    mark = 1

    mark += 1
    sys.stderr.write(
        f"node count: {t.node_count()}, uniq={t.unique_node_count(mark)} bound={t.bound}\n"
    )

    with open("tree.dot", "w") as out:
        out.write(t.to_dot(cells))
        out.write("\n")

    for i, cell in enumerate(lift_cells):
        mark += 1
        t = t.lift_choice(
            cell, len(cells[cell]), None, mark, dedupe=True, compress=True
        )
        mark += 1
        sys.stderr.write(
            f"lift{i}.dot {cell} -> node count: {t.node_count()}, uniq={t.unique_node_count(mark)}\n"
        )
        with open(f"lift{i}.dot", "w") as out:
            out.write(t.to_dot(cells))
            out.write("\n")


if __name__ == "__main__":
    main()
