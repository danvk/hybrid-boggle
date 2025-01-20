#!/usr/bin/env python
"""Break a 2x2 board class via successive lifting."""

import json
import sys

from boggle.eval_tree import EvalTreeBoggler
from boggle.trie import make_py_trie


def main():
    (board,) = sys.argv[1:]
    trie = make_py_trie("boggle-words.txt")
    cells = board.split(" ")
    dims = {
        4: (2, 2),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(cells)]

    etb = EvalTreeBoggler(trie, dims)
    etb.ParseBoard(board)
    cells = board.split(" ")
    t = etb.BuildTree()
    print(t.bound)
    print(t.node_count(), t.unique_node_count(), t.unique_node_count_by_hash())

    for i in range(4):
        print(f"lift {i}")
        t = t.lift_choice(i, len(cells[i]))
        print(
            f"-> {t.bound=}, {t.node_count()} nodes, {t.unique_node_count()} unique, {t.unique_node_count_by_hash()} structurally unique"
        )
        if dims == (2, 2):
            with open(f"/tmp/lifted{i}.json", "w") as out:
                json.dump(t.to_json(etb), out)


if __name__ == "__main__":
    main()
